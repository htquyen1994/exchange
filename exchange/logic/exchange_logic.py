from exchange.util.auth import require_authenticate
from exchange.util.ccxt_manager import CcxtManager
from exchange.util.common import Util
from exchange.util.manager import Manager
from exchange.util.trader_agent import TraderAgent
from swagger_server.models import CommonResponse, ExchangesResponse


class ExchangeLogic:
    @classmethod
    @require_authenticate
    @Util.system_error_handler
    def configure_post(cls, configure):
        try:
            primary_exchange = configure.primary_exchange
            secondary_exchange = configure.secondary_exchange
            limit = configure.limit
            simulated = configure.simulated
            coin = configure.coin
            Manager.get_instance().set_config_trade(primary_exchange, secondary_exchange, coin, limit, simulated)
            resp = CommonResponse()
            return resp, 200
        except Exception as ex:
            print("ExchangeLogic.configure_post::".format(ex.__str__()))

    @classmethod
    @require_authenticate
    @Util.system_error_handler
    def start_post(cls):
        try:
            TraderAgent.get_instance().start_trade()
            resp = CommonResponse()
            return resp, 200
        except Exception as ex:
            print("ExchangeLogic.start_post::".format(ex.__str__()))

    @classmethod
    @require_authenticate
    @Util.system_error_handler
    def stop_post(cls):
        try:
            TraderAgent.get_instance().stop_trade()
            resp = CommonResponse()
            return resp, 200
        except Exception as ex:
            print("ExchangeLogic.stop_post::".format(ex.__str__()))

    @classmethod
    @require_authenticate
    @Util.system_error_handler
    def exchanges_get(cls):
        try:
            exchanges = CcxtManager.get_instance().get_exchanges_available()
            resp = ExchangesResponse()
            resp.coin_list = exchanges
            return resp, 200
        except Exception as ex:
            print("ExchangeLogic.stop_post::".format(ex.__str__()))

    @classmethod
    def start(cls):
        try:
            Manager.get_instance().start()
            print("Get giá trị",  Manager.get_instance().start_flag)
            resp = ExchangesResponse()
            return resp, 200
        except Exception as ex:
            print("ExchangeLogic.configure_post::".format(ex.__str__()))

    @classmethod
    def stop(cls):
        try:
            Manager.get_instance().stop()
            print("Get giá trị", Manager.get_instance().start_flag)
            resp = ExchangesResponse()
            return resp, 200
        except Exception as ex:
            print("ExchangeLogic.configure_post::".format(ex.__str__()))
    
    @classmethod
    @require_authenticate
    @Util.system_error_handler
    def rebalance_config_post(cls, ConfigRequest):
        try:
            required_fields = [
                "enabled",
                "usdt_ratio",
                "coin_ratio",
                "usdt_threshold",
                "coin_threshold"
            ]
            for field in required_fields:
                value = getattr(ConfigRequest, field, None)
                if value is None:
                    raise ValueError(f"Missing or null '{field}' field")
                
            Manager.get_instance().set_rebalance_config(ConfigRequest)
            resp = CommonResponse()
            resp.message = "Rebalance parameters updated successfully"
            resp.data = vars(ConfigRequest)
            return resp, 200
        except Exception as ex:
            print(f"ExchangeLogic.rebalance_config_post::{ex}")

    @classmethod
    @require_authenticate
    @Util.system_error_handler
    def rebalance_status_get(cls):
        try:
            resp = CommonResponse()
            manager = Manager.get_instance()
            config = manager.get_rebalance_config()
            resp.message = {
                "enabled": config.enabled,
                "usdt_ratio": config.usdt_ratio,
                "coin_ratio": config.coin_ratio,
                "usdt_threshold": config.usdt_threshold,
                "coin_threshold": config.coin_threshold,
            }
            return resp, 200
        except Exception as ex:
            print(f"ExchangeLogic.rebalance_status_get::{ex}")