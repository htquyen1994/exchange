import connexion
import six

from exchange.logic.exchange_logic import ExchangeLogic
from swagger_server.models.common_response import CommonResponse  # noqa: E501
from swagger_server import util


def start_post():  # noqa: E501
    """Start trade post

    Do Start trade # noqa: E501


    :rtype: CommonResponse
    """
    return ExchangeLogic.start()
