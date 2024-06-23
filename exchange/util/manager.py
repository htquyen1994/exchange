import datetime
import multiprocessing
from multiprocessing import Process, Event, Queue
from time import sleep

from config.config import ExchangesCode
from exchange.models.order_status import OrderStatus
from exchange.util.ccxt_manager import CcxtManager
from exchange.util.exchange_pending_thread import ExchangePendingThread
from exchange.util.exchange_thread import ExchangeThread
import uuid
import telebot
from time import gmtime, strftime

from exchange.util.log_agent import LoggerAgent

CHAT_ID = "-4262576067"
CHAT_WARNING_ID = "-4277043865"


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
        bot = telebot.TeleBot("6508394630:AAGioVntFAwjr5a3lMZW_Jpx2vaOaNo_PLI")
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

                            # # Cost group
                            # primary_cost_group = calc_order_group(primary_msg['order_book'])
                            # secondary_cost_group = calc_order_group(secondary_msg['order_book'])

                            msg_1 = "Secondary exchange {0} / {1}".format(
                                secondary_amount_usdt,
                                secondary_amount_coin
                            )

                            msg_2 = "Primary exchange {0} / {1}".format(
                                primary_amount_usdt,
                                primary_amount_coin
                            )

                            # print(msg_1)
                            # print(msg_2)

                            coin_trade = shared_ccxt_manager.get_coin_trade()
                            ccxt_primary = shared_ccxt_manager.get_ccxt(True)
                            ccxt_secondary = shared_ccxt_manager.get_ccxt(False)
                            temp1 = (secondary_amount_coin * secondary_buy_price) < 10
                            temp2 = (primary_amount_coin * primary_buy_price) < 10
                            if secondary_amount_usdt < 10 or primary_amount_usdt < 10 or temp1 or temp2:
                                # msg = "Warning exchange {0}/{1}".format(
                                #     shared_ccxt_manager.get_exchange(False).exchange_code,
                                #     shared_ccxt_manager.get_exchange(True).exchange_code
                                # )
                                #
                                # msg = msg + "\n COIN {0} / {1}".format(primary_amount_coin, secondary_amount_coin)
                                # msg = msg + "\n USDT {0} / {1}".format(primary_amount_usdt, secondary_amount_usdt)
                                #
                                # bot.send_message(CHAT_WARNING_ID, msg)
                                # sleep(5)
                                total_coin = float(primary_amount_coin + secondary_amount_coin)
                                total_usdt = float(primary_amount_usdt + secondary_amount_usdt)
                                handle_invalid_balance(bot,
                                                       shared_ccxt_manager,
                                                       total_coin,
                                                       total_usdt)
                                continue
                            # ban san primary (gate) bids, mua secondary (bingx): ask
                            if primary_buy_price > 1.006 * secondary_sell_price:
                                is_command_group = False
                                # Handle group order
                                quantity_group = calc_quantity_group_order(primary_msg['order_book'],
                                                                           secondary_msg['order_book'],
                                                                           False)

                                quantity = min(min(
                                    min(
                                        primary_buy_price * quantity_group['quantity'],
                                        secondary_sell_price * quantity_group['quantity']) / primary_buy_price,
                                    primary_amount_coin,
                                    secondary_amount_coin),
                                    (min(primary_amount_usdt, secondary_amount_usdt) / secondary_sell_price))

                                cost_group_primary = calc_cost_group_order_by_quantity(primary_msg['order_book'],
                                                                                       quantity,
                                                                                       False)
                                cost_group_secondary = calc_cost_group_order_by_quantity(secondary_msg['order_book'],
                                                                                         quantity,
                                                                                         True)
                                if cost_group_primary > 1.006 * cost_group_secondary:
                                    primary_order = ccxt_primary.create_market_sell_order(coin_trade, quantity)

                                    if shared_ccxt_manager.get_exchange(
                                            False).exchange_code == ExchangesCode.GATE.value:
                                        # ccxt_secondary['options']['createMarketBuyOrderRequiresPrice'] = False
                                        secondary_order = ccxt_secondary.create_market_buy_order(coin_trade,
                                                                                                 cost_group_primary)
                                    else:
                                        secondary_order = ccxt_secondary.create_market_buy_order(coin_trade, quantity)
                                    order_mgs_primary = round(cost_group_primary, 2)
                                    order_mgs_secondary = round(cost_group_secondary, 2)
                                    print("1====> Sell primary, buy secondary {0} => {1}".format(cost_group_primary,
                                                                                                 cost_group_secondary))
                                    print("1====> Sell primary, buy secondary Mua ban quantity {0} => {1}".format(
                                        quantity, round(cost_group_primary - cost_group_secondary, 2)))
                                    primary_pending_order = OrderStatus(True,
                                                                        primary_order['id'],
                                                                        order_mgs_primary)
                                    secondary_pending_order = OrderStatus(False,
                                                                          secondary_order['id'],
                                                                          order_mgs_secondary)

                                    msg_transaction = {'primary': primary_pending_order,
                                                       'secondary': secondary_pending_order}
                                    __pending_queue.put(msg_transaction)
                                    is_command_group = True
                                if not is_command_group:
                                    quantity = max(min(
                                        min(
                                            primary_buy_price * primary_buy_quantity,
                                            secondary_sell_price * secondary_sell_quantity,
                                            primary_amount_usdt,
                                            secondary_amount_usdt) / primary_buy_price, primary_amount_coin,
                                        secondary_amount_coin), (3.1 / secondary_sell_price))
                                    precision_invalid = (quantity * primary_buy_price) < 2 or (
                                            quantity * secondary_sell_price) < 2
                                    if precision_invalid:
                                        msg = "======PRECISION PRICE======\n"
                                        msg = msg + "USDT {0}/{1}\n".format(primary_amount_usdt, secondary_amount_usdt)
                                        msg = msg + "COIN {0}/{1}\n".format(primary_amount_coin, secondary_amount_coin)
                                        msg = msg + "quantity: {0}\n".format(quantity)
                                        msg = msg + "Price buy: {0} => {1}\n".format(primary_buy_price,
                                                                                     quantity * primary_buy_price)
                                        msg = msg + "Second sell: {0} => {1}\n".format(secondary_sell_price,
                                                                                       quantity * primary_buy_price)
                                        bot.send_message(CHAT_WARNING_ID, msg)
                                    else:
                                        print("Buy primary and sell secondary", quantity)
                                        primary_order = ccxt_primary.create_limit_sell_order(coin_trade,
                                                                                             quantity,
                                                                                             primary_buy_price)
                                        secondary_order = ccxt_secondary.create_limit_buy_order(coin_trade,
                                                                                                quantity,
                                                                                                secondary_sell_price)
                                        print("Call 1 => {0} / {1}".format(primary_order['id'], secondary_order['id']))
                                        # handle_exchange_order_transaction(bot,
                                        #                                   ccxt_primary, ccxt_secondary,
                                        #                                   primary_order['id'], secondary_order['id'],
                                        #                                   coin_trade)
                                        order_mgs_primary = round(quantity * primary_buy_price, 2)
                                        order_mgs_secondary = round(quantity * secondary_sell_price, 2)
                                        primary_pending_order = OrderStatus(True,
                                                                            primary_order['id'],
                                                                            order_mgs_primary)
                                        secondary_pending_order = OrderStatus(False,
                                                                              secondary_order['id'],
                                                                              order_mgs_secondary)

                                        msg_transaction = {'primary': primary_pending_order,
                                                           'secondary': secondary_pending_order}
                                        __pending_queue.put(msg_transaction)

                            # Bán sàn bingx, mua gate
                            elif secondary_buy_price > 1.006 * primary_sell_price:
                                is_command_group = False
                                # Handle group order
                                quantity_group = calc_quantity_group_order(primary_msg['order_book'],
                                                                           secondary_msg['order_book'],
                                                                           True)

                                quantity = min(min(
                                    min(
                                        secondary_buy_price * quantity_group['quantity'],
                                        primary_sell_price * quantity_group['quantity']) / secondary_buy_price,
                                    primary_amount_coin,
                                    secondary_amount_coin),
                                    (min(primary_amount_usdt, secondary_amount_usdt) / primary_sell_price))
                                # Bán sàn bingx, mua gate cost_group_secondary
                                cost_group_primary = calc_cost_group_order_by_quantity(primary_msg['order_book'],
                                                                                       quantity,
                                                                                       True)
                                cost_group_secondary = calc_cost_group_order_by_quantity(secondary_msg['order_book'],
                                                                                         quantity,
                                                                                         False)
                                if cost_group_secondary > 1.006 * cost_group_primary:
                                    if shared_ccxt_manager.get_exchange(True).exchange_code == ExchangesCode.GATE.value:
                                        # ccxt_primary['options']['createMarketBuyOrderRequiresPrice'] = False
                                        primary_order = ccxt_primary.create_market_buy_order(coin_trade,
                                                                                             cost_group_primary)
                                    else:
                                        primary_order = ccxt_primary.create_market_buy_order(coin_trade, quantity)
                                    secondary_order = ccxt_secondary.create_market_sell_order(coin_trade, quantity)
                                    order_mgs_primary = round(cost_group_primary, 2)
                                    order_mgs_secondary = round(cost_group_secondary, 2)
                                    print("2====> buy primary, sell secondary {0} => {1}".format(cost_group_primary,
                                                                                                 cost_group_secondary))
                                    print("2====> buy primary, sell secondary Mua ban quantity {0} => {1}".format(
                                        quantity, round(
                                            cost_group_primary - cost_group_secondary, 2)))

                                    primary_pending_order = OrderStatus(True,
                                                                        primary_order['id'],
                                                                        order_mgs_primary)
                                    secondary_pending_order = OrderStatus(False,
                                                                          secondary_order['id'],
                                                                          order_mgs_secondary)

                                    msg_transaction = {'primary': primary_pending_order,
                                                       'secondary': secondary_pending_order}
                                    __pending_queue.put(msg_transaction)
                                    is_command_group = True
                                if not is_command_group:
                                    quantity = max(min(
                                        min(secondary_buy_price * secondary_buy_quantity,
                                            primary_sell_price * primary_sell_quantity,
                                            secondary_amount_usdt,
                                            primary_amount_usdt) / secondary_buy_price, secondary_amount_coin,
                                        primary_amount_coin), (3.1 / primary_sell_price))

                                    precision_invalid = (quantity * secondary_buy_price) < 2 or (
                                            quantity * primary_sell_price) < 2
                                    if precision_invalid:
                                        msg = "======PRECISION PRICE======\n"
                                        msg = msg + "quantity: {0}\n".format(quantity)
                                        msg = msg + "USDT {0}/{1} => {2}\n".format(primary_amount_usdt,
                                                                                   secondary_amount_usdt, (
                                                                                           primary_amount_usdt + secondary_amount_usdt))
                                        msg = msg + "COIN {0}/{1} => {2}\n".format(primary_amount_coin,
                                                                                   secondary_amount_coin, (
                                                                                           primary_amount_coin + secondary_amount_coin))
                                        msg = msg + "Price sell: {0} => {1}\n".format(primary_sell_price,
                                                                                      quantity * primary_sell_price)
                                        msg = msg + "Second buy: {0} => {1}\n".format(secondary_buy_price,
                                                                                      quantity * secondary_buy_price)
                                        bot.send_message(CHAT_WARNING_ID, msg)
                                    else:
                                        print("Sell primary and buy secondary", quantity)
                                        primary_order = ccxt_primary.create_limit_buy_order(coin_trade,
                                                                                            quantity,
                                                                                            primary_sell_price)
                                        secondary_order = ccxt_secondary.create_limit_sell_order(coin_trade,
                                                                                                 quantity,
                                                                                                 secondary_buy_price)
                                        # handle_exchange_order_transaction(bot,
                                        #                                   ccxt_primary, ccxt_secondary,
                                        #                                   primary_order['id'], secondary_order['id'],
                                        #                                   coin_trade)
                                        order_mgs_primary = round(quantity * primary_sell_price, 2)
                                        order_mgs_secondary = round(quantity * secondary_buy_price, 2)
                                        primary_pending_order = OrderStatus(True,
                                                                            primary_order['id'],
                                                                            order_mgs_primary)
                                        secondary_pending_order = OrderStatus(False,
                                                                              secondary_order['id'],
                                                                              order_mgs_secondary)

                                        msg_transaction = {'primary': primary_pending_order,
                                                           'secondary': secondary_pending_order}
                                        __pending_queue.put(msg_transaction)
                                        # __pending_queue.put(secondary_pending_order)

                            else:
                                sleep(0.1)
                                print("Waiting...")
                                if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                                    bot.send_message(CHAT_ID, "Trading status is waiting - not match")
                                    current_time = datetime.datetime.now()
                        except Exception as ex:
                            print("Error manager 0:  {}".format(ex.__str__()))
                            # logger.info("Error manager 1: {0}".format(ex))
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
                    # logger.info("Error manager 2: {0}".format(ex))
                    try:
                        if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                            bot.send_message(CHAT_ID, "Error manager")
                            current_time = datetime.datetime.now()
                        else:
                            sleep(1)
                    except Exception as ex:
                        # logger.info("Send chat box error".format(ex))
                        print("Send chat box error {0}".format(ex))

            if not self.start_event.is_set():
                try:
                    if __pending_thread is not None:
                        __pending_thread.stop_job()

                    if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                        bot.send_message(CHAT_ID, "Trading is not start")
                        current_time = datetime.datetime.now()
                except Exception as ex:
                    # logger.info("Send chat box error".format(ex))
                    print("Send chat box error {0}".format(ex))
            sleep(1)
            print("Process is stopped")
            # logger.info("Process is running")
            try:
                if (datetime.datetime.now() - current_time).total_seconds() >= 300:
                    bot.send_message(CHAT_ID, "Process is stopped")
                    current_time = datetime.datetime.now()
            except Exception as ex:
                print("Send chat box error {0}".format(ex))


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
        return param_object
    return None


def handle_exchange_order_transaction(bot, exchange_primary, exchange_secondary,
                                      primary_order_id, secondary_order_id,
                                      symbol):
    count = 0
    while count < 1:
        count = count + 1
        sleep(1)
        try:
            primary_order_status = exchange_primary.fetch_order(primary_order_id, symbol)
            secondary_order_status = exchange_secondary.fetch_order(secondary_order_id, symbol)
            print("Order status {0} / {1} ".format(primary_order_status['status'], secondary_order_status['status']))
            if primary_order_status['status'] == 'closed' and secondary_order_status['status'] == 'closed':
                bot.send_message(CHAT_ID, "Buy sell success")
                # count = count + 1
                # continue
            else:
                if primary_order_status['status'] == 'open' or primary_order_status is None:
                    result = exchange_primary.cancel_order(primary_order_id, symbol)
                    msg = "Command cancel buy/sell at primary"
                    bot.send_message(CHAT_ID, msg)

                if secondary_order_status['status'] == 'open' or secondary_order_status is None:
                    result = exchange_secondary.cancel_order(secondary_order_id, symbol)
                    msg = "Command cancel buy/sell at secondary"
                    bot.send_message(CHAT_ID, msg)
        except Exception as err:
            print("Error: {0}".format(err))


def send_bot_message_coin(bot, shared_ccxt_manager, heading_title,
                          primary_amount_coin, secondary_amount_coin,
                          primary_amount_usdt, secondary_amount_usdt):
    msg = "{0} {1}/{2}".format(
        heading_title,
        shared_ccxt_manager.get_exchange(False).exchange_code,
        shared_ccxt_manager.get_exchange(True).exchange_code
    )

    msg = msg + "\n COIN {0} / {1}".format(primary_amount_coin, secondary_amount_coin)
    msg = msg + "\n USDT {0} / {1}".format(primary_amount_usdt, secondary_amount_usdt)
    bot.send_message(CHAT_WARNING_ID, msg)


def calc_order_group(order_book):
    loop = min(min(len(order_book['bids']), len(order_book['asks'])), 4)
    index = 0
    cost_buy = 0
    cost_sell = 0
    while index < loop:
        cost_buy = cost_buy + order_book['bids'][index][0] * order_book['bids'][index][1]
        cost_sell = cost_sell + order_book['asks'][index][0] * order_book['asks'][index][1]
        index = index + 1
    return {'cost_sell': cost_sell, 'cost_buy': cost_buy}


def calc_quantity_group_order(order_primary, order_secondary, is_buy_primary):
    quantity_primary = 0
    quantity_secondary = 0
    if is_buy_primary:
        quantity_primary = (
                order_primary['asks'][0][1] + order_primary['asks'][1][1] + order_primary['asks'][2][1] +
                order_primary['asks'][3][1] + order_primary['asks'][4][1]
        )
        quantity_secondary = (
                order_secondary['bids'][0][1] + order_secondary['bids'][1][1] + order_secondary['bids'][2][1] +
                order_secondary['bids'][3][1] + order_secondary['bids'][4][1]
        )
    else:
        quantity_primary = (
                order_primary['bids'][0][1] + order_primary['bids'][1][1] + order_primary['bids'][2][1] +
                order_primary['bids'][3][1] + order_primary['bids'][4][1])
        quantity_secondary = (
                order_secondary['asks'][0][1] + order_secondary['asks'][1][1] + order_secondary['asks'][2][1] +
                order_secondary['asks'][3][1] + order_secondary['asks'][4][1])

    quantity = min(quantity_secondary, quantity_primary)
    return {'quantity': quantity, 'secondary': quantity_secondary, 'primary': quantity_primary}


def calc_cost_group_order(order, is_buy):
    if is_buy:
        return (order['asks'][0][0] * order['asks'][0][1] +
                order['asks'][1][0] * order['asks'][1][1] +
                order['asks'][2][0] * order['asks'][2][1] +
                order['asks'][3][0] * order['asks'][3][1] +
                order['asks'][4][0] * order['asks'][4][1])
    else:
        return (order['bids'][0][0] * order['bids'][0][1] +
                order['bids'][1][0] * order['bids'][1][1] +
                order['bids'][2][0] * order['bids'][2][1] +
                order['bids'][3][0] * order['bids'][3][1] +
                order['bids'][4][0] * order['bids'][4][1])


#
def calc_cost_group_order_by_quantity(order, quantity, is_buy):
    if is_buy:
        ok_q1 = min(order['asks'][0][1], quantity)
        ok_q2 = min(order['asks'][1][1], quantity - ok_q1)
        ok_q3 = min(order['asks'][2][1], quantity - ok_q2 - ok_q1)
        ok_q4 = min(order['asks'][3][1], quantity - ok_q3 - ok_q2 - ok_q1)
        ok_q5 = min(order['asks'][4][1], quantity - ok_q4 - ok_q3 - ok_q2 - ok_q1)
        return (order['asks'][0][0] * ok_q1 +
                order['asks'][1][0] * ok_q2 +
                order['asks'][2][0] * ok_q3 +
                order['asks'][3][0] * ok_q4 +
                order['asks'][4][0] * ok_q5)
    else:
        ok_q1 = min(order['bids'][0][1], quantity)
        ok_q2 = min(order['bids'][1][1], quantity - ok_q1)
        ok_q3 = min(order['bids'][2][1], quantity - ok_q2 - ok_q1)
        ok_q4 = min(order['bids'][3][1], quantity - ok_q3 - ok_q2 - ok_q1)
        ok_q5 = min(order['bids'][4][1], quantity - ok_q4 - ok_q3 - ok_q2 - ok_q1)
        return (order['bids'][0][0] * ok_q1 +
                order['bids'][1][0] * ok_q2 +
                order['bids'][2][0] * ok_q3 +
                order['bids'][3][0] * ok_q4 +
                order['bids'][4][0] * ok_q5)


def handle_invalid_balance(bot, shared_ccxt_manager, total_coin_current, total_usdt_current):
    is_transfer = False
    while not is_transfer:
        try:
            primary_msg = get_balance(shared_ccxt_manager, True)
            secondary_msg = get_balance(shared_ccxt_manager, False)
            if primary_msg is not None and secondary_msg is not None:
                # primary exchange
                primary_balance = primary_msg['balance']
                primary_amount_usdt = primary_balance['amount_usdt']
                primary_amount_coin = primary_balance['amount_coin']

                # secondary exchange
                secondary_balance = secondary_msg['balance']
                secondary_amount_usdt = secondary_balance['amount_usdt']
                secondary_amount_coin = secondary_balance['amount_coin']
                coin_temp = float(secondary_amount_coin + primary_amount_coin)
                usdt_temp = float(secondary_amount_usdt + primary_amount_usdt)

                if coin_temp < 10000:
                    is_transfer = True
                else:
                    msg = "Warning exchange {0}/{1}".format(
                        shared_ccxt_manager.get_exchange(False).exchange_code,
                        shared_ccxt_manager.get_exchange(True).exchange_code
                    )
                    msg = msg + "\n COIN {0} / {1}".format(primary_amount_coin, secondary_amount_coin)
                    msg = msg + "\n USDT {0} / {1}".format(primary_amount_usdt, secondary_amount_usdt)

                    bot.send_message(CHAT_WARNING_ID, msg)
                    sleep(5)
            else:
                sleep(1)
        except Exception as err:
            print("Error: {0}".format(err))

