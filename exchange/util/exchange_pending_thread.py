from datetime import time
from threading import Thread
from time import sleep
from time import gmtime, strftime

from config.config import ExchangesCode
from exchange.util.ccxt_manager import CcxtManager
import telebot

initialize = False
CHAT_ID = "-4269611597"


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
            self.thread = Thread(target=self.job_function, args=(self.__queue, shared_ccxt_manager, bot_tele))
            self.thread.start()
            print("------------------ START THREAD (ExchangePendingThread)------------------ ")
        else:
            print("------------------ THREAD (ExchangePendingThread) is running------------------ ")

    def stop_job(self):
        if self.is_running:
            self.is_running = False
            self.thread.join()

    def job_function(self, q, shared_ccxt_manager, bot_tele):
        total_profit = 0
        while self.is_running:
            try:
                if not q.empty():
                    symbol = shared_ccxt_manager.get_coin_trade()
                    order_transaction = q.get()
                    primary_transaction = order_transaction['primary']
                    secondary_transaction = order_transaction['secondary']
                    primary_ccxt_manager = shared_ccxt_manager.get_ccxt(True)
                    secondary_ccxt_manager = shared_ccxt_manager.get_ccxt(False)
                    primary_exchange_code = shared_ccxt_manager.get_exchange(True).exchange_code
                    secondary_exchange_code = shared_ccxt_manager.get_exchange(False).exchange_code
                    count = 0
                    while count < 1:
                        count = count + 1
                        sleep(4)
                        try:
                            primary_order_status = None
                            if shared_ccxt_manager.get_exchange(True).exchange_code == ExchangesCode.BYBIT.value:
                                primary_order_status = primary_ccxt_manager.fetch_open_order(
                                    primary_transaction.order_id, symbol)
                                print("Lệnh open bybit ==> {0}".format(primary_order_status))
                                if primary_order_status is None:
                                    primary_order_status = primary_ccxt_manager.fetch_closed_order(
                                        primary_transaction.order_id, symbol)
                                    print("Lệnh closed bybit ==> {0}".format(primary_order_status))
                            else:
                                primary_order_status = primary_ccxt_manager.fetch_order(primary_transaction.order_id,
                                                                                    symbol)
                            secondary_order_status = secondary_ccxt_manager.fetch_order(secondary_transaction.order_id,
                                                                                        symbol)

                            # TODO after if secondary exchange is a bybit
                            # if shared_ccxt_manager.get_exchange(False).exchange_code == ExchangesCode.BYBIT.value:
                            #     secondary_order_status = secondary_ccxt_manager.fetch_open_order(
                            #         primary_transaction.order_id, symbol)
                            #     if secondary_order_status is None:
                            #         secondary_order_status = secondary_ccxt_manager.fetch_closed_order(
                            #             primary_transaction.order_id, symbol)

                            filled_primary = primary_order_status['filled']
                            filled_secondary = secondary_order_status['filled']
                            price_primary = primary_order_status['price']
                            price_secondary = secondary_order_status['price']
                            side_primary = primary_order_status['side']
                            side_secondary = secondary_order_status['side']
                            cost_primary = get_total_cost(primary_exchange_code, primary_order_status)
                            cost_secondary = get_total_cost(secondary_exchange_code, secondary_order_status)
                            if primary_order_status['status'] == 'closed' and secondary_order_status['status'] == 'closed':
                                profit = 0
                                if side_primary == 'buy' and side_secondary == 'sell':
                                    profit = round((cost_secondary - cost_primary), 4)
                                elif side_secondary == 'buy' and side_primary == 'sell':
                                    profit = round((cost_primary - cost_secondary), 4)
                                total_profit = round((total_profit + profit), 4)
                                bot_tele.send_message(CHAT_ID, "Buy sell success: {0} => total: {1}".format(profit,
                                                                                                            total_profit))
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
                else:
                    sleep(2)
                    # print("Thread cancel order is checking")
            except Exception as ex:
                sleep(1)
                print("ExchangePendingThread.job_function::".format(ex.__str__()))


def get_total_cost(exchange_code, order):
    if exchange_code == ExchangesCode.BINGX.value:
        return float(order['info']['cummulativeQuoteQty'])
    if exchange_code == ExchangesCode.GATE.value:
        return float(order['info']['filled_total'])
    if exchange_code == ExchangesCode.BYBIT.value:
        return float(order['info']['cumExecValue'])