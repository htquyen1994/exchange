import connexion
from exchange.logic.exchange_logic import ExchangeLogic
from swagger_server.models.trade_strategy_config_request import TradeStrategyConfigRequest
from swagger_server import util

def trade_strategy_config_post(ConfigRequest):
    if connexion.request.is_json:
        ConfigRequest = TradeStrategyConfigRequest.from_dict(connexion.request.get_json())
    return ExchangeLogic.trade_strategy_config_post(ConfigRequest)


def trade_strategy_config_get():
    """Get auto rebalance status
    """
    return ExchangeLogic.trade_strategy_config_get()
