from datetime import time
from threading import Thread
from time import sleep
from time import gmtime, strftime
from exchange.util.ccxt_manager import CcxtManager
import telebot


initialize = False
CHAT_ID = "-4256093220"


class ExchangePendingThread:
    thread = None
    __is_initialize = False
    __ccxt_manager = None
    __queue = None
    bot = None

    def __init__(self, queue):
        self.is_running = False
        self.__is_initialize = False
        self.__ccxt_manager = CcxtManager.get_instance()
        self.__queue = queue
        self.bot = telebot.TeleBot("6331463036:AAF5L45My0A17fNI01HrBwQeYWhtnX0ZIzc")

    def start_job(self, shared_ccxt_manager):
        if not self.is_running:
            self.is_running = True
            self.thread = Thread(target=self.job_function,  args=(self.__queue, shared_ccxt_manager))
            self.thread.start()
            print("------------------ START THREAD (ExchangePendingThread)------------------ ")
        else:
            print("------------------ THREAD (ExchangePendingThread) is running------------------ ")

    def stop_job(self):
        if self.is_running:
            self.is_running = False
            self.thread.join()

    def job_function(self, q, shared_ccxt_manager):
        while self.is_running:
            try:
                if not q.empty():
                    sleep(2)
                    symbol = shared_ccxt_manager.get_coin_trade()
                    # symbol = coin_trade + "/USDT"
                    order_transaction = q.get()
                    order_id = order_transaction.order_id
                    exchange = shared_ccxt_manager.instance.get_ccxt(order_transaction.is_primary)
                    if exchange and order_id:
                        order_status = exchange.fetch_order(order_id, symbol)
                        if order_status['status'] == 'closed':
                            print("===> Lệnh đã được thực hiện thành công: ", order_status)
                            msg = "Command success: \n {0}".format(order_status)
                            self.bot.send_message(CHAT_ID, msg)

                        elif order_status['status'] == 'open':
                            result = exchange.cancel_order(order_id, symbol)
                            msg = "Command cancel: \n {0}".format(order_status)
                            self.bot.send_message(CHAT_ID, msg)
                        else:
                            msg = "Command failed or cancel: \n {0}".format(order_status)
                            self.bot.send_message(CHAT_ID, msg)
                else:
                    sleep(2)
            except Exception as ex:
                sleep(1)
                print("ExchangePendingThread.job_function::".format(ex.__str__()))
