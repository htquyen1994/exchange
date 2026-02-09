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
            coin = configure.coin
            arbitrage_threshold = configure.arbitrage_threshold
            max_trade_quantity = configure.max_trade_quantity
            primary_trade = configure.primary_trade
            secondary_trade = configure.secondary_trade
            telegram_config = configure.telegram_config
            Manager.get_instance().set_config_trade(primary_exchange, secondary_exchange, coin, arbitrage_threshold, max_trade_quantity, primary_trade, secondary_trade, telegram_config)
            resp = CommonResponse()
            return resp, 200
        except Exception as ex:
            print(f"ExchangeLogic.configure_post::{ex}")
            return {"error": str(ex)}, 400

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
                "coin_threshold",
                "trend_threshold",
                "primary",
                "secondary",
            ]

            for field in required_fields:
                value = getattr(ConfigRequest, field, None)
                if value is None:
                    raise ValueError(f"Missing or null '{field}' field")
            wallet_required = [
                "coin_address",
                "usdt_address",
                "coin_network",
                "usdt_network",
            ]

            for side in ["primary", "secondary"]:
                wallet = getattr(ConfigRequest, side)

                for w_field in wallet_required:
                    if getattr(wallet, w_field, None) is None:
                        raise ValueError(f"Missing '{w_field}' in '{side}'")

            Manager.get_instance().set_rebalance_config(ConfigRequest)

            resp = CommonResponse()
            resp.message = "Rebalance parameters updated successfully"
            resp.data = {
                "enabled": ConfigRequest.enabled,
                "usdt_ratio": ConfigRequest.usdt_ratio,
                "coin_ratio": ConfigRequest.coin_ratio,
                "usdt_threshold": ConfigRequest.usdt_threshold,
                "coin_threshold": ConfigRequest.coin_threshold,
                "trend_threshold": ConfigRequest.trend_threshold,
                "primary": vars(ConfigRequest.primary),
                "secondary": vars(ConfigRequest.secondary),
            }

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
                "trend_threshold": config.trend_threshold,
                "primary": {
                    "coin_address": config.primary.coin_address,
                    "usdt_address": config.primary.usdt_address,
                    "coin_network": config.primary.coin_network,
                    "usdt_network": config.primary.usdt_network,
                } if config.primary else None,
                "secondary": {
                    "coin_address": config.secondary.coin_address,
                    "usdt_address": config.secondary.usdt_address,
                    "coin_network": config.secondary.coin_network,
                    "usdt_network": config.secondary.usdt_network,
                } if config.secondary else None,
            }
            return resp, 200
        except Exception as ex:
            print(f"ExchangeLogic.rebalance_status_get::{ex}")
    @classmethod
    @require_authenticate
    @Util.system_error_handler
    def trade_strategy_config_post(cls, ConfigRequest):
        try:
            required_fields = [
                "mode"
            ]
            for field in required_fields:
                value = getattr(ConfigRequest, field, None)
                if value is None:
                    raise ValueError(f"Missing or null '{field}' field")
                
            Manager.get_instance().set_trade_strategy_config(ConfigRequest)
            resp = CommonResponse()
            resp.message = "Trade strategy parameters updated successfully"
            resp.data = vars(ConfigRequest)
            return resp, 200
        except Exception as ex:
            print(f"ExchangeLogic.trade_strategy_config_post::{ex}")
    @classmethod
    @require_authenticate
    @Util.system_error_handler
    def trade_strategy_config_get(cls):
        try:
            resp = CommonResponse()
            manager = Manager.get_instance()
            config = manager.get_trade_strategy_config()
            resp.message = {
                "mode": config.mode,
            }
            return resp, 200
        except Exception as ex:
            print(f"ExchangeLogic.trade_strategy_config_get::{ex}")