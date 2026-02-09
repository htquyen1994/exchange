# coding: utf-8

from __future__ import absolute_import
from swagger_server.models.base_model_ import Model
from swagger_server import util


# ---------------------------------
# Nested Model
# ---------------------------------

class RebalanceSide(Model):

    def __init__(
        self,
        coin_address: str = None,
        usdt_address: str = None,
        coin_network: str = None,
        usdt_network: str = None
    ):

        self.swagger_types = {
            'coin_address': str,
            'usdt_address': str,
            'coin_network': str,
            'usdt_network': str,
        }

        self.attribute_map = {
            'coin_address': 'coin_address',
            'usdt_address': 'usdt_address',
            'coin_network': 'coin_network',
            'usdt_network': 'usdt_network',
        }

        self._coin_address = coin_address
        self._usdt_address = usdt_address
        self._coin_network = coin_network
        self._usdt_network = usdt_network

    @classmethod
    def from_dict(cls, dikt) -> 'RebalanceSide':
        return util.deserialize_model(dikt, cls)


# ---------------------------------
# Main Model
# ---------------------------------

class RebalanceConfigRequest(Model):

    def __init__(
        self,
        enabled: bool = None,
        usdt_ratio: float = None,
        coin_ratio: float = None,
        usdt_threshold: float = None,
        coin_threshold: float = None,
        primary: RebalanceSide = None,
        secondary: RebalanceSide = None,
        trend_threshold: float = None
    ):

        self.swagger_types = {
            'enabled': bool,
            'usdt_ratio': float,
            'coin_ratio': float,
            'usdt_threshold': float,
            'coin_threshold': float,
            'primary': RebalanceSide,
            'secondary': RebalanceSide,
            'trend_threshold': float,
        }

        self.attribute_map = {
            'enabled': 'enabled',
            'usdt_ratio': 'usdt_ratio',
            'coin_ratio': 'coin_ratio',
            'usdt_threshold': 'usdt_threshold',
            'coin_threshold': 'coin_threshold',
            'primary': 'primary',
            'secondary': 'secondary',
            'trend_threshold': 'trend_threshold',
        }

        self._enabled = enabled
        self._usdt_ratio = usdt_ratio
        self._coin_ratio = coin_ratio
        self._usdt_threshold = usdt_threshold
        self._coin_threshold = coin_threshold
        self._primary = primary
        self._secondary = secondary
        self._trend_threshold = trend_threshold

    @classmethod
    def from_dict(cls, dikt) -> 'RebalanceConfigRequest':
        return util.deserialize_model(dikt, cls)

    # -------------------------
    # Properties
    # -------------------------

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    @property
    def usdt_ratio(self):
        return self._usdt_ratio

    @usdt_ratio.setter
    def usdt_ratio(self, value):
        self._usdt_ratio = value

    @property
    def coin_ratio(self):
        return self._coin_ratio

    @coin_ratio.setter
    def coin_ratio(self, value):
        self._coin_ratio = value

    @property
    def usdt_threshold(self):
        return self._usdt_threshold

    @usdt_threshold.setter
    def usdt_threshold(self, value):
        self._usdt_threshold = value

    @property
    def coin_threshold(self):
        return self._coin_threshold

    @coin_threshold.setter
    def coin_threshold(self, value):
        self._coin_threshold = value

    @property
    def primary(self):
        return self._primary

    @primary.setter
    def primary(self, value):
        self._primary = value

    @property
    def secondary(self):
        return self._secondary

    @secondary.setter
    def secondary(self, value):
        self._secondary = value

    @property
    def trend_threshold(self):
        return self._trend_threshold

    @trend_threshold.setter
    def trend_threshold(self, value):
        self._trend_threshold = value
