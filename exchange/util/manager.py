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
        # self.ccxt_manager = CcxtManager.get_instance()
        # self.logger = LoggerAgent.get_instance()

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

        while True:
            __pending_queue = None
            __pending_thread = None
            initialize = False
            shared_ccxt_manager = None
            while self.start_event.is_set():
                try:
                    if not initialize and not queue_config.empty():
                        shared_ccxt_manager = queue_config.get()
                        __pending_queue = Queue()
                        __pending_thread = ExchangePendingThread(__pending_queue)
                        __pending_thread.start_job(shared_ccxt_manager, bot)
                        sleep(1)
                        initialize = True
                    # print("=====Execute time main {0}".format(strftime("%Y-%m-%d %H:%M:%S", gmtime())))
                    primary_msg, secondary_msg = execute_orders_concurrently(
                        lambda: get_balance(shared_ccxt_manager, True),
                        lambda: get_balance(shared_ccxt_manager, False)
                    )
                    primary_code = shared_ccxt_manager.get_exchange(True).exchange_code
                    secondary_code = shared_ccxt_manager.get_exchange(False).exchange_code
                    
                    primary_min_notional = get_min_notional(primary_code)
                    secondary_min_notional = get_min_notional(secondary_code)
                    
                    if primary_msg is not None and secondary_msg is not None:
                        # primary exchange
                        primary_sell_price = primary_msg['order_book']['bids'][0][0]
                        primary_buy_price = primary_msg['order_book']['asks'][0][0]
                        primary_balance = primary_msg['balance']
                        primary_amount_usdt = primary_balance['amount_usdt']
                        primary_amount_coin = primary_balance['amount_coin']

                        # secondary exchange
                        secondary_sell_price = secondary_msg['order_book']['bids'][0][0]
                        secondary_buy_price = secondary_msg['order_book']['asks'][0][0]
                        secondary_balance = secondary_msg['balance']
                        secondary_amount_usdt = secondary_balance['amount_usdt']
                        secondary_amount_coin = secondary_balance['amount_coin']

                        coin_trade = shared_ccxt_manager.get_coin_trade()
                        ccxt_primary = shared_ccxt_manager.get_ccxt(True)
                        ccxt_secondary = shared_ccxt_manager.get_ccxt(False)
                        secondary_coin_condition = (secondary_amount_coin * secondary_buy_price) < 10
                        primary_coin_condition = (primary_amount_coin * primary_buy_price) < 10
                        if secondary_amount_usdt < 10 or primary_amount_usdt < 10 or secondary_coin_condition or primary_coin_condition:
                            msg = "Warning exchange {0}/{1}".format(
                                primary_code,
                                secondary_code
                            )

                            msg = msg + "\n COIN {0} / {1}".format(primary_amount_coin, secondary_amount_coin)
                            msg = msg + "\n USDT {0} / {1}".format(primary_amount_usdt, secondary_amount_usdt)

                            bot.send_message(TelegramSetting.CHAT_WARNING_ID, msg)
                            sleep(300)
                            continue
                        # mua sàn secondary - bán sàn primary
                        if primary_sell_price > TradeSetting.ARBITRAGE_THRESHOLD * secondary_buy_price:
                            trade_info = maximum_quantity_trade_able(secondary_msg['order_book'],primary_msg['order_book'], TradeSetting.ARBITRAGE_THRESHOLD, TradeSetting.MAX_TRADE_QUANTITY)
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
                                    lambda: ccxt_primary.create_limit_sell_order(coin_trade, quantity, sell_price),
                                    lambda: ccxt_secondary.create_limit_buy_order(coin_trade, quantity, buy_price)
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
                            trade_info = maximum_quantity_trade_able(primary_msg['order_book'], secondary_msg['order_book'], TradeSetting.ARBITRAGE_THRESHOLD, TradeSetting.MAX_TRADE_QUANTITY)
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
                                    lambda: ccxt_primary.create_limit_buy_order(coin_trade, quantity, buy_price),
                                    lambda: ccxt_secondary.create_limit_sell_order(coin_trade, quantity, sell_price)
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
                            sleep(0.1)
                            print("Waiting...")
                            if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                                bot.send_message(TelegramSetting.CHAT_ID, "Trading status is waiting - not match")
                                current_time = datetime.datetime.now()
                    else:
                        sleep(0.5)
                except Exception as ex:
                    print("Error: {}".format(str(ex)))
                    send_error_telegram(ex, "Main Trading Loop", bot)

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

def get_balance(shared_ccxt_manager, is_primary):
    param_object = {}
    ccxt = shared_ccxt_manager.get_ccxt(is_primary)
    coin = shared_ccxt_manager.get_coin_trade()
    balance = ccxt.fetch_balance()
    orderbook = ccxt.fetch_order_book(coin)
    param_object['order_book'] = orderbook
    if balance is not None and balance['free'] is not None:
        param_object['balance'] = {}
        param_object['balance']['amount_usdt'] = float(0)
        param_object['balance']['amount_coin'] = float(0)
        for currency, amount in balance['free'].items():
            if currency == "USDT":
                param_object['balance']['amount_usdt'] = float(amount)
            if currency == coin.split('/')[0]:
                param_object['balance']['amount_coin'] = float(amount)
        return param_object
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