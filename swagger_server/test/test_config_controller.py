# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.common_response import CommonResponse  # noqa: E501
from swagger_server.models.configure_trade_request import ConfigureTradeRequest  # noqa: E501
from swagger_server.test import BaseTestCase


class TestConfigController(BaseTestCase):
    """ConfigController integration test stubs"""

    def test_config_post(self):
        """Test case for config_post

        Configuration trade post
        """
        Config = ConfigureTradeRequest()
        response = self.client.open(
            '/v1/config',
            method='POST',
            data=json.dumps(Config),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
