from threading import Thread
from time import sleep
from time import gmtime, strftime
from exchange.util.order_executor import execute_orders_concurrently
from config.config import ExchangesCode, TelegramSetting
from exchange.util.ccxt_manager import CcxtManager
from exchange.util.telegram_utils import send_error_telegram
from config.profit_tracker import load_trading_data, save_trading_data

initialize = False


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
        trading_data = load_trading_data()
        total_profit = trading_data.get("total_profit", 0)    
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

                    sleep(4)
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

                    filled_primary = get_filled_size(primary_exchange_code, primary_order_status)
                    filled_secondary = get_filled_size(secondary_exchange_code, secondary_order_status)
                    price_primary = primary_order_status['price']
                    price_secondary = secondary_order_status['price']
                    side_primary = primary_order_status['side']
                    side_secondary = secondary_order_status['side']
                    amount = min(filled_primary, filled_secondary)
                    if is_order_completed(primary_order_status) and is_order_completed(secondary_order_status):
                        profit = calculate_profit(primary_ccxt_manager, primary_transaction.order_id, secondary_ccxt_manager, secondary_transaction.order_id, symbol)
                        if profit is not None:
                            total_profit = total_profit + profit
                            save_trading_data(total_profit=total_profit)

                            msg = (
                                f"✅ Trade Completed\n"
                                f"{primary_exchange_code.upper()} | Side: {side_primary} | Status: {primary_order_status['status']}\n"
                                f"{secondary_exchange_code.upper()} | Side: {side_secondary} | Status: {secondary_order_status['status']}\n"
                                f"Amount: {amount}\n"
                                f"Profit: {profit:.4f}\n"
                                f"Total Profit: {total_profit:.4f}\n"
                            )

                            bot_tele.send_message(TelegramSetting.CHAT_ID, msg)
                        else:
                            send_error_telegram(Exception("Cannot calculate profit"), "Trade Completed", bot_tele)

                    elif is_order_pending(primary_order_status) and is_order_pending(secondary_order_status):
                            execute_orders_concurrently(
                                lambda: primary_ccxt_manager.cancel_order(primary_transaction.order_id, symbol),
                                lambda: secondary_ccxt_manager.cancel_order(secondary_transaction.order_id, symbol)
                            )  

                            msg = (
                                f"❌ Cancel Orders\n"
                                f"{primary_exchange_code.upper()} |"
                                f"Total: {primary_transaction.total}\n"
                                f"{secondary_exchange_code.upper()} |"
                                f"Total: {secondary_transaction.total}\n"
                                f"Total Profit: {total_profit:.4f}\n"
                            )
                            bot_tele.send_message(TelegramSetting.CHAT_ID, msg)

                    elif is_order_pending(primary_order_status) ^  is_order_pending(secondary_order_status):
                        profit = abs(round(amount * price_primary - amount * price_secondary, 4))
                        msg = (
                            f"⏳ Pending Orders\n"
                            f"{primary_exchange_code.upper()} | Status: {primary_order_status['status']}\n"
                            f"{secondary_exchange_code.upper()} | Status: {secondary_order_status['status']}\n"
                            f"Amount: {amount}\n"
                            f"Profit: {profit}\n"
                            f"Total Profit: {total_profit:.4f}\n"
                        )
                        if not order_transaction.get('pending_sent', False):
                            bot_tele.send_message(TelegramSetting.CHAT_ID, msg)
                            order_transaction['pending_sent'] = True
                        q.put(order_transaction)
                else:
                    sleep(2)
                    # print("Thread cancel order is checking")
            except Exception as ex:
                sleep(1)
                print("ExchangePendingThread.job_function::{}".format(ex.__str__()))
                send_error_telegram(ex, "Main Trading Loop", bot_tele)

def calculate_profit(primary, primary_order_id, secondary, secondary_order_id, symbol):
    def get_summary(exchange, order_id):
        if exchange.has.get('fetchOrderTrades'):
            related = exchange.fetch_order_trades(order_id, symbol)
        else:
            all_trades = exchange.fetch_my_trades(symbol)
            related = [t for t in all_trades if t.get("order") == order_id]

        if not related:
            return None, None, None

        cost = sum(t["cost"] for t in related)
        fee  = sum(t["fee"]["cost"] for t in related if t.get("fee"))
        side = related[0]["side"]
        return cost, fee, side

    cost_p, fee_p, side_p = get_summary(primary, primary_order_id)
    cost_s, fee_s, side_s = get_summary(secondary, secondary_order_id)

    if side_p is None or side_s is None:
        print("Không get được dữ liệu trade, bỏ qua tính profit.")
        return None
    if side_p == "buy":
        return cost_s - cost_p - (fee_s + fee_p)
    else:
        return cost_p - cost_s - (fee_p + fee_s)

def get_filled_size(exchange_code, order):
    if exchange_code == ExchangesCode.BITMART.value:
        return float(order['info']['filledSize'])
    return order['filled']
    
def is_order_completed(order_status):
    status = order_status['status'].lower()
    return status in ['closed', 'filled']

def is_order_pending(order_status):
    status = order_status['status'].lower()
    return status in ['open', 'new', 'partially_filled'] 
