import connexion
import six

from swagger_server.models.common_response import CommonResponse  # noqa: E501
from swagger_server.models.login_request import LoginRequest  # noqa: E501
from swagger_server.models.login_response import LoginResponse  # noqa: E501
from swagger_server import util


def login_post(Login):  # noqa: E501
    """Login post

    Do login # noqa: E501

    :param Login: Parameter Login
    :type Login: dict | bytes

    :rtype: LoginResponse
    """
    if connexion.request.is_json:
        Login = LoginRequest.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
