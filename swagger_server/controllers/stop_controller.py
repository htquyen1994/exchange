import connexion
import six

from exchange.logic.exchange_logic import ExchangeLogic
from swagger_server.models.common_response import CommonResponse  # noqa: E501
from swagger_server import util


def stop_post():  # noqa: E501
    """Stop trade post

    Do Stop trade # noqa: E501


    :rtype: CommonResponse
    """
    return ExchangeLogic.stop()

