import datetime
import multiprocessing
from multiprocessing import Process, Event, Queue
from time import sleep
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
import time
import traceback

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
        self.rebalance_config.enabled = False
        self.rebalance_config.usdt_ratio = 0
        self.rebalance_config.coin_ratio = 0
        self.rebalance_config.usdt_threshold = 0
        self.rebalance_config.coin_threshold = 0

        self.rebalance_config.primary = manager.Namespace()
        self.rebalance_config.primary.coin_address = ""
        self.rebalance_config.primary.usdt_address = ""
        self.rebalance_config.primary.coin_network = ""
        self.rebalance_config.primary.usdt_network = ""

        self.rebalance_config.secondary = manager.Namespace()
        self.rebalance_config.secondary.coin_address = ""
        self.rebalance_config.secondary.usdt_address = ""
        self.rebalance_config.secondary.coin_network = ""
        self.rebalance_config.secondary.usdt_network = ""
        self.rebalance_config.trend_threshold = 0

        self.trade_strategy_config = manager.Namespace()
        self.trade_strategy_config.mode = "concurrently" # concurrently | sell_priority | buy_priority
        
        self.runtime_config = manager.Namespace()
        self.runtime_config.arbitrage_threshold = 1
        self.runtime_config.max_trade_quantity = None

        self.runtime_config.primary_trade = manager.Namespace()
        self.runtime_config.primary_trade.fee_taker = 0
        self.runtime_config.primary_trade.min_notional = 0

        self.runtime_config.secondary_trade = manager.Namespace()
        self.runtime_config.secondary_trade.fee_taker = 0
        self.runtime_config.secondary_trade.min_notional = 0
        
        self.telegram_config = manager.Namespace()
        self.telegram_config.bot_token = ""
        self.telegram_config.chat_id = ""
        self.telegram_config.chat_topic = 0
        self.telegram_config.warning_topic = 0
        self.telegram_config.error_topic = 0
    
    def set_rebalance_config(self, config):
        self.rebalance_config.enabled = bool(config.enabled)
        self.rebalance_config.usdt_ratio = float(config.usdt_ratio)
        self.rebalance_config.coin_ratio = float(config.coin_ratio)
        self.rebalance_config.usdt_threshold = float(config.usdt_threshold)
        self.rebalance_config.coin_threshold = float(config.coin_threshold)
        self.rebalance_config.primary.coin_address = config.primary.coin_address
        self.rebalance_config.primary.usdt_address = config.primary.usdt_address
        self.rebalance_config.primary.coin_network = config.primary.coin_network
        self.rebalance_config.primary.usdt_network = config.primary.usdt_network

        self.rebalance_config.secondary.coin_address = config.secondary.coin_address
        self.rebalance_config.secondary.usdt_address = config.secondary.usdt_address
        self.rebalance_config.secondary.coin_network = config.secondary.coin_network
        self.rebalance_config.secondary.usdt_network = config.secondary.usdt_network

        self.rebalance_config.trend_threshold = float(config.trend_threshold)
    
    def set_config_trade(self, primary_exchange, secondary_exchange, coin, arbitrage_threshold, max_trade_quantity, primary_trade, secondary_trade, telegram_config):
        ccxt = CcxtManager.get_instance()
        ccxt.set_configure(primary_exchange, secondary_exchange, coin)
        self.queue_config.put(ccxt)
        self.runtime_config.arbitrage_threshold = arbitrage_threshold
        self.runtime_config.max_trade_quantity = max_trade_quantity

        self.runtime_config.primary_trade.fee_taker = float(primary_trade.fee_taker)
        self.runtime_config.primary_trade.min_notional = float(primary_trade.min_notional)
        self.runtime_config.secondary_trade.fee_taker = float(secondary_trade.fee_taker)
        self.runtime_config.secondary_trade.min_notional = float(secondary_trade.min_notional)

        self.telegram_config.bot_token = telegram_config.bot_token
        self.telegram_config.chat_id = telegram_config.chat_id
        self.telegram_config.chat_topic = telegram_config.chat_topic
        self.telegram_config.warning_topic = telegram_config.warning_topic
        self.telegram_config.error_topic = telegram_config.error_topic

    def get_rebalance_config(self):
        return self.rebalance_config
    
    def set_trade_strategy_config(self, config):
        self.trade_strategy_config.mode = config.mode
      
    def get_trade_strategy_config(self):
        return self.trade_strategy_config

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

    def do_work(self, queue_config):
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
                        bot = telebot.TeleBot(self.telegram_config.bot_token)
                        shared_ccxt_manager = queue_config.get()
                        primary_ccxt = shared_ccxt_manager.get_ccxt(True)
                        secondary_ccxt = shared_ccxt_manager.get_ccxt(False)
                        symbol = shared_ccxt_manager.get_coin_trade()
                        watcher = WSOrderbookWatcher(primary_ccxt.id, secondary_ccxt.id, symbol)
                        __pending_queue = Queue()
                        __pending_thread = ExchangePendingThread(__pending_queue)
                        __pending_thread.start_job(shared_ccxt_manager, bot, self.telegram_config)
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
                            self.rebalance_config, self.runtime_config.arbitrage_threshold,
                            bot, self.telegram_config
                        )
                    else:
                        rebalance_manager.reset_rebalancing_state()
                    # mua sàn secondary - bán sàn primary
                    if primary_sell_price > self.runtime_config.arbitrage_threshold * secondary_buy_price:
                        trade_info = maximum_quantity_trade_able(secondary_orderbook, primary_orderbook, self.runtime_config.arbitrage_threshold, self.runtime_config.max_trade_quantity)
                        sell_price = trade_info["sell_price"]
                        buy_price = trade_info["buy_price"]
                        quantity =min(trade_info["quantity"],
                                      primary_amount_coin,
                                      secondary_amount_usdt*(1-self.runtime_config.secondary_trade.fee_taker)/buy_price
                        )
                        precision_invalid = (quantity * buy_price) <= self.runtime_config.secondary_trade.min_notional or (
                                quantity * sell_price) <= self.runtime_config.primary_trade.min_notional
                        if precision_invalid:
                            if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                                reason = "Volume small, SKIP" if quantity == trade_info["quantity"] else f"Insufficient balance {quantity}"
                                bot.send_message(self.telegram_config.chat_id, reason, message_thread_id=self.telegram_config.chat_topic)
                                current_time = datetime.datetime.now()
                            sleep(0.1)
                            continue
                        else:
                            sell_action = lambda amount=None: primary_ccxt.create_limit_sell_order(
                                symbol,
                                amount or quantity,
                                sell_price
                            )

                            buy_action = lambda amount=None: secondary_ccxt.create_limit_buy_order(
                                symbol,
                                amount or quantity,
                                buy_price
                            )
                            primary_order, secondary_order = handle_dual_order(
                                sell_action = sell_action,
                                sell_ccxt = primary_ccxt,
                                buy_action = buy_action,
                                buy_ccxt = secondary_ccxt,
                                symbol = symbol,
                                quantity=quantity,
                                mode = self.trade_strategy_config.mode,
                                bot = bot,
                                telegram_config = self.telegram_config
                            )
                            if not primary_order or not secondary_order:
                                continue
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
                    elif secondary_sell_price > self.runtime_config.arbitrage_threshold * primary_buy_price:
                        trade_info = maximum_quantity_trade_able(primary_orderbook, secondary_orderbook, self.runtime_config.arbitrage_threshold, self.runtime_config.max_trade_quantity)
                        sell_price = trade_info["sell_price"]
                        buy_price = trade_info["buy_price"]
                        quantity =min(trade_info["quantity"],
                                      secondary_amount_coin,
                                      primary_amount_usdt*(1-self.runtime_config.primary_trade.fee_taker)/buy_price
                        ) 

                        precision_invalid = (quantity * sell_price) <= self.runtime_config.secondary_trade.min_notional or (
                                quantity * buy_price) <= self.runtime_config.primary_trade.min_notional
                        if precision_invalid:
                            if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                                reason = "Volume small, SKIP" if quantity == trade_info["quantity"] else f"Insufficient balance {quantity}"
                                bot.send_message(self.telegram_config.chat_id, reason, message_thread_id=self.telegram_config.chat_topic)
                                current_time = datetime.datetime.now()
                            sleep(0.1)
                            continue
                        else:
                            sell_action = lambda amount=None: secondary_ccxt.create_limit_sell_order(
                                symbol,
                                secondary_ccxt.amount_to_precision(symbol, amount or quantity),
                                sell_price,
                            )

                            buy_action = lambda amount=None: primary_ccxt.create_limit_buy_order(
                                symbol,
                                primary_ccxt.amount_to_precision(symbol, amount or quantity),
                                buy_price,
                            )

                            secondary_order, primary_order = handle_dual_order(
                                sell_action=sell_action,
                                sell_ccxt=secondary_ccxt,
                                buy_action=buy_action,
                                buy_ccxt=primary_ccxt,
                                symbol=symbol,
                                quantity=quantity,
                                mode=self.trade_strategy_config.mode,
                                bot=bot,
                                telegram_config = self.telegram_config
                            )
                            if not primary_order or not secondary_order:
                                continue
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
                            bot.send_message(self.telegram_config.chat_id, "Trading status is waiting - not match", message_thread_id=self.telegram_config.chat_topic)
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
                    send_error_telegram(f"{ex}\n\nDebug: {debug_info}", "Main Trading Loop", bot, self.telegram_config.chat_id, self.telegram_config.error_topic)
                    sleep(10)

            if watcher is not None:
                watcher.stop()

            if not self.start_event.is_set():
                try:
                    if __pending_thread is not None:
                        __pending_thread.stop_job()

                    if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                        bot.send_message(self.telegram_config.chat_id, "Trading is not start", message_thread_id=self.telegram_config.chat_topic)
                        current_time = datetime.datetime.now()
                except Exception as ex:
                    print("Send chat box error {0}".format(ex))
            sleep(1)
            print("Process is stopped")
            if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                bot.send_message(self.telegram_config.chat_id, "Process is stopped", message_thread_id=self.telegram_config.chat_topic)
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

def handle_dual_order(
    sell_action,
    buy_action,
    sell_ccxt,
    buy_ccxt,
    symbol,
    quantity,
    mode="concurrently",
    bot=None,
    telegram_config=None,
):
    try:
        if mode == "concurrently":
            return execute_orders_concurrently(sell_action, buy_action)

        if mode == "sell_priority":
            sell_order = sell_action()
            order_id = sell_order["id"]

            for _ in range(2):
                order = sell_ccxt.fetch_order(order_id, symbol)
                filled = get_filled_amount(order)

                if filled > 0:
                    break

                time.sleep(0.3)

            filled = get_filled_amount(order)

            if filled >= quantity:
                print(f"[ARB] SELL fully filled {filled}/{quantity}")
                buy_order = buy_action()
                return order, buy_order

            print(f"[ARB] SELL filled {filled}/{quantity} → cancel")

            try:
                sell_ccxt.cancel_order(order_id, symbol)
            except Exception as e:
                print(f"[ARB] Cancel error → assume FULL fill: {e}")
                buy_order = buy_action(quantity)
                return order, buy_order

            final_order = sell_ccxt.fetch_order(order_id, symbol)
            final_filled = get_filled_amount(final_order)

            print(f"[ARB] SELL final filled {final_filled}/{quantity}")

            if final_filled > 0:
                buy_order = buy_action(final_filled)
                return final_order, buy_order

            return None, None

        if mode == "buy_priority":
            buy_order = buy_action()
            order_id = buy_order["id"]

            for _ in range(2):
                order = buy_ccxt.fetch_order(order_id, symbol)
                filled = get_filled_amount(order)

                if filled > 0:
                    break

                time.sleep(0.3)

            filled = get_filled_amount(order)

            if filled >= quantity:
                print(f"[ARB] BUY fully filled {filled}/{quantity}")
                sell_order = sell_action()
                return sell_order, order

            print(f"[ARB] BUY filled {filled}/{quantity} → cancel")

            try:
                buy_ccxt.cancel_order(order_id, symbol)
            except Exception as e:
                print(f"[ARB] Cancel error → assume FULL fill: {e}")
                sell_order = sell_action(quantity)
                return sell_order, order

            # fetch lại sau cancel
            final_order = buy_ccxt.fetch_order(order_id, symbol)
            final_filled = get_filled_amount(final_order)

            print(f"[ARB] BUY final filled {final_filled}/{quantity}")

            if final_filled > 0:
                sell_order = sell_action(final_filled)
                return sell_order, final_order

            return None, None

        print(f"[handle_dual_order] Invalid mode {mode}")
        return None, None

    except Exception as ex:
        print(f"[handle_dual_order] Fatal Error: {ex}")
        send_telegram_error_once(symbol, ex, bot, telegram_config)
        return None, None

def get_filled_amount(order):
    return float(order.get("filled", 0) or 0)

_last_telegram_dual_order_time = {}
def send_telegram_error_once(
    symbol: str, ex: Exception, bot=None, telegram_config=None, cooldown: int = 300
):
    global _last_telegram_dual_order_time
    now = datetime.datetime.now().timestamp()
    last_time = _last_telegram_dual_order_time.get(symbol, 0)

    if bot and telegram_config and now - last_time >= cooldown:
        error_msg = f"{ex}\n\nTraceback:\n{traceback.format_exc()}"
        send_error_telegram(
            error_msg,
            f"handle_dual_order ({symbol})",
            bot,
            telegram_config.chat_id,
            telegram_config.error_topic,
        )
        _last_telegram_dual_order_time[symbol] = now