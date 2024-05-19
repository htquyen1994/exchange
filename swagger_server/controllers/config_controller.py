import connexion
import six

from exchange.logic.exchange_logic import ExchangeLogic
from swagger_server.models.common_response import CommonResponse  # noqa: E501
from swagger_server.models.configure_trade_request import ConfigureTradeRequest  # noqa: E501
from swagger_server import util


def config_post(Config):  # noqa: E501
    """Configuration trade post

    Do Configuration trade # noqa: E501

    :param Config: Parameter Configuration trade
    :type Config: dict | bytes

    :rtype: CommonResponse
    """
    if connexion.request.is_json:
        Config = ConfigureTradeRequest.from_dict(connexion.request.get_json())  # noqa: E501
    return ExchangeLogic.configure_post(Config)


