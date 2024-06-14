import ccxt

from config.config import ExchangesCode


def init_cctx_exchange(exchange):
    ccxt_exchange = None
    exchange_code = exchange.exchange_code
    param = {'apiKey': exchange.private_key, 'secret': exchange.secret_key}
    if exchange_code == ExchangesCode.BINANCE.value:
        ccxt_exchange = ccxt.binance(param)
    elif exchange_code == ExchangesCode.OKEX.value:
        param['password'] = exchange.password
        ccxt_exchange = ccxt.okx(param)
    elif exchange_code == ExchangesCode.GATE.value:
        ccxt_exchange = ccxt.gate(param)
    elif exchange_code == ExchangesCode.HOUBI.value:
        ccxt_exchange = ccxt.huobi(param)
    elif exchange_code == ExchangesCode.BYBIT.value:
        ccxt_exchange = ccxt.bybit(param)
    elif exchange_code == ExchangesCode.KUCOIN.value:
        ccxt_exchange = ccxt.kucoin(param)
    elif exchange_code == ExchangesCode.BITGET.value:
        param['password'] = exchange.password
        ccxt_exchange = ccxt.bitget(param)
    elif exchange_code == ExchangesCode.MEXC.value:
        ccxt_exchange = ccxt.mexc(param)
    elif exchange_code == ExchangesCode.BINGX.value:
        ccxt_exchange = ccxt.bingx(param)
    return ccxt_exchange


class CcxtManager:
    __instance = None
    __primary_exchange = None
    __secondary_exchange = None
    __ccxt_primary = None
    __ccxt_secondary = None
    __coin_trade = None
    __simulator = True
    __limit = 100
    rotation_usdt = 0.5
    rotation_coin = 0.5
    total_coin = 0
    total_usdt = 0

    def __init__(self):
        CcxtManager.__instance = self

    @staticmethod
    def get_instance():
        if CcxtManager.__instance is None:
            CcxtManager.__instance = CcxtManager()
        return CcxtManager.__instance

    def set_configure(self, primary_info, secondary_info, coin, rotation_coin, rotation_usdt, total_coin, total_usdt):
        self.set_primary_exchange(primary_info)
        self.set_secondary_exchange(secondary_info)
        self.__coin_trade = coin
        self.rotation_coin = rotation_coin
        self.rotation_usdt = rotation_usdt
        self.total_coin = total_coin
        self.total_usdt = total_usdt

    def set_primary_exchange(self, exchange_info):
        self.__primary_exchange = exchange_info
        self.__ccxt_primary = init_cctx_exchange(exchange_info)

    def set_secondary_exchange(self, exchange_info):
        self.__secondary_exchange = exchange_info
        self.__ccxt_secondary = init_cctx_exchange(exchange_info)

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
