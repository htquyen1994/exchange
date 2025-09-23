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
    def rebalance_toggle_post(cls, ToggleRequest):
        try:
            # body: {"enabled": true/false}
            if "enabled" not in ToggleRequest:
                raise ValueError("Missing 'enabled' field")

            enabled = bool(ToggleRequest["enabled"])
            Manager.get_instance().set_auto_rebalance(enabled)

            resp = CommonResponse()
            resp.message = enabled
            return resp, 200
        except Exception as ex:
            print("ExchangeLogic.rebalance_toggle_post::{}".format(ex.__str__()))


    @classmethod
    @require_authenticate
    @Util.system_error_handler
    def rebalance_status_get(cls):
        try:
            resp = CommonResponse()
            resp.message = Manager.get_instance().get_auto_rebalance()
            return resp, 200
        except Exception as ex:
            print("ExchangeLogic.rebalance_status_get::{}".format(ex.__str__()))