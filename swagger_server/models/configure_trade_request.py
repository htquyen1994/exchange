# coding: utf-8

from __future__ import absolute_import
from typing import Dict
from swagger_server.models.base_model_ import Model
from swagger_server.models.exchange_request import ExchangeRequest
from swagger_server import util


# -------------------------
# Nested Models
# -------------------------

class TradeFeeConfig(Model):

    def __init__(self, fee_taker: float = None, min_notional: float = None):
        self.swagger_types = {
            'fee_taker': float,
            'min_notional': float
        }

        self.attribute_map = {
            'fee_taker': 'fee_taker',
            'min_notional': 'min_notional'
        }

        self._fee_taker = fee_taker
        self._min_notional = min_notional

    @property
    def fee_taker(self):
        return self._fee_taker

    @fee_taker.setter
    def fee_taker(self, value):
        self._fee_taker = value

    @property
    def min_notional(self):
        return self._min_notional

    @min_notional.setter
    def min_notional(self, value):
        self._min_notional = value


class TelegramBotConfig(Model):

    def __init__(
        self,
        bot_token: str = None,
        chat_id: str = None,
        chat_topic: int = None,
        warning_topic: int = None,
        error_topic: int = None,
    ):
        self.swagger_types = {
            'bot_token': str,
            'chat_id': str,
            'chat_topic': int,
            'warning_topic': int,
            'error_topic': int,
        }

        self.attribute_map = {
            'bot_token': 'bot_token',
            'chat_id': 'chat_id',
            'chat_topic': 'chat_topic',
            'warning_topic': 'warning_topic',
            'error_topic': 'error_topic',
        }

        self._bot_token = bot_token
        self._chat_id = chat_id
        self._chat_topic = chat_topic
        self._warning_topic = warning_topic
        self._error_topic = error_topic

    @property
    def bot_token(self):
        return self._bot_token

    @bot_token.setter
    def bot_token(self, value):
        self._bot_token = value

    @property
    def chat_id(self):
        return self._chat_id

    @chat_id.setter
    def chat_id(self, value):
        self._chat_id = value

    @property
    def chat_topic(self):
        return self._chat_topic

    @chat_topic.setter
    def chat_topic(self, value):
        self._chat_topic = value

    @property
    def warning_topic(self):
        return self._warning_topic

    @warning_topic.setter
    def warning_topic(self, value):
        self._warning_topic = value

    @property
    def error_topic(self):
        return self._error_topic

    @error_topic.setter
    def error_topic(self, value):
        self._error_topic = value


# -------------------------
# Main Model
# -------------------------

class ConfigureTradeRequest(Model):

    def __init__(
        self,
        coin: str = None,
        primary_exchange: ExchangeRequest = None,
        secondary_exchange: ExchangeRequest = None,
        arbitrage_threshold: float = None,
        max_trade_quantity: float = None,
        primary_trade: TradeFeeConfig = None,
        secondary_trade: TradeFeeConfig = None,
        telegram_config: TelegramBotConfig = None,
    ):

        self.swagger_types = {
            'coin': str,
            'primary_exchange': ExchangeRequest,
            'secondary_exchange': ExchangeRequest,
            'arbitrage_threshold': float,
            'max_trade_quantity': float,
            'primary_trade': TradeFeeConfig,
            'secondary_trade': TradeFeeConfig,
            'telegram_config': TelegramBotConfig,
        }

        self.attribute_map = {
            'coin': 'coin',
            'primary_exchange': 'primary_exchange',
            'secondary_exchange': 'secondary_exchange',
            'arbitrage_threshold': 'arbitrage_threshold',
            'max_trade_quantity': 'max_trade_quantity',
            'primary_trade': 'primary_trade',
            'secondary_trade': 'secondary_trade',
            'telegram_config': 'telegram_config',
        }

        self._coin = coin
        self._primary_exchange = primary_exchange
        self._secondary_exchange = secondary_exchange
        self._arbitrage_threshold = arbitrage_threshold
        self._max_trade_quantity = max_trade_quantity
        self._primary_trade = primary_trade
        self._secondary_trade = secondary_trade
        self._telegram_config = telegram_config

    @classmethod
    def from_dict(cls, dikt) -> 'ConfigureTradeRequest':
        return util.deserialize_model(dikt, cls)

    @property
    def coin(self):
        return self._coin

    @coin.setter
    def coin(self, value):
        self._coin = value

    @property
    def primary_exchange(self):
        return self._primary_exchange

    @primary_exchange.setter
    def primary_exchange(self, value):
        self._primary_exchange = value

    @property
    def secondary_exchange(self):
        return self._secondary_exchange

    @secondary_exchange.setter
    def secondary_exchange(self, value):
        self._secondary_exchange = value

    @property
    def arbitrage_threshold(self):
        return self._arbitrage_threshold

    @arbitrage_threshold.setter
    def arbitrage_threshold(self, value):
        self._arbitrage_threshold = value

    @property
    def max_trade_quantity(self):
        return self._max_trade_quantity

    @max_trade_quantity.setter
    def max_trade_quantity(self, value):
        self._max_trade_quantity = value

    @property
    def primary_trade(self):
        return self._primary_trade

    @primary_trade.setter
    def primary_trade(self, value):
        self._primary_trade = value

    @property
    def secondary_trade(self):
        return self._secondary_trade

    @secondary_trade.setter
    def secondary_trade(self, value):
        self._secondary_trade = value

    @property
    def telegram_config(self):
        return self._telegram_config

    @telegram_config.setter
    def telegram_config(self, value):
        self._telegram_config = value
