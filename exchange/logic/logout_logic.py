from flask import Response, make_response

from exchange.util.auth import require_authenticate
from exchange.util.common import Util
from exchange.util.const import ResponseMessage
from exchange.util.trader_agent import TraderAgent


class LogoutLogic:
    @classmethod
    @require_authenticate
    @Util.system_error_handler
    def logout_post(cls):
        """
        Do logout
        :rtype: CommResponse
        :return: Logout result
        """
        TraderAgent.get_instance().set_session(None)
        return Util.make_json_response(session_key=''), ResponseMessage.Success.http_code
