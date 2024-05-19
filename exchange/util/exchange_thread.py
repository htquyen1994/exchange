from datetime import time
from threading import Thread
from time import sleep
from time import gmtime, strftime


class ExchangeThread:
    thread = None
    logger = None
    __is_initialize = False
    # __queue = None
    __is_primary = None
    # __ccxt_manager = None
    # __ccxt_exchange = None

    def __init__(self, queue, is_primary):
        self.is_running = False
        self.__is_initialize = False
        self.__queue = queue
        self.__is_primary = is_primary
        # self.__ccxt_manager = CcxtManager.get_instance()
        # self.__ccxt_exchange = self.__ccxt_manager.get_ccxt(self.__is_primary)

    def start_job(self, shared_ccxt_manager):
        if not self.is_running:
            self.is_running = True
            print("Init job, " + str(" {}").format(self.__is_primary))
            self.thread = Thread(target=self.job_function, args=(self.__queue, shared_ccxt_manager, self.__is_primary))
            self.thread.start()
            print("Job started successfully")
        else:
            print("Job is already running")

    def stop_job(self):
        if self.is_running:
            self.is_running = False
            print("Job stopping...")
            self.thread.join()
            print("Job stopped successfully")
        else:
            print("Job is not running")

    def job_function(self, queue, shared_ccxt_manager, is_primary):
        while self.is_running:
            try:
                param_object = {}
                ccxt = shared_ccxt_manager.get_ccxt(is_primary)
                coin = shared_ccxt_manager.get_coin_trade()
                orderbook = ccxt.fetch_order_book(coin)
                param_object['order_book'] = orderbook
                balance = ccxt.fetch_balance()
                name_process = 'Primary exchange'
                if not is_primary:
                    name_process = 'Second exchange'
                print("=====Execute balance {0}: {1}".format(name_process, strftime("%Y-%m-%d %H:%M:%S", gmtime())))
                if balance is not None and balance['total'] is not None:
                    param_object['balance'] = {}
                    param_object['balance']['amount_usdt'] = float(0)
                    param_object['balance']['amount_coin'] = float(0)
                    for currency, amount in balance['total'].items():
                        if currency == "USDT":
                            param_object['balance']['amount_usdt'] = float(amount)
                        if currency == coin.split('/')[0]:
                            param_object['balance']['amount_coin'] = float(amount)

                    if shared_ccxt_manager.get_simulator() == 1:
                        param_object['balance']['amount_usdt'] = 250
                        param_object['balance']['amount_coin'] = 250

                    # queue.put(param_object)
                    put_queue_latest_value(queue, param_object)
            except Exception as ex:
                sleep(1)
                print("====> ExchangeThread.job_function::", str.__str__(ex))


def put_queue_latest_value(q, value):
    if not q.full():
        q.put(value)
    else:
        q.get()
        q.put(value)

