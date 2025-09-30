import os
from enum import Enum
from dotenv import load_dotenv
load_dotenv()

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

    ARBITRAGE_THRESHOLD = float(os.getenv("ARBITRAGE_THRESHOLD"))
    MAX_TRADE_QUANTITY = int(os.getenv("MAX_TRADE_QUANTITY"))



class Message(Enum):
    MSG_CLOSE_MONITOR = "_CLOSE_IOT_LOG_MONITOR_"


class TimeRequest:
    GET_REQUEST = 60  # seconds


class ExchangesCode(Enum):
    BINGX = 'bingx'
    BINANCE = 'binance'
    OKEX = 'okex'
    GATE = 'gate'
    HOUBI = 'houbi'
    BYBIT = 'bybit'
    KUCOIN = 'kucoin'
    BITGET = 'bitget'
    MEXC = 'mexc'
    BITMART = 'bitmart'

class ExchangeNotionalSetting:
    """Min notional value required per exchange"""
    MIN = {
        "BITMART": 5.0,
        "MEXC": 1.0,
        "DEFAULT": 1.0
    }

class TelegramSetting:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.getenv("CHAT_ID")
    CHAT_WARNING_ID = os.getenv("CHAT_WARNING_ID")
    CHAT_ERROR_ID = os.getenv("CHAT_ERROR_ID")


class TradeEnv:
    PRIMARY_COIN_ADDRESS = os.getenv("PRIMARY_COIN_ADDRESS")
    PRIMARY_USDT_ADDRESS = os.getenv("PRIMARY_USDT_ADDRESS")
    SECONDARY_COIN_ADDRESS = os.getenv("SECONDARY_COIN_ADDRESS")
    SECONDARY_USDT_ADDRESS = os.getenv("SECONDARY_USDT_ADDRESS")
    COIN_NETWORK = os.getenv("COIN_NETWORK")
    USDT_NETWORK = os.getenv("USDT_NETWORK")

    REBALANCE_RATIO = float(os.getenv("REBALANCE_RATIO", 0.5))
    REBALANCE_THRESHOLD = int(os.getenv("REBALANCE_THRESHOLD",10))

    PRIMARY_FEE_TAKER = float(os.getenv("PRIMARY_FEE_TAKER", 0.06))
    SECONDARY_FEE_TAKER = float(os.getenv("SECONDARY_FEE_TAKER", 0.06))
