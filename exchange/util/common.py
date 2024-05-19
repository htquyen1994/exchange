from exchange.util.const import Function, AuthorizationError, ResponseMessage, InvalidParamError
import datetime
import json
import time
from datetime import timedelta, time
from decorator import decorator
from flask import request, make_response

from exchange.util.log_agent import LoggerAgent


class Session:
    # Session timeout
    TIMEOUT = 3600
    # Key
    AUTH_KEY = 'Authorization'
    # Session key
    AUTH_SESSION_KEY = '_authentication'


class AuthUtil:
    """Auth utility"""

    @classmethod
    def set_cookie(cls, response, key_str, session_key):
        response.set_cookie(key_str, session_key)

    @classmethod
    def get_key(cls):
        key = cls.get_session_key_from_cookie()
        if key is None:
            key = cls.get_session_key_from_header()
        return key

    @classmethod
    def get_session_key_from_cookie(cls):
        if Session.AUTH_SESSION_KEY in request.cookies:
            return request.cookies[Session.AUTH_SESSION_KEY]

    @classmethod
    def get_session_key_from_header(cls):
        if Session.AUTH_KEY in request.headers:
            return request.headers[Session.AUTH_KEY]



class CommonUtil:
    @staticmethod
    def get_function_id(function):
        return Function[str(function)].id()


class Util:
    """Util"""

    @staticmethod
    @decorator
    def system_error_handler(f: callable, *args, **kwargs):
        """
        Decorator function to system error for all APIs
        :param f: decorator function
        :param args: decorator args
        :param kwargs: decorator kwargs
        :rtype: tuple
        :return: Swagger/ConnexionのResponse return format: tuple(data, http_code)
                data: CommonResponse
                http_code: http code
        """
        function_name = f.__name__
        for count in range(0, 3):
            try:
                return f(*args, **kwargs)

            except AuthorizationError as ex:
                # Auth error
                LoggerAgent.error(function_name, ex.__str__())
                return Util.__auth_error_response(ex)

            except Exception as ex:
                # Database error
                LoggerAgent.error(function_name, "{}".format(str(ex)))
                return Util.__error_response(ex)

    @staticmethod
    def __error_response(exception):
        """
        Make error to response
        :param exception: exception (Exception)
        :return: Swagger/ConnexionのResponse response format: tuple(data, http_code)
                data: CommonResponse
                http_code: http code
        """
        return ResponseMessage.exception_response(exception)

    @staticmethod
    def __auth_error_response(exception):
        """
        Make authentication/authorization error to response
        :param exception: exception (Exception)
        :return: Swagger/ConnexionのResponse response format: tuple(data, http_code)
                data: CommonResponse
                http_code: http code
        """
        return ResponseMessage.AuthenticateFailed.make_response(message=str(exception))

    @staticmethod
    def ensure_int(var_name, var_value):
        """
        Validate value is int
        :type var_name: str
        :param var_name:　var name
        :type var_value: str
        :param var_value:　value in str
        :rtype: int
        :return: value of var_value
        """
        try:
            return int(var_value)
        except Exception:
            raise InvalidParamError("{0}:{1}".format(var_name,var_value))

    @staticmethod
    def ensure_length_str(var_name, var_value):
        try:
            len_str = len(var_value)
            if len_str > 256:
                raise
            return
        except Exception as ex:
            raise InvalidParamError("Length of {0} > 256 characters".format(var_name))

    @staticmethod
    def make_json_response(body=None, session_key=None):
        """
        Validate value is int
        :type body: dict
        :param body: response body
        :type session_key: str
        :param session_key: session key
        :rtype: Response
        :return: response
        """
        if body is None:
            res = make_response()
        else:
            json_body = json.dumps(body)
            res = make_response(json_body)
            res.mimetype = 'application/json'
        if session_key is not None:
            AuthUtil.set_cookie(res, Session.AUTH_SESSION_KEY, session_key)
        return res
