import connexion

from exchange.logic.exchange_logic import ExchangeLogic
from swagger_server.models.rebalance_config_request import RebalanceConfigRequest
from swagger_server import util

def rebalance_config_post(ConfigRequest):
    if connexion.request.is_json:
        ConfigRequest = RebalanceConfigRequest.from_dict(connexion.request.get_json())
    return ExchangeLogic.rebalance_config_post(ConfigRequest)


def rebalance_status_get():
    """Get auto rebalance status
    """
    return ExchangeLogic.rebalance_status_get()
