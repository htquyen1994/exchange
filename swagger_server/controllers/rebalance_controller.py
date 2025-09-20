import connexion

from exchange.logic.exchange_logic import ExchangeLogic
from swagger_server.models.rebalance_toggle_request import RebalanceToggleRequest  # noqa: E501
from swagger_server import util

def rebalance_toggle_post(ToggleRequest):  # noqa: E501
    """Toggle auto rebalance on/off
    body: {"enable": true/false}
    """
    if connexion.request.is_json:
        body = RebalanceToggleRequest.from_dict(connexion.request.get_json())  # noqa: E501
    return ExchangeLogic.rebalance_toggle_post(ToggleRequest)


def rebalance_status_get():  # noqa: E501
    """Get auto rebalance status
    """
    return ExchangeLogic.rebalance_status_get()
