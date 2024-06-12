from datetime import time
from threading import Thread
from time import sleep
from time import gmtime, strftime
from exchange.util.ccxt_manager import CcxtManager
import telebot


initialize = False
CHAT_ID = "-4262576067"


class ExchangePendingThread:
    thread = None
    __is_initialize = False
    __ccxt_manager = None
    __queue = None
    bot_tele = None

    def __init__(self, queue):
        self.is_running = False
        self.__is_initialize = False
        self.__ccxt_manager = CcxtManager.get_instance()
        self.__queue = queue

    def start_job(self, shared_ccxt_manager, bot_tele):
        if not self.is_running:
            self.is_running = True
            self.thread = Thread(target=self.job_function,  args=(self.__queue, shared_ccxt_manager, bot_tele))
            self.thread.start()
            print("------------------ START THREAD (ExchangePendingThread)------------------ ")
        else:
            print("------------------ THREAD (ExchangePendingThread) is running------------------ ")

    def stop_job(self):
        if self.is_running:
            self.is_running = False
            self.thread.join()

    def job_function(self, q, shared_ccxt_manager, bot_tele):
        total_profit = 14.42
        while self.is_running:
            try:
                if not q.empty():
                    symbol = shared_ccxt_manager.get_coin_trade()
                    order_transaction = q.get()
                    primary_transaction = order_transaction['primary']
                    secondary_transaction = order_transaction['secondary']
                    primary_ccxt_manager = shared_ccxt_manager.get_ccxt(True)
                    secondary_ccxt_manager = shared_ccxt_manager.get_ccxt(False)
                    count = 0
                    while count < 1:
                        count = count + 1
                        sleep(4)
                        try:
                            primary_order_status = primary_ccxt_manager.fetch_order(primary_transaction.order_id, symbol)
                            secondary_order_status = secondary_ccxt_manager.fetch_order(secondary_transaction.order_id, symbol)
                            filled_primary = primary_order_status['filled']
                            filled_secondary = secondary_order_status['filled']
                            price_primary = primary_order_status['price']
                            price_secondary = secondary_order_status['price']
                            cost_primary = primary_order_status['cost']
                            cost_secondary = secondary_order_status['cost']
                            if primary_order_status['status'] == 'closed' and secondary_order_status['status'] == 'closed':
                                profit = abs(round(primary_transaction.total - secondary_transaction.total, 3))
                                total_profit = round((total_profit + profit), 4)
                                bot_tele.send_message(CHAT_ID, "Buy sell success: {0} => total: {1}".format(profit, total_profit))
                            else:
                                msg = "Canceled "
                                if primary_order_status['status'] == 'open':
                                    primary_ccxt_manager.cancel_order(primary_transaction.order_id, symbol)
                                    msg = msg + " primary {0}".format(primary_transaction.total)
                                elif secondary_order_status['status'] == 'open':
                                    secondary_ccxt_manager.cancel_order(secondary_transaction.order_id, symbol)
                                    msg = msg + " secondary {0}".format(secondary_transaction.total)

                                amount = min(filled_primary, filled_secondary)
                                profit = abs(round(amount * price_primary - amount * price_secondary, 4))
                                total_profit = round((total_profit + profit), 4)
                                msg = msg + " => total: {0}".format(total_profit)
                                bot_tele.send_message(CHAT_ID, msg)
                        except Exception as err:
                            print("Error: {0}".format(err))
                    # count = 0
                    # while count < 1:
                    #     try:
                    #         sleep(2)
                    #         count = count + 1
                    #         order_status = ccxt_manager.fetch_order(order_id, symbol)
                    #         print("Order status {0}".format(order_status['status']))
                    #         if order_status['status'] == 'closed':
                    #             bot_tele.send_message(CHAT_ID, "Success: {0}".format(total))
                    #         else:
                    #             if order_status['status'] == 'open':
                    #                 result = ccxt_manager.cancel_order(order_id, symbol)
                    #                 msg = "Canceled: {0}".format(total)
                    #                 bot_tele.send_message(CHAT_ID, msg)
                    #     except Exception as err:
                    #         print("Error: {0}".format(err))
                else:
                    sleep(2)
                    # print("Thread cancel order is checking")
            except Exception as ex:
                sleep(1)
                print("ExchangePendingThread.job_function::".format(ex.__str__()))
