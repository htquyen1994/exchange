import datetime
import math
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
from exchange.util.sync_core.exchange_factory import ExchangeFactory

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
        bot = telebot.TeleBot("6331463036:AAF5L45My0A17fNI01HrBwQeYWhtnX0ZIzc")
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
                    primary_msg = get_balance(shared_ccxt_manager, True)
                    secondary_msg = get_balance(shared_ccxt_manager, False)

                    if primary_msg is not None and secondary_msg is not None:
                        try:
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
                            precision_invalid = False

                            # TEST
                            handle_sync_exchange(bot,
                                                 shared_ccxt_manager,
                                                 primary_amount_usdt,
                                                 secondary_amount_usdt,
                                                 primary_amount_coin,
                                                 secondary_amount_coin,
                                                 primary_buy_price,
                                                 secondary_buy_price)

                            temp1 = (secondary_amount_coin * secondary_buy_price) < 5
                            temp2 = (primary_amount_coin * primary_buy_price) < 5
                            if secondary_amount_usdt < 5 or primary_amount_usdt < 5 or temp1 or temp2:
                                precision_invalid = True
                            # elif primary_buy_price > 1.006 * secondary_sell_price:
                            #     quantity = min(
                            #         min(
                            #             primary_buy_price * primary_buy_quantity,
                            #             secondary_sell_price * secondary_sell_quantity,
                            #             primary_amount_usdt,
                            #             secondary_amount_usdt) / primary_buy_price, primary_amount_coin,
                            #         secondary_amount_coin)
                            #     precision_invalid = (quantity * primary_buy_price) < 5 or (
                            #             quantity * secondary_sell_price) < 5
                            # elif secondary_buy_price > 1.006 * primary_sell_price:
                            #     quantity = min(
                            #         min(secondary_buy_price * secondary_buy_quantity,
                            #             primary_sell_price * primary_sell_quantity,
                            #             secondary_amount_usdt,
                            #             primary_amount_usdt) / secondary_buy_price, secondary_amount_coin,
                            #         primary_amount_coin)
                            #     precision_invalid = (quantity * secondary_buy_price) < 5 or (
                            #             quantity * primary_sell_price) < 5
                            # if precision_invalid:
                            #     handle_sync_exchange(bot,
                            #                          shared_ccxt_manager,
                            #                          primary_amount_usdt,
                            #                          secondary_amount_usdt,
                            #                          primary_amount_coin,
                            #                          secondary_amount_coin,
                            #                          primary_buy_price,
                            #                          secondary_buy_price)
                            else:
                                sleep(1)
                                try:
                                    if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                                        bot.send_message(CHAT_ID, "Sync exchange is running")
                                        current_time = datetime.datetime.now()
                                except Exception as ex:
                                    print("Error:  {}".format(ex))
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
                try:
                    if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                        bot.send_message(CHAT_ID, "Trading is not start")
                        current_time = datetime.datetime.now()
                except Exception as ex:
                    logger.info("Send chat box error".format(ex))
            sleep(1)
            print("Process is stopped")
            logger.info("Process is running")
            try:
                if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                    bot.send_message(CHAT_ID, "Process is stopped")
                    current_time = datetime.datetime.now()
            except Exception as ex:
                logger.info("Send chat box error".format(ex))


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


def handle_sync_exchange(bot, shared_ccxt_manager, primary_amount_usdt, secondary_amount_usdt, primary_amount_coin,
                         secondary_amount_coin, primary_sell_price, secondary_sell_price):
    try:

        symbol = shared_ccxt_manager.get_coin_trade()
        currency = symbol.split('/')[0]
        rotation_coin = shared_ccxt_manager.rotation_coin
        rotation_usdt = shared_ccxt_manager.rotation_usdt
        total_coin = shared_ccxt_manager.total_coin
        total_usdt = shared_ccxt_manager.total_usdt

        exchange_primary = shared_ccxt_manager.get_exchange(True)
        exchange_secondary = shared_ccxt_manager.get_exchange(False)
        ccxt_primary = shared_ccxt_manager.get_ccxt(True)
        ccxt_secondary = shared_ccxt_manager.get_ccxt(False)
        primary_sync = ExchangeFactory.create_exchange(exchange_primary.exchange_code,
                                                       exchange_primary.private_key,
                                                       exchange_primary.secret_key,
                                                       exchange_primary.password)
        secondary_sync = ExchangeFactory.create_exchange(exchange_secondary.exchange_code,
                                                         exchange_secondary.private_key,
                                                         exchange_secondary.secret_key,
                                                         exchange_secondary.password)

        # Xử lý chỉ mua hoặc bán sàn mỗi bên
        result = total_coin > ((secondary_amount_coin + primary_amount_coin) + round(10 / secondary_sell_price))
        # TEST
        result = False
        if result:
            bot.send_message(CHAT_ID, "===Chênh lệch lệnh mua bán====")
            status = False
            is_primary_sync = False
            quantity = total_coin - (secondary_amount_coin + primary_amount_coin)
            order_command = None
            if secondary_amount_coin > primary_amount_coin:
                # order_command = ccxt_secondary.create_limit_buy_order(symbol, quantity, secondary_sell_price)
                order_command = ccxt_secondary.create_market_buy_order(symbol, quantity)
            else:
                is_primary_sync = True
                # order_command = ccxt_primary.create_limit_buy_order(symbol, quantity, primary_sell_price)
                order_command = ccxt_primary.create_market_buy_order(symbol, quantity)

            name = exchange_primary.exchange_code if is_primary_sync else exchange_secondary.exchange_code
            msg = "Thực hiện mua coin ở sàn {0} với số lượng {1} => START".format(name, quantity)
            bot.send_message(CHAT_ID, msg)
            count_retry = 0
            while count_retry < 5:
                msg = "Kiểm tra mua coin ở sàn {0} với số lượng {1} ==> PENDING".format(name, quantity)
                bot.send_message(CHAT_ID, msg)
                order_status = None
                count_retry = count_retry + 1
                if is_primary_sync:
                    order_status = ccxt_primary.fetch_order(order_command['id'], symbol)
                else:
                    order_status = ccxt_secondary.fetch_order(order_command['id'], symbol)
                if order_status['status'] == 'closed':
                    status = True
                    count_retry = 5
                sleep(1)

            if status:
                msg = "Thực hiện mua coin ở sàn {0} với số lượng {1} ==> SUCCESS".format(name, quantity)
                bot.send_message(CHAT_ID, msg)
            else:
                if is_primary_sync:
                    ccxt_primary.cancel_order(order_command['id'], symbol)
                    msg = "Kiểm tra mua coin ở sàn {0} với số lượng {1} ==> CANCELED".format(name, quantity)
                    bot.send_message(CHAT_ID, msg)
                    return
                else:
                    ccxt_secondary.cancel_order(order_command['id'], symbol)
                    msg = "Kiểm tra mua coin ở sàn {0} với số lượng {1} ==> CANCELED".format(name, quantity)
                    bot.send_message(CHAT_ID, msg)
                    return

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

        #  Bắt đầu chuyển coin và usdt

        is_transfer_coin_at_primary = True
        is_transfer_usdt_at_primary = True
        result_transfer_coin = None
        result_transfer_usdt = None
        if 1==1: #primary_amount_coin_temp > after_primary_coin
            # transfer_quantity = primary_amount_coin_temp - after_primary_coin
            transfer_quantity = 100
            payload = {
                'chain': exchange_primary.chain_coin,
                'address': exchange_secondary.address_coin,
                'amount': transfer_quantity,
                'coin': currency
            }
            result_transfer_coin = primary_sync.withdraw(payload)
            bot.send_message(CHAT_ID, "Thực hiện chuyển coin từ {0} => {1} : {2}".format(exchange_primary.exchange_code,
                                                                                         exchange_secondary.exchange_code,
                                                                                         transfer_quantity))

        elif 1 == 1: #secondary_amount_coin_temp > after_secondary_coin
            is_transfer_coin_at_primary = False
            # transfer_quantity = secondary_amount_coin_temp - after_secondary_coin
            transfer_quantity = 100
            payload = {
                'chain': exchange_secondary.chain_coin,
                'address': exchange_primary.address_coin,
                'amount': transfer_quantity,
                'coin': currency
            }
            result_transfer_coin = secondary_sync.withdraw(payload)
            bot.send_message(CHAT_ID, "Thực hiện chuyển coin từ {0} => {1} : {2}"
                             .format(exchange_secondary.exchange_code, exchange_primary.exchange_code, transfer_quantity))

        elif primary_amount_usdt_temp > after_primary_usdt:
            # transfer_quantity = primary_amount_usdt_temp - after_primary_usdt
            transfer_quantity = 5
            payload = {
                'chain': exchange_primary.chain_usdt,
                'address': exchange_secondary.address_usdt,
                'amount': transfer_quantity,
                'coin': 'USDT'
            }
            result_transfer_usdt = primary_sync.withdraw(payload)
            bot.send_message(CHAT_ID, "Thực hiện chuyển USDT từ {0} => {1} : {2}".format(exchange_primary.exchange_code,
                                                                                         exchange_secondary.exchange_code,
                                                                                         transfer_quantity))
        elif secondary_amount_usdt_temp > after_secondary_usdt:
            is_transfer_usdt_at_primary = False
            # transfer_quantity = secondary_amount_usdt_temp - after_secondary_usdt
            transfer_quantity = 5
            payload = {
                'chain': exchange_secondary.chain_usdt,
                'address': exchange_primary.address_usdt,
                'amount': transfer_quantity,
                'coin': 'USDT'
            }
            result_transfer_usdt = secondary_sync.withdraw(payload)
            bot.send_message(CHAT_ID,
                             "Thực hiện chuyển USDT từ {0} => {1} : {2}".format(exchange_secondary.exchange_code,
                                                                                exchange_primary.exchange_code,
                                                                                transfer_quantity))

        # ===============================================================================
        bot.send_message(CHAT_ID, "Bắt đầu thực hiện quá trình kiểm tra chuyển COIN/USDT")
        # ===============================================================================
        order_coin_id = None
        order_usdt_id = None
        if result_transfer_coin is not None:
            if result_transfer_coin.success:
                order_coin_id = result_transfer_coin.id
            else:
                bot.send_message(CHAT_ID, "Lệnh chuyển COIN không thành công -> xảy ra vấn đề gọi lệnh")
        if result_transfer_usdt is not None:
            if result_transfer_usdt.success:
                order_usdt_id = result_transfer_usdt.id
            else:
                bot.send_message(CHAT_ID, "Lệnh chuyển USDT không thành công -> xảy ra vấn đề gọi lệnh")

        if order_coin_id is not None or order_usdt_id is not None:
            count = False
            time_check = 0
            while count < 2:
                sleep(1)
                time_check = time_check + 1
                if time_check > 600:
                    count = 2
                if order_coin_id:
                    if is_transfer_coin_at_primary:
                        result = primary_sync.get_withdraw_list(order_coin_id)
                    else:
                        result = secondary_sync.get_withdraw_list(order_coin_id)
                    if result.success:
                        if result.command == 2:
                            bot.send_message(CHAT_ID, "Thực hiện chuyển COIN hoàn thành: {0}".format(result.status))
                            count = count + 1
                        else:
                            bot.send_message(CHAT_ID, "Thực hiện chuyển COIN đang trong quá trình: {0}".format(
                                result.status))
                    else:
                        bot.send_message(CHAT_ID, "Lệnh kiểm tra transfer không thành công")
                if order_usdt_id:
                    if is_transfer_usdt_at_primary:
                        result = primary_sync.get_withdraw_list(order_usdt_id)
                    else:
                        result = secondary_sync.get_withdraw_list(order_usdt_id)
                    if result.success:
                        if result.command == 2:
                            bot.send_message(CHAT_ID, "Thực hiện chuyển USDT hoàn thành: {0}".format(result.status))
                            count = count + 1
                        else:
                            bot.send_message(CHAT_ID, "Thực hiện chuyển USDT đang trong quá trình: {0}".format(
                                result.status))
                    else:
                        bot.send_message(CHAT_ID, "Lệnh kiểm tra transfer không thành công")
                        print("Lệnh kiểm tra transfer không thành công")

        else:
            bot.send_message(CHAT_ID, "Lệnh chuyển USDT/COIN không thành công -> xảy ra vấn đề gọi lệnh")

    except Exception as ex:
        print("Lỗi chuyển USDT và coin: {0}".format(ex))
        bot.send_message(CHAT_ID, "Lỗi chuyển USDT và coin: {0}".format(ex))
