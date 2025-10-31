import datetime
import multiprocessing
from multiprocessing import Process, Event, Queue
from time import sleep
from config.config import TradeSetting, TelegramSetting, ExchangeNotionalSetting, TradeEnv
from exchange.models.order_status import OrderStatus
from exchange.util.ccxt_manager import CcxtManager
from exchange.util.exchange_pending_thread import ExchangePendingThread
from exchange.util.exchange_thread import ExchangeThread
import telebot
from exchange.util.log_agent import LoggerAgent
from exchange.util.order_executor import execute_orders_concurrently
from exchange.util.telegram_utils import send_error_telegram
from exchange.util.ws_orderbook_watcher import WSOrderbookWatcher
from exchange.util.rebalancing import RebalancingManager
from exchange.util.orderbook_tools import maximum_quantity_trade_able

class Manager:
    start_flag = True
    instance = None
    initialize = True
    ccxt_manager = None
    shared_ccxt_manager = None
    queue_config = Queue()

    # logger = None

    @staticmethod
    def get_instance():
        if Manager.instance is None:
            print("Init other instance")
            Manager.instance = Manager()
        return Manager.instance

    def __init__(self):
        self.process = None
        self.instance = self
        self.start_event = Event()
        manager = multiprocessing.Manager()
        self.shared_ccxt_manager = manager.Namespace()
        self.shared_ccxt_manager.instance = CcxtManager.get_instance()
        self.rebalance_config = manager.Namespace()
    
    def set_rebalance_config(self, config):
        self.rebalance_config.enabled = bool(config.enabled)
        self.rebalance_config.usdt_ratio = float(config.usdt_ratio)
        self.rebalance_config.coin_ratio = float(config.coin_ratio)
        self.rebalance_config.usdt_threshold = float(config.usdt_threshold)
        self.rebalance_config.coin_threshold = float(config.coin_threshold)
    def get_rebalance_config(self):
        return self.rebalance_config

    def get_shared_ccxt_manager(self):
        return self.shared_ccxt_manager

    def start_worker(self):
        self.process = Process(target=self.do_work, args=(self.queue_config,))
        self.process.start()

    def start(self):
        if self.start_event.is_set():
            return
        self.start_event.set()

    def stop(self):
        if not self.start_event.is_set():
            return
        self.start_event.clear()  # Đặt sự kiện dừng thành False

    def stop_worker(self):
        try:
            self.start_flag = False
            self.process.join()
            self.process.daemon = True
            self.process = None
            print("Stop worker")
        except Exception as ex:
            print("TraderAgent.worker_handler::".format(ex.__str__()))

    def set_config_trade(self, primary_exchange, secondary_exchange, coin, limit, simulator):
        ccxt = CcxtManager.get_instance()
        ccxt.set_configure(primary_exchange, secondary_exchange, coin, limit, simulator)
        self.queue_config.put(ccxt)

    def do_work(self, queue_config):
        bot = telebot.TeleBot(TelegramSetting.TOKEN)
        current_time = datetime.datetime.now()
        watcher = None
        rebalance_manager = RebalancingManager()

        while True:
            __pending_queue = None
            __pending_thread = None
            initialize = False
            shared_ccxt_manager = None
            while self.start_event.is_set():
                try:
                    if not initialize and not queue_config.empty():
                        shared_ccxt_manager = queue_config.get()
                        primary_ccxt = shared_ccxt_manager.get_ccxt(True)
                        secondary_ccxt = shared_ccxt_manager.get_ccxt(False)
                        symbol = shared_ccxt_manager.get_coin_trade()
                        watcher = WSOrderbookWatcher(primary_ccxt.id, secondary_ccxt.id, symbol)
                        __pending_queue = Queue()
                        __pending_thread = ExchangePendingThread(__pending_queue)
                        __pending_thread.start_job(shared_ccxt_manager, bot)
                        sleep(1)
                        initialize = True
                    primary_balance, secondary_balance = execute_orders_concurrently(
                        lambda: get_balance(primary_ccxt, symbol),
                        lambda: get_balance(secondary_ccxt, symbol)
                    )
                    if primary_balance is None or secondary_balance is None:
                        continue
                    if not watcher.wait_update(timeout=5):
                        continue
                    
                    primary_orderbook, secondary_orderbook = watcher.get_orderbooks()
                    if not primary_orderbook or not secondary_orderbook:
                        continue
                    
                    primary_code = primary_ccxt.id
                    secondary_code = secondary_ccxt.id
                    primary_min_notional = get_min_notional(primary_code)
                    secondary_min_notional = get_min_notional(secondary_code)

                    primary_sell_price = primary_orderbook['bids'][0][0]
                    primary_buy_price = primary_orderbook['asks'][0][0]
                    primary_amount_usdt = primary_balance.get("amount_usdt", {}).get("free", 0)
                    primary_amount_coin = primary_balance.get('amount_coin', {}).get("free", 0)
                    secondary_sell_price = secondary_orderbook['bids'][0][0]
                    secondary_buy_price = secondary_orderbook['asks'][0][0]
                    secondary_amount_usdt = secondary_balance.get("amount_usdt", {}).get("free", 0)
                    secondary_amount_coin = secondary_balance.get('amount_coin', {}).get("free", 0)
                    
                    wallet_not_enough = rebalance_manager.check_wallet_conditions(
                        primary_balance, secondary_balance,
                        primary_buy_price, secondary_buy_price,
                        self.rebalance_config
                    )
                    if wallet_not_enough:
                        rebalance_manager.handle_low_balance(
                            primary_ccxt, secondary_ccxt, symbol,
                            primary_orderbook, secondary_orderbook,
                            primary_balance, secondary_balance,
                            self.rebalance_config, TradeSetting.ARBITRAGE_THRESHOLD
                        )
                    else:
                        rebalance_manager.reset_rebalancing_state()

                    # mua sàn secondary - bán sàn primary
                    if primary_sell_price > TradeSetting.ARBITRAGE_THRESHOLD * secondary_buy_price:
                        trade_info = maximum_quantity_trade_able(secondary_orderbook, primary_orderbook, TradeSetting.ARBITRAGE_THRESHOLD, TradeSetting.MAX_TRADE_QUANTITY)
                        sell_price = trade_info["sell_price"]
                        buy_price = trade_info["buy_price"]
                        quantity =min(trade_info["quantity"],
                                      primary_amount_coin,
                                      secondary_amount_usdt*(1-TradeEnv.SECONDARY_FEE_TAKER)/buy_price
                        )

                        precision_invalid = (quantity * buy_price) <= secondary_min_notional or (
                                quantity * sell_price) <= primary_min_notional
                        if precision_invalid:
                            if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                                reason = "Volume small, SKIP" if quantity == trade_info["quantity"] else f"Insufficient balance {quantity}"
                                bot.send_message(TelegramSetting.CHAT_ID, reason)
                                current_time = datetime.datetime.now()
                            sleep(0.1)
                            continue
                        else:
                            primary_order, secondary_order = execute_orders_concurrently(
                                lambda: primary_ccxt.create_limit_sell_order(symbol, quantity, sell_price),
                                lambda: secondary_ccxt.create_limit_buy_order(symbol, quantity, buy_price)
                            )
                            order_mgs_primary = round(quantity * buy_price, 2)
                            order_mgs_secondary = round(quantity * sell_price, 2)
                            primary_pending_order = OrderStatus(True,
                                                                primary_order['id'],
                                                                order_mgs_primary)
                            secondary_pending_order = OrderStatus(False,
                                                                  secondary_order['id'],
                                                                  order_mgs_secondary)

                            msg_transaction = {'primary': primary_pending_order,
                                                'secondary': secondary_pending_order}
                            __pending_queue.put(msg_transaction)
                            current_time = datetime.datetime.now()

                    # mua sàn primary - bán sàn secondary
                    elif secondary_sell_price > TradeSetting.ARBITRAGE_THRESHOLD * primary_buy_price:
                        trade_info = maximum_quantity_trade_able(primary_orderbook, secondary_orderbook, TradeSetting.ARBITRAGE_THRESHOLD, TradeSetting.MAX_TRADE_QUANTITY)
                        sell_price = trade_info["sell_price"]
                        buy_price = trade_info["buy_price"]
                        quantity =min(trade_info["quantity"],
                                      secondary_amount_coin,
                                      primary_amount_usdt*(1-TradeEnv.PRIMARY_FEE_TAKER)/buy_price
                        ) 

                        precision_invalid = (quantity * sell_price) <= secondary_min_notional or (
                                quantity * buy_price) <= primary_min_notional
                        if precision_invalid:
                            if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                                reason = "Volume small, SKIP" if quantity == trade_info["quantity"] else f"Insufficient balance {quantity}"
                                bot.send_message(TelegramSetting.CHAT_ID, reason)
                                current_time = datetime.datetime.now()
                            sleep(0.1)
                            continue
                        else:
                            primary_order, secondary_order = execute_orders_concurrently(
                                lambda: primary_ccxt.create_limit_buy_order(symbol, quantity, buy_price),
                                lambda: secondary_ccxt.create_limit_sell_order(symbol, quantity, sell_price)
                            )
                            order_mgs_primary = round(quantity * buy_price, 2)
                            order_mgs_secondary = round(quantity * sell_price, 2)
                            primary_pending_order = OrderStatus(True,
                                                                primary_order['id'],
                                                                order_mgs_primary)
                            secondary_pending_order = OrderStatus(False,
                                                                  secondary_order['id'],
                                                                  order_mgs_secondary)

                            msg_transaction = {'primary': primary_pending_order,
                                                'secondary': secondary_pending_order}
                            __pending_queue.put(msg_transaction)
                            current_time = datetime.datetime.now()
                    else:
                        if (datetime.datetime.now() - current_time).total_seconds() >= 3*3600:
                            print("Waiting...")
                            bot.send_message(TelegramSetting.CHAT_ID, "Trading status is waiting - not match")
                            current_time = datetime.datetime.now()
                    sleep(0.01)
                except Exception as ex:
                    debug_info = {
                        "primary_balance": primary_balance if 'primary_balance' in locals() else None,
                        "secondary_balance": secondary_balance if 'secondary_balance' in locals() else None,
                        "sell_price": sell_price if 'sell_price' in locals() else None,
                        "buy_price": buy_price if 'buy_price' in locals() else None,
                        "quantity": quantity if 'quantity' in locals() else None
                    }
                    print("Error: {} | Debug: {}".format(str(ex), debug_info))
                    send_error_telegram(f"{ex}\n\nDebug: {debug_info}", "Main Trading Loop", bot)
                    sleep(10)

            if watcher is not None:
                watcher.stop()

            if not self.start_event.is_set():
                try:
                    if __pending_thread is not None:
                        __pending_thread.stop_job()

                    if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                        bot.send_message(TelegramSetting.CHAT_ID, "Trading is not start")
                        current_time = datetime.datetime.now()
                except Exception as ex:
                    print("Send chat box error {0}".format(ex))
            sleep(1)
            print("Process is stopped")
            if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                bot.send_message(TelegramSetting.CHAT_ID, "Process is stopped")
                current_time = datetime.datetime.now()

def get_balance(ccxt_instance, symbol):
    balance = ccxt_instance.fetch_balance()
    result = {
        'amount_usdt': {
            "free": 0.0,
            "used": 0.0,
            "total": 0.0
        }, 
        'amount_coin': {
            "free": 0.0,
            "used": 0.0,
            "total": 0.0
        }
    }

    if balance and balance.get("free") is not None:
        base_coin = symbol.split('/')[0]
        if balance.get("USDT") is not None:
            result["amount_usdt"] = balance["USDT"]
        if balance.get(base_coin) is not None:
            result["amount_coin"] = balance[base_coin]

    return result

def get_min_notional(exchange_code: str) -> float:
    return ExchangeNotionalSetting.MIN.get(exchange_code.upper(), ExchangeNotionalSetting.MIN["DEFAULT"])
