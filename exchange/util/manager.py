import datetime
import multiprocessing
from multiprocessing import Process, Event, Queue
from time import sleep
from exchange.util.ccxt_manager import CcxtManager
from exchange.util.exchange_pending_thread import ExchangePendingThread
from exchange.util.exchange_thread import ExchangeThread
import uuid
import telebot
from time import gmtime, strftime

from exchange.util.log_agent import LoggerAgent

CHAT_ID = "-4256093220"


class Manager:
    start_flag = True
    instance = None
    initialize = True
    ccxt_manager = None
    shared_ccxt_manager = None
    queue_config = Queue()
    logger = None

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
        self.logger = LoggerAgent.get_instance()

    def get_shared_ccxt_manager(self):
        return self.shared_ccxt_manager

    def start_worker(self):
        self.process = Process(target=self.do_work, args=(self.queue_config, self.logger))
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

    def do_work(self, queue_config, logger):
        bot = telebot.TeleBot("6331463036:AAF5L45My0A17fNI01HrBwQeYWhtnX0ZIzc")
        current_time = datetime.datetime.now()

        while True:
            # __primary_thread = None
            # __secondary_thread = None
            __pending_thread = None
            # __primary_queue = None
            # __secondary_queue = None
            __pending_queue = None
            initialize = False
            shared_ccxt_manager = None
            while self.start_event.is_set():
                try:
                    if not initialize and not queue_config.empty():
                        shared_ccxt_manager = queue_config.get()
                        # __primary_queue = Queue(maxsize=1)
                        # __secondary_queue = Queue(maxsize=1)
                        __pending_queue = Queue()
                        # __primary_thread = ExchangeThread(__primary_queue, True)
                        # __secondary_thread = ExchangeThread(__secondary_queue, False)
                        __pending_thread = ExchangePendingThread(__pending_queue)

                        # __secondary_thread.start_job(shared_ccxt_manager)
                        # __primary_thread.start_job(shared_ccxt_manager)
                        __pending_thread.start_job(shared_ccxt_manager)
                        initialize = True
                    # print("==============Cal:  ", str(__primary_queue.qsize()), str(__secondary_queue.qsize()))
                    # print("Get queue {} / {}".format(__primary_queue.qsize(), __secondary_queue.qsize()))
                    print("=====Execute time main {0}".format(strftime("%Y-%m-%d %H:%M:%S", gmtime())))
                    primary_msg = get_balance(shared_ccxt_manager, True)
                    secondary_msg = get_balance(shared_ccxt_manager, False)

                    if primary_msg is not None and secondary_msg is not None:
                        try:
                            # primary_msg = get_latest_queue(__primary_queue)
                            # secondary_msg = get_latest_queue(__secondary_queue)

                            # primary exchange
                            primary_buy_price = primary_msg['order_book']['bids'][0][0]
                            primary_sell_price = primary_msg['order_book']['asks'][0][0]
                            primary_buy_quantity = primary_msg['order_book']['bids'][0][1]
                            primary_sell_quantity = primary_msg['order_book']['asks'][0][1]
                            primary_balance = primary_msg['balance']
                            primary_amount_usdt = primary_balance['amount_usdt']
                            primary_amount_coin = primary_balance['amount_coin']

                            # secondary exchange
                            secondary_buy_price = secondary_msg['order_book']['bids'][0][0]
                            secondary_sell_price = secondary_msg['order_book']['asks'][0][0]
                            secondary_buy_quantity = secondary_msg['order_book']['bids'][0][1]
                            secondary_sell_quantity = secondary_msg['order_book']['asks'][0][1]
                            secondary_balance = secondary_msg['balance']
                            secondary_amount_usdt = secondary_balance['amount_usdt']
                            secondary_amount_coin = secondary_balance['amount_coin']

                            msg_1 = "Secondary exchange {0} / {1}".format(
                                secondary_amount_usdt,
                                secondary_amount_coin
                            )

                            msg_2 = "Primary exchange {0} / {1}".format(
                                primary_amount_usdt,
                                primary_amount_coin
                            )

                            print(msg_1)
                            print(msg_2)

                            coin_trade = shared_ccxt_manager.get_coin_trade()
                            ccxt_primary = shared_ccxt_manager.get_ccxt(True)
                            ccxt_secondary = shared_ccxt_manager.get_ccxt(False)

                            if secondary_amount_usdt < 20 or primary_amount_usdt < 20:

                                msg = "Warning exchange {0}/{1}".format(
                                    shared_ccxt_manager.get_exchange(False).exchange_code,
                                    shared_ccxt_manager.get_exchange(True).exchange_code
                                )

                                msg = msg + "\n COIN {0} / {1}".format(primary_amount_coin, secondary_amount_coin)
                                msg = msg + "\n USDT {0} / {1}".format(primary_amount_usdt, secondary_amount_usdt)

                                bot.send_message(CHAT_ID, msg)
                                logger.info(msg)
                                sleep(5)
                                continue

                            if primary_buy_price > 1.006 * secondary_sell_price:
                                quantity = min(
                                    min(
                                        primary_buy_price * primary_buy_quantity,
                                        secondary_sell_price * secondary_sell_quantity,
                                        primary_amount_usdt,
                                        secondary_amount_usdt) / primary_buy_price, primary_amount_coin,
                                    secondary_amount_coin)
                                print("Buy primary and sell secondary", quantity)
                                logger.info("Buy primary and sell secondary: {0}".format(quantity))
                                primary_order = ccxt_primary.create_limit_sell_order(coin_trade,
                                                                                     quantity,
                                                                                     primary_buy_price)
                                secondary_order = ccxt_secondary.create_limit_buy_order(coin_trade,
                                                                                        quantity,
                                                                                        secondary_sell_price)
                                __pending_queue.put({'is_primary': True, 'order_id': primary_order['id']})
                                __pending_queue.put({'is_primary': False, 'order_id': secondary_order['id']})

                            elif secondary_buy_price > 1.006 * primary_sell_price:
                                quantity = min(
                                    min(secondary_buy_price * secondary_buy_quantity,
                                        primary_sell_price * primary_sell_quantity,
                                        secondary_amount_usdt,
                                        primary_amount_usdt) / secondary_buy_price, secondary_amount_coin,
                                    primary_amount_coin)
                                print("Sell primary and buy secondary", quantity)
                                logger.info("Sell primary and buy secondary: {0}".format(quantity))
                                primary_order = ccxt_primary.create_limit_buy_order(coin_trade,
                                                                                    quantity,
                                                                                    primary_sell_price)
                                secondary_order = ccxt_secondary.create_limit_sell_order(coin_trade,
                                                                                         quantity,
                                                                                         secondary_buy_price)

                                __pending_queue.put({'is_primary': True, 'order_id': primary_order['id']})
                                __pending_queue.put({'is_primary': False, 'order_id': secondary_order['id']})
                            else:
                                sleep(0.1)
                                print("Waiting...")
                                logger.info("Waiting...")
                                if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                                    bot.send_message(CHAT_ID, "Trading status is waiting - not match")
                                    current_time = datetime.datetime.now()
                        except Exception as ex:
                            print("Error manager:  {}".format(ex))
                            logger.info("Error manager 1: {0}".format(ex))
                            try:
                                if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                                    bot.send_message(CHAT_ID, "Error manager")
                                    current_time = datetime.datetime.now()
                            except Exception as ex:
                                print("Error:  {}".format(ex))
                    else:
                        sleep(0.5)
                except Exception as ex:
                    print("Error:  {}".format(ex))
                    logger.info("Error manager 2: {0}".format(ex))
                    try:
                        if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                            bot.send_message(CHAT_ID, "Error manager")
                            current_time = datetime.datetime.now()
                        else:
                            sleep(1)
                    except Exception as ex:
                        logger.info("Send chat box error".format(ex))

            if not self.start_event.is_set():
                if __pending_thread is not None:
                    __pending_thread.stop_job()
                try:
                    if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                        bot.send_message(CHAT_ID, "Trading is not start")
                        current_time = datetime.datetime.now()
                except Exception as ex:
                    logger.info("Send chat box error".format(ex))
            sleep(0.5)
            print("Process is stopped")
            logger.info("Process is running")
            try:
                if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                    bot.send_message(CHAT_ID, "Process is stopped")
                    current_time = datetime.datetime.now()
            except Exception as ex:
                logger.info("Send chat box error".format(ex))


def get_latest_queue(q):
    if not q.empty():
        return q.get()
    else:
        return None


def get_balance(shared_ccxt_manager, is_primary):
    param_object = {}
    ccxt = shared_ccxt_manager.get_ccxt(is_primary)
    coin = shared_ccxt_manager.get_coin_trade()
    orderbook = ccxt.fetch_order_book(coin)
    param_object['order_book'] = orderbook
    balance = ccxt.fetch_balance()
    if balance is not None and balance['total'] is not None:
        param_object['balance'] = {}
        param_object['balance']['amount_usdt'] = float(0)
        param_object['balance']['amount_coin'] = float(0)
        for currency, amount in balance['total'].items():
            if currency == "USDT":
                param_object['balance']['amount_usdt'] = float(amount)
            if currency == coin.split('/')[0]:
                param_object['balance']['amount_coin'] = float(amount)

        # if shared_ccxt_manager.get_simulator() == 1:
        #     param_object['balance']['amount_usdt'] = 250
        #     param_object['balance']['amount_coin'] = 250
        return param_object
    return None
