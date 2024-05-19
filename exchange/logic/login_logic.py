import uuid

from config.message import ErrorMessage
from exchange.util.log_agent import LoggerAgent
from swagger_server.models import LoginResponse
from exchange.util.trader_agent import TraderAgent
from exchange.util.common import Util
from exchange.util.const import ResponseMessage, WebError, LoginError, InvalidParamError


class LoginLogic:

    @classmethod
    @Util.system_error_handler
    def login_post(cls, login):
        try:
            cls.__ensure_login_request(login)
            # Begin transaction
            session_key = LoginLogic.__do_login(login.login_id, login.password)
            LoggerAgent.info("Login succeeded, id={}".format(login.login_id))
            # Make info to response
            login_res = LoginResponse(
                secret_key=session_key,
                access_info=None
            )
            return Util.make_json_response(login_res.to_dict(), session_key), ResponseMessage.Success.http_code
        except WebError as ex:
            #  login error
            LoggerAgent.warning(ex.__str__())
            return ex.make_response(str(ex))

    @classmethod
    def __do_login(cls,  user_id, password):
        if user_id != 'admin' or password != 'admin@135':
            raise LoginError(ErrorMessage.LoginError)
        # create new session key
        return cls.__create_new_session_key(user_id)

    @classmethod
    def __create_new_session_key(cls,  user_id):
        session_key = "{}{}".format(user_id, uuid.uuid4().__str__())
        cls.__insert_session_key(session_key)
        return session_key

    @classmethod
    def _delete_expired_session_key(cls):
        TraderAgent.get_instance().set_session(None)

    @classmethod
    def __insert_session_key(cls, session_key):
        TraderAgent.get_instance().set_session(session_key)

    @classmethod
    def __ensure_login_request(cls, login_request):
        if login_request is None:
            raise InvalidParamError("login_request is None")
        if login_request.login_id is None:
            raise InvalidParamError("login_id is None")
        if login_request.password is None:
            raise InvalidParamError("Password is None")
