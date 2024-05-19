import connexion
import six

from swagger_server.models.common_response import CommonResponse  # noqa: E501
from swagger_server.models.ping_response import PingResponse  # noqa: E501
from swagger_server import util


def ping_post():  # noqa: E501
    """Start trade post

    Do Start trade # noqa: E501


    :rtype: PingResponse
    """
    return 'do some magic!'
