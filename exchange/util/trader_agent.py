import multiprocessing
from multiprocessing import Process
from multiprocessing.queues import Queue
from time import sleep

from exchange.util.ccxt_manager import CcxtManager
from exchange.util.exchange_thread import ExchangeThread
from exchange.util.log_agent import LoggerAgent


class TraderAgent:
    __instance = None
    __worker_process = None
    stop_flag = False
    session_key_trade = None

    # Initialization flag
    init_process_trade = False
    logger = None
    running_flag = False
    __simulator = True
    __ccxt_manager = None

    __secondary_exchange_thread = None
    __primary_exchange_thread = None

    @staticmethod
    def get_instance():
        if TraderAgent.__instance is None:
            TraderAgent.__instance = TraderAgent()
        return TraderAgent.__instance

    def __init__(self):
        self.session_key = None
        self.logger = LoggerAgent.get_instance()
        self.__ccxt_manager = CcxtManager.get_instance()
        self.__worker_process = None
        self.start_worker()

    def set_session(self, key):
        self.session_key = key

    def get_session_key(self):
        return self.session_key

    def stop_worker(self):
        if TraderAgent.__worker_process is not None:
            self.logger.info("------------------------------------------------")
            self.logger.info("------------------ STOP PROCESS ----------------")
            self.logger.info("------------------------------------------------")
            self.__worker_process.join()
            self.__worker_process = None

    def start_worker(self):
        if TraderAgent.__worker_process is None:
            self.logger.info("------------------------------------------------")
            self.logger.info("------------------ START PROCESS ----------------")
            self.logger.info("------------------------------------------------")
            # self.__worker_process = multiprocessing.Process(
            #     target=TraderAgent.worker_handler
            # )
            self.__worker_process = Process(target=self.worker_handler, args=())

            self.__worker_process.daemon = False
            self.__worker_process.start()
            print("Start working thread")

    def set_config_trade(self, primary_exchange, secondary_exchange, coin, simulator):
        self.__ccxt_manager.set_primary_exchange(primary_exchange)
        self.__ccxt_manager.set_secondary_exchange(secondary_exchange)
        self.__ccxt_manager.set_coin_trade(coin)
        self.__simulator = simulator
        self.init_process_trade = False

    def start_trade(self):
        self.logger.info("------------------------------------------------")
        self.logger.info("------------------ START TRADE -----------------")
        self.logger.info("------------------------------------------------")
        self.running_flag = True
        print("Hello world ", self.running_flag)

    def stop_trade(self):
        self.logger.info("------------------------------------------------")
        self.logger.info("------------------ STOP TRADE -----------------")
        self.logger.info("------------------------------------------------")
        self.running_flag = False
        if self.__primary_exchange_thread is not None:
            self.__primary_exchange_thread.stop_job()
        if self.__secondary_exchange_thread is not None:
            self.__secondary_exchange_thread.stop_job()

        self.init_process_trade = False

    def worker_handler(self):
        try:
            while True:
                print("Check data", self.running_flag, TraderAgent.running_flag)
                if not self.running_flag:

                    print("Process sleeping...")
                    sleep(1)
                else:
                    primary_queue = None
                    secondary_queue = None
                    while self.running_flag:
                        if not self.init_process_trade:
                            primary_queue = Queue()
                            secondary_queue = Queue()
                            self.__primary_exchange_thread = ExchangeThread(primary_queue, True)
                            self.__secondary_exchange_thread = ExchangeThread(secondary_queue, False)

                            self.__primary_exchange_thread.start_job(primary_queue)
                            self.__secondary_exchange_thread.start_job(secondary_queue)
                            self.init_process_trade = True

                        if not primary_queue.empty() and not secondary_queue.empty():
                            primary_msg = primary_queue.get()
                            secondary_msg = secondary_queue.get()

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

                            coin_trade = self.__ccxt_manager.get_coin_trade()
                            ccxt_primary = self.__ccxt_manager.get_ccxt(True)
                            ccxt_secondary = self.__ccxt_manager.get_ccxt(False)
                            if primary_buy_price > 1.01 * secondary_sell_price:
                                quantity = min(
                                    min(
                                        primary_buy_price * primary_buy_quantity,
                                        secondary_sell_price * secondary_sell_quantity,
                                        primary_amount_usdt,
                                        secondary_amount_usdt) / primary_buy_price, primary_amount_coin, secondary_amount_coin)

                                primary_order = ccxt_primary.create_limit_sell_order(coin_trade,
                                                                                     quantity,
                                                                                     primary_buy_price)
                                secondary_order = ccxt_secondary.create_limit_buy_order(coin_trade,
                                                                                        quantity,
                                                                                        secondary_sell_price)

                            elif secondary_buy_price > 1.01 * primary_sell_price:
                                quantity = min(
                                    min(secondary_buy_price * secondary_buy_quantity,
                                        primary_sell_price * primary_sell_quantity,
                                        secondary_amount_usdt,
                                        primary_amount_usdt) / secondary_buy_price, secondary_amount_coin,
                                    primary_amount_coin)
                                primary_order = ccxt_primary.create_limit_buy_order(coin_trade,
                                                                                    quantity,
                                                                                    primary_sell_price)
                                secondary_order = ccxt_secondary.create_limit_sell_order(coin_trade,
                                                                                         quantity,
                                                                                         secondary_buy_price)
                        else:
                            sleep(10)

        except Exception as ex:
            print("TraderAgent.worker_handler::".format(ex.__str__()))

        
