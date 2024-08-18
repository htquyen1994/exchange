from enum import Enum


class AppConfig:
    VERSION = "20200506"

class SessionSetting:
    """Session setting"""
    # Session time out (s)
    SESSION_TIMEOUT = 3600


class LogSetting:
    LOG_FILE = "D:/smartcanteen.log"


class TradeSetting:
    SIMULATOR = True
    TIME_GET_ORDER_BOOK = 10
    EXCHANGES = ['binance', 'okex', 'gate', 'houbi', 'bybit', 'kucoin', 'bitget', 'mexc']


class Message(Enum):
    MSG_CLOSE_MONITOR = "_CLOSE_IOT_LOG_MONITOR_"


class TimeRequest:
    GET_REQUEST = 60  # seconds


class ExchangesCode(Enum):
    BINANCE = 'binance'
    OKEX = 'okex'
    GATE = 'gate'
    HOUBI = 'houbi'
    BYBIT = 'bybit'
    KUCOIN = 'kucoin'
    BITGET = 'bitget'
    MEXC = 'mexc'
    BINGX = 'bingx'
