# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.common_response import CommonResponse  # noqa: E501
from swagger_server.models.ping_response import PingResponse  # noqa: E501
from swagger_server.test import BaseTestCase


class TestPingController(BaseTestCase):
    """PingController integration test stubs"""

    def test_ping_post(self):
        """Test case for ping_post

        Start trade post
        """
        response = self.client.open(
            '/v1/ping',
            method='POST',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
