from config.config import ExchangesCode
from exchange.util.sync_core.exchange_bingx import BingXExchange
from exchange.util.sync_core.exchange_bitget import BitGetExchange
from exchange.util.sync_core.exchange_gate import GateExchange


class ExchangeFactory:
    @staticmethod
    def create_exchange(exchange_name, api_key, secret, password=None):
        if exchange_name == ExchangesCode.BITGET.value:
            return BitGetExchange(api_key, secret)
        elif exchange_name == ExchangesCode.GATE.value:
            return GateExchange(api_key, secret, password)
        elif exchange_name == ExchangesCode.BINGX.value:
            return BingXExchange(api_key, secret, password)
        else:
            raise ValueError(f"Sàn giao dịch {exchange_name} không được hỗ trợ.")
