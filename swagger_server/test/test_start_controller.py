# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.common_response import CommonResponse  # noqa: E501
from swagger_server.test import BaseTestCase


class TestStartController(BaseTestCase):
    """StartController integration test stubs"""

    def test_start_post(self):
        """Test case for start_post

        Start trade post
        """
        response = self.client.open(
            '/v1/start',
            method='POST',
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
