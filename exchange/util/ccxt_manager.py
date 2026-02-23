import ccxt

from config.config import ExchangesCode


def init_ccxt_exchange(exchange):
    exchange_code = exchange.exchange_code
    param = {
        'apiKey': exchange.private_key,
        'secret': exchange.secret_key,
    }

    if getattr(exchange, "password", None):
        param['password'] = exchange.password

    if getattr(exchange, "uid", None):
        param['uid'] = exchange.uid

    if getattr(exchange, "options", None):
        param['options'] = exchange.options

    if exchange_code in ccxt.exchanges:
        exchange_class = getattr(ccxt, exchange_code)
        return exchange_class(param)

    raise ValueError(f"Exchange '{exchange_code}' is not supported by ccxt")


class CcxtManager:
    __instance = None
    __primary_exchange = None
    __secondary_exchange = None
    __ccxt_primary = None
    __ccxt_secondary = None
    __coin_trade = None
    __simulator = True
    __limit = 100

    def __init__(self):
        CcxtManager.__instance = self

    @staticmethod
    def get_instance():
        if CcxtManager.__instance is None:
            CcxtManager.__instance = CcxtManager()
        return CcxtManager.__instance

    def set_configure(self, primary_info, secondary_info, coin):
        self.set_primary_exchange(primary_info)
        self.set_secondary_exchange(secondary_info)
        self.__coin_trade = coin

    def set_primary_exchange(self, exchange_info):
        self.__primary_exchange = exchange_info
        self.__ccxt_primary = init_ccxt_exchange(exchange_info)

    def set_secondary_exchange(self, exchange_info):
        self.__secondary_exchange = exchange_info
        self.__ccxt_secondary = init_ccxt_exchange(exchange_info)

    def get_exchange(self, is_primary):
        if is_primary:
            return self.__primary_exchange
        return self.__secondary_exchange

    def get_simulator(self):
        return self.__simulator

    def get_limit(self):
        return self.__simulator

    def get_ccxt(self, is_primary):
        if is_primary:
            return self.__ccxt_primary
        return self.__ccxt_secondary

    def get_exchanges_available(self):
        return convert_enum_to_array(ExchangesCode)

    def get_coin_trade(self):
        return self.__coin_trade

def convert_enum_to_array(enum_class):
    return [{'exchange_code': exchange.value, 'exchange_name': exchange.name} for exchange in enum_class]
