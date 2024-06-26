import datetime
import math
import multiprocessing
import time
from multiprocessing import Process, Event, Queue
from time import sleep
from exchange.util.ccxt_manager import CcxtManager
from exchange.util.exchange_pending_thread import ExchangePendingThread
from exchange.util.exchange_thread import ExchangeThread
import uuid
import telebot
from time import gmtime, strftime

from exchange.util.log_agent import LoggerAgent
from exchange.util.sync_core.exchange_factory import ExchangeFactory

CHAT_ID = "-4254987506"
current_time_checked = datetime.datetime.now()


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
        self.start_event.clear()

    def stop_worker(self):
        try:
            self.start_flag = False
            self.process.join()
            self.process.daemon = True
            self.process = None
            print("Stop worker")
        except Exception as ex:
            print("TraderAgent.worker_handler::".format(ex.__str__()))

    def set_config_trade(self, primary_exchange, secondary_exchange, coin, rotation_coin,
                         rotation_usdt, total_coin, total_usdt):
        ccxt = CcxtManager.get_instance()
        ccxt.set_configure(primary_exchange, secondary_exchange, coin, rotation_coin,
                           rotation_usdt, total_coin, total_usdt)
        self.queue_config.put(ccxt)

    def do_work(self, queue_config, logger):
        bot = telebot.TeleBot("7480119894:AAHVUyPGucEGxEUeEKJIAQw1VEDYlZ1dqMA")
        current_time = datetime.datetime.now()

        while True:
            initialize = False
            shared_ccxt_manager = None
            while self.start_event.is_set():
                try:
                    if not initialize and not queue_config.empty():
                        shared_ccxt_manager = queue_config.get()
                        initialize = True
                    print("=====Execute time main {0}".format(strftime("%Y-%m-%d %H:%M:%S", gmtime())))
                    if check_invalid_balance_exchange(shared_ccxt_manager):
                        print("---Has to sync data---")
                        handle_sync_exchange(bot, shared_ccxt_manager)
                    else:
                        sleep(2)
                        try:
                            if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                                bot.send_message(CHAT_ID, "Checking balance")
                                current_time = datetime.datetime.now()
                            else:
                                sleep(1)
                        except Exception as ex:
                            print("Send chat box error".format(ex))

                except Exception as ex:
                    print("Error:  {}".format(ex))
                    try:
                        if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                            bot.send_message(CHAT_ID, "Error manager")
                            current_time = datetime.datetime.now()
                        else:
                            sleep(1)
                    except Exception as ex:
                        print("Send chat box error".format(ex))

            if not self.start_event.is_set():
                try:
                    print("Stop sync")
                    if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                        bot.send_message(CHAT_ID, "Trading is not start")
                        current_time = datetime.datetime.now()
                except Exception as ex:
                    print("Send chat box error".format(ex))
            sleep(1)
            print("Process is stopped")
            # logger.info("Process is running")
            try:
                if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                    bot.send_message(CHAT_ID, "Process is stopped")
                    current_time = datetime.datetime.now()
            except Exception as ex:
                # logger.info("Send chat box error".format(ex))
                print("Send tele is error")


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
        return param_object
    return None


def handle_sync_exchange(bot, shared_ccxt_manager):
    try:
        bot.send_message(CHAT_ID, "--------START TRANSFER COIN/USDT-----")
        symbol = shared_ccxt_manager.get_coin_trade()
        currency = symbol.split('/')[0]
        rotation_coin = shared_ccxt_manager.rotation_coin
        rotation_usdt = shared_ccxt_manager.rotation_usdt
        # total_coin = shared_ccxt_manager.total_coin
        # total_usdt = shared_ccxt_manager.total_usdt

        exchange_primary = shared_ccxt_manager.get_exchange(True)
        exchange_secondary = shared_ccxt_manager.get_exchange(False)
        ccxt_primary = shared_ccxt_manager.get_ccxt(True)
        ccxt_secondary = shared_ccxt_manager.get_ccxt(False)

        # Check before withdraw
        time_since = str(int((time.time() - 180) * 1000))
        primary_withdrawals_coin = ccxt_primary.fetch_withdrawals(currency, time_since)
        secondary_withdrawals_coin = ccxt_secondary.fetch_withdrawals(currency, time_since)
        primary_withdrawals_usdt = ccxt_primary.fetch_withdrawals('USDT', time_since)
        secondary_withdrawals_usdt = ccxt_secondary.fetch_withdrawals('USDT', time_since)
        if (len(primary_withdrawals_usdt) > 0
                or len(secondary_withdrawals_usdt) > 0
                or len(primary_withdrawals_coin) > 0
                or len(secondary_withdrawals_coin) > 0):
            print("Đang có lệnh chuyển tiền")
            bot.send_message(CHAT_ID, "Đang có tồn tại có lệnh chuyển COIN/USDT")
            return

        primary_sync = ExchangeFactory.create_exchange(exchange_primary.exchange_code,
                                                       exchange_primary.private_key,
                                                       exchange_primary.secret_key,
                                                       exchange_primary.password)
        secondary_sync = ExchangeFactory.create_exchange(exchange_secondary.exchange_code,
                                                         exchange_secondary.private_key,
                                                         exchange_secondary.secret_key,
                                                         exchange_secondary.password)
        # lấy lại tổng giá coin và usdt 2 sàn
        primary_msg = get_balance(shared_ccxt_manager, True)
        secondary_msg = get_balance(shared_ccxt_manager, False)

        primary_balance = primary_msg['balance']
        primary_amount_usdt_temp = primary_balance['amount_usdt']
        primary_amount_coin_temp = primary_balance['amount_coin']

        secondary_balance = secondary_msg['balance']
        secondary_amount_usdt_temp = secondary_balance['amount_usdt']
        secondary_amount_coin_temp = secondary_balance['amount_coin']

        # Tiếp tục transfer coin và usdt giữa các sàn

        current_coin_total = primary_amount_coin_temp + secondary_amount_coin_temp
        current_usdt_total = primary_amount_usdt_temp + secondary_amount_usdt_temp

        # Số lượng coin và usdt sau khi transfer giữa các sàn
        after_primary_coin = math.floor(rotation_coin * current_coin_total / 100)
        after_secondary_coin = math.floor(current_coin_total - after_primary_coin)
        after_primary_usdt = math.floor(rotation_usdt * current_usdt_total / 100)
        after_secondary_usdt = math.floor(current_usdt_total - after_primary_usdt)

        print("===============================================================")
        print("Tổng coin 2 sàn: {0}".format(current_coin_total))
        print("Tổng usdt 2 sàn: {0}".format(current_usdt_total))

        print("Coin Primary trước và sau \n {0} ---- {1}".format(primary_amount_coin_temp, after_primary_coin))
        print("Coin Secondary trước và sau \n {0} ---- {1}".format(secondary_amount_coin_temp, after_secondary_coin))
        print("USDT Primary trước và sau \n {0} ---- {1}".format(primary_amount_usdt_temp, after_primary_usdt))
        print("USDT Secondary trước và sau \n {0} ---- {1}".format(secondary_amount_usdt_temp, after_secondary_usdt))
        #  Bắt đầu chuyển coin và usdt

        usdt_withdraw_id = None
        coin_withdraw_id = None
        # SEND COIN
        if primary_amount_coin_temp > after_primary_coin:
            transfer_quantity = primary_amount_coin_temp - after_primary_coin
            payload = {
                'chain': exchange_primary.chain_coin,
                'address': exchange_secondary.address_coin,
                'amount': transfer_quantity,
                'coin': currency
            }
            coin_withdraw_id = primary_sync.withdraw(payload)
            print("COIN từ primary -> secondary \n {0}".format(transfer_quantity))
            bot.send_message(CHAT_ID, "Thực hiện chuyển coin từ {0} => {1} : {2}"
                             .format(exchange_primary.exchange_code,
                                     exchange_secondary.exchange_code,
                                     transfer_quantity))
        elif secondary_amount_coin_temp > after_secondary_coin:
            transfer_quantity = secondary_amount_coin_temp - after_secondary_coin
            payload = {
                'chain': exchange_secondary.chain_coin,
                'address': exchange_primary.address_coin,
                'amount': transfer_quantity,
                'coin': currency
            }
            coin_withdraw_id = secondary_sync.withdraw(payload)
            print("COIN từ secondary -> primary \n {0}".format(transfer_quantity))
            bot.send_message(CHAT_ID, "Thực hiện chuyển coin từ {0} => {1} : {2}"
                             .format(exchange_secondary.exchange_code, exchange_primary.exchange_code,
                                     transfer_quantity))

        # Send USDT
        if primary_amount_usdt_temp > after_primary_usdt:
            transfer_quantity = primary_amount_usdt_temp - after_primary_usdt
            payload = {
                'chain': exchange_primary.chain_usdt,
                'address': exchange_secondary.address_usdt,
                'amount': transfer_quantity,
                'coin': 'USDT'
            }
            usdt_withdraw_id = primary_sync.withdraw(payload)
            bot.send_message(CHAT_ID, "Thực hiện chuyển USDT từ {0} => {1} : {2}"
                             .format(exchange_primary.exchange_code,
                                     exchange_secondary.exchange_code,
                                     transfer_quantity))
            print("USDT từ primary -> secondary \n {0}".format(transfer_quantity))
        elif secondary_amount_usdt_temp > after_secondary_usdt:
            transfer_usdt_primary = False
            transfer_quantity = secondary_amount_usdt_temp - after_secondary_usdt
            payload = {
                'chain': exchange_secondary.chain_usdt,
                'address': exchange_primary.address_usdt,
                'amount': transfer_quantity,
                'coin': 'USDT'
            }
            usdt_withdraw_id = secondary_sync.withdraw(payload)
            print("USDT từ secondary -> primary \n {0}".format(transfer_quantity))
            bot.send_message(CHAT_ID, "Thực hiện chuyển USDT từ {0} => {1} : {2}"
                             .format(exchange_secondary.exchange_code,
                                     exchange_primary.exchange_code,
                                     transfer_quantity))

        # ===============================================================================
        bot.send_message(CHAT_ID, "Bắt đầu thực hiện quá trình kiểm tra chuyển COIN/USDT")
        # ===============================================================================

        if coin_withdraw_id is None:
            bot.send_message(CHAT_ID, "Lệnh chuyển COIN không thành công -> xảy ra vấn đề gọi lệnh")

        elif usdt_withdraw_id is None:
            bot.send_message(CHAT_ID, "Lệnh chuyển USDT không thành công -> xảy ra vấn đề gọi lệnh")
        else:
            count_check = 0
            while count_check < 1200:
                count_check = count_check + 1
                sleep(1)
                invalid = check_invalid_balance_exchange(shared_ccxt_manager)
                bot.send_message(CHAT_ID, "Đã thực hiện chuyển. Đang quá trình chờ kiểm tra")
                if not invalid:
                    bot.send_message(CHAT_ID, "Hoàn thành chuyển COIN/USDT")
                    count_check = 1201
    except Exception as ex:
        print("Có lỗi chuyển USDT và coin: {0}".format(ex))
        bot.send_message(CHAT_ID, "Có lỗi chuyển USDT và coin: {0}".format(ex))


def find_record_by_id(data, record_id):
    for record in data:
        if record['id'] == record_id:
            return record
    return None


def check_invalid_balance_exchange(shared_ccxt_manager):
    primary_msg = get_balance(shared_ccxt_manager, True)
    secondary_msg = get_balance(shared_ccxt_manager, False)
    if primary_msg is not None and secondary_msg is not None:
        # primary exchange
        primary_buy_price = primary_msg['order_book']['bids'][0][0]
        primary_balance = primary_msg['balance']
        primary_amount_usdt = primary_balance['amount_usdt']
        primary_amount_coin = primary_balance['amount_coin']

        # secondary exchange
        secondary_buy_price = secondary_msg['order_book']['bids'][0][0]
        secondary_balance = secondary_msg['balance']
        secondary_amount_usdt = secondary_balance['amount_usdt']
        secondary_amount_coin = secondary_balance['amount_coin']

        temp1 = (secondary_amount_coin * secondary_buy_price) < 10
        temp2 = (primary_amount_coin * primary_buy_price) < 10
        if secondary_amount_usdt < 10 or primary_amount_usdt < 10 or temp1 or temp2:
            return True
    return False
