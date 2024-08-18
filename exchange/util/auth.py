"""Authenticate"""
import time

import bcrypt
from decorator import decorator
from flask import g, request, redirect

from exchange.util.common import Session
from exchange.util.const import ResponseMessage
from exchange.util.log_agent import LoggerAgent


@decorator
def require_authenticate(func: callable, *args, **kwargs):
    """
    A decorator for view entry's authentication.
    :param func: decorate function
    :param args: args parameter of decorate function
    :param kwargs: kwargs parameter of decorate function
    :return: -
    """
    try:
        return func(*args, **kwargs)

    except Exception as ex:
        # server error, DB error
        LoggerAgent.error("require_authenticate", ex.__str__())
        return ResponseMessage.ServerError.http_code



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

