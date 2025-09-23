import datetime
import multiprocessing
from multiprocessing import Process, Event, Queue
from time import sleep
from config.config import TradeSetting, TelegramSetting, ExchangeNotionalSetting
from exchange.models.order_status import OrderStatus
from exchange.util.ccxt_manager import CcxtManager
from exchange.util.exchange_pending_thread import ExchangePendingThread
from exchange.util.exchange_thread import ExchangeThread
import telebot
from collections import deque
from exchange.util.log_agent import LoggerAgent
from exchange.util.order_executor import execute_orders_concurrently
from exchange.util.telegram_utils import send_error_telegram
from exchange.util.ws_orderbook_watcher import WSOrderbookWatcher
from exchange.util.rebalancing import rebalancing

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
        self.shared_config = manager.Namespace()
        self.shared_config.auto_rebalance = False
        # self.ccxt_manager = CcxtManager.get_instance()
        # self.logger = LoggerAgent.get_instance()
    
    def set_auto_rebalance(self, enable: bool):
        self.shared_config.auto_rebalance = enable

    def get_auto_rebalance(self) -> bool:
        return self.shared_config.auto_rebalance

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
        is_rebalancing = False
        last_warning_time = None   

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
                    primary_amount_usdt = primary_balance['amount_usdt']
                    primary_amount_coin = primary_balance['amount_coin']

                    secondary_sell_price = secondary_orderbook['bids'][0][0]
                    secondary_buy_price = secondary_orderbook['asks'][0][0]
                    secondary_amount_usdt = secondary_balance['amount_usdt']
                    secondary_amount_coin = secondary_balance['amount_coin']
                    
                    secondary_coin_condition = (secondary_amount_coin * secondary_buy_price) < 10
                    primary_coin_condition = (primary_amount_coin * primary_buy_price) < 10
                    wallet_not_enough = secondary_amount_usdt < 10 or primary_amount_usdt < 10 or secondary_coin_condition or primary_coin_condition
                    if wallet_not_enough:
                        if not is_rebalancing:
                            try:
                                rebalancing(primary_ccxt, secondary_ccxt, symbol,
                                            primary_orderbook, secondary_orderbook,
                                            self.shared_config.auto_rebalance, TradeSetting.ARBITRAGE_THRESHOLD)
                                is_rebalancing = True
                            except Exception as ex:
                                is_rebalancing = False
                                send_error_telegram(ex, "Rebalancing Failed", bot)
                                sleep(10)
                        msg = "Warning exchange {0}/{1}".format(
                            primary_code,
                            secondary_code
                        )
                        msg = msg + "\n COIN {0} / {1}".format(primary_amount_coin, secondary_amount_coin)
                        msg = msg + "\n USDT {0} / {1}".format(primary_amount_usdt, secondary_amount_usdt)
                        if last_warning_time is None or (datetime.datetime.now() - last_warning_time).total_seconds() >= 600:
                            bot.send_message(TelegramSetting.CHAT_WARNING_ID, msg)
                            last_warning_time = datetime.datetime.now()
                    else:
                        is_rebalancing = False

                    # mua sàn secondary - bán sàn primary
                    if primary_sell_price > TradeSetting.ARBITRAGE_THRESHOLD * secondary_buy_price:
                        trade_info = maximum_quantity_trade_able(secondary_orderbook, primary_orderbook, TradeSetting.ARBITRAGE_THRESHOLD, TradeSetting.MAX_TRADE_QUANTITY)
                        sell_price = trade_info["sell_price"]
                        buy_price = trade_info["buy_price"]
                        quantity =min(trade_info["quantity"], primary_amount_coin, secondary_amount_usdt/buy_price) 

                        precision_invalid = (quantity * buy_price) <= secondary_min_notional or (
                                quantity * sell_price) <= primary_min_notional
                        if precision_invalid:
                            if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                                bot.send_message(TelegramSetting.CHAT_ID, "Volume small, SKIP")
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
                        

                    # mua sàn primary - bán sàn secondary
                    elif secondary_sell_price > TradeSetting.ARBITRAGE_THRESHOLD * primary_buy_price:
                        trade_info = maximum_quantity_trade_able(primary_orderbook, secondary_orderbook, TradeSetting.ARBITRAGE_THRESHOLD, TradeSetting.MAX_TRADE_QUANTITY)
                        sell_price = trade_info["sell_price"]
                        buy_price = trade_info["buy_price"]
                        quantity =min(trade_info["quantity"], secondary_amount_coin, primary_amount_usdt/buy_price) 

                        precision_invalid = (quantity * sell_price) <= secondary_min_notional or (
                                quantity * buy_price) <= primary_min_notional
                        if precision_invalid:
                            if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                                bot.send_message(TelegramSetting.CHAT_ID, "Volume small, SKIP")
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

                    else:
                        if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                            print("Waiting...")
                            bot.send_message(TelegramSetting.CHAT_ID, "Trading status is waiting - not match")
                            current_time = datetime.datetime.now()
                    sleep(0.01)
                except Exception as ex:
                    debug_info = {
                        "primary_balance": primary_balance if 'primary_balance' in locals() else None,
                        "secondary_balance": secondary_balance if 'secondary_balance' in locals() else None,
                        "last_quantity": quantity if 'quantity' in locals() else None
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
    result = {'amount_usdt': 0.0, 'amount_coin': 0.0}

    if balance is not None and balance.get('free') is not None:
        base_coin = symbol.split('/')[0]
        for currency, amount in balance['free'].items():
            if currency == "USDT":
                result['amount_usdt'] = float(amount)
            if currency == base_coin:
                result['amount_coin'] = float(amount)
        return result

    return None

def get_min_notional(exchange_code: str) -> float:
    return ExchangeNotionalSetting.MIN.get(exchange_code.upper(), ExchangeNotionalSetting.MIN["DEFAULT"])

def maximum_quantity_trade_able(buy_order_book, sell_order_book, threshold, max_trade_quantity):
    """
    Find the maximum tradable quantity between two order books
    while satisfying the arbitrage threshold condition.

    Args:
        buy_order_book: {"asks": deque([(price, quantity), ...])}
        sell_order_book: {"bids": deque([(price, quantity), ...])}
        threshold: arbitrage threshold (multiplier)
        max_trade_quantity: maximum trade quantity

    Returns:
        {"buy_price": float, "sell_price": float, "quantity": float}
    """
    asks = deque([list(x) for x in buy_order_book["asks"]])  # [price, qty]
    bids = deque([list(x) for x in sell_order_book["bids"]])

    result = {
        "buy_price": 0,
        "sell_price": 0,
        "quantity": 0
    }

    while asks and bids and result["quantity"] < max_trade_quantity:
        buy_price, buy_quantity = asks[0]
        sell_price, sell_quantity = bids[0]

        if sell_price <= buy_price * threshold:
            break

        result["buy_price"] = buy_price
        result["sell_price"] = sell_price

        remain = max_trade_quantity - result["quantity"]

        if buy_quantity > sell_quantity:
            trade_qty = min(sell_quantity, remain)
            asks[0][1] = buy_quantity - trade_qty
            if trade_qty == sell_quantity:
                bids.popleft()
            result["quantity"] += trade_qty
        elif buy_quantity < sell_quantity:
            trade_qty = min(buy_quantity, remain)
            bids[0][1] = sell_quantity - trade_qty
            if trade_qty == buy_quantity:
                asks.popleft()
            result["quantity"] += trade_qty
        else:
            trade_qty = min(buy_quantity, remain)
            if trade_qty == buy_quantity:
                asks.popleft()
                bids.popleft()
            else:
                asks[0][1] = buy_quantity - trade_qty
                bids[0][1] = sell_quantity - trade_qty
            result["quantity"] += trade_qty

    return result