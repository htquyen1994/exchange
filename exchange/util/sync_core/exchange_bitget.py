from exchange.util.sync_core.exchange_sync_base import AbstractExchange
import hmac
import hashlib
import requests
import json
import time
# from datetime import datetime
from datetime import datetime, timezone, timedelta
import base64


class BitGetExchange(AbstractExchange):
    def __init__(self, api_key, secret, password=None):
        super(BitGetExchange, self).__init__(api_key, secret, password)

    def withdraw(self, payload):
        base_url = "https://api.bitget.com"
        endpoint = "/api/spot/v1/wallet/withdrawal"
        if payload['coin'] != 'USDT':
            payload['network'] = payload['chain'] 
        payload_str = json.dumps(payload)
        timestamp = str(int(time.time() * 1000))
        message = str(timestamp) + str.upper("POST") + endpoint + payload_str
        signature = self.gen_sign(message)
        headers = {
            'Content-Type': 'application/json',
            'ACCESS-KEY': self.api_key,
            'ACCESS-TIMESTAMP': timestamp,
            'ACCESS-PASSPHRASE': self.password,
            'ACCESS-SIGN': signature,
            "Locale": "en-US"
        }

        response = requests.post(base_url + endpoint, headers=headers, data=payload_str)
        data = response.json()
        return self._check_response_withdraw(data)

    def gen_sign(self, message):
        mac = hmac.new(bytes(self.secret, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
        d = mac.digest()
        return base64.b64encode(d).decode('utf-8')

    def get_withdraw_list(self, order_id):
        base_url = "https://api.bitget.com"
        endpoint = "/api/spot/v1/wallet/withdrawal-list"
        current_timestamp = int(time.time() * 1000)
        two_hours_ago_timestamp = int((time.time() - 2 * 3600) * 1000)
        params = {"startTime": str(two_hours_ago_timestamp), "endTime": str(current_timestamp)}
        request_path = endpoint + self.parse_params_to_str(params)
        body = ""

        timestamp = str(int(time.time() * 1000))
        message = str(timestamp) + str.upper("GET") + request_path
        signature = self.gen_sign(message)
       
        headers = {
            'Content-Type': 'application/json',
            'ACCESS-KEY': self.api_key,
            'ACCESS-TIMESTAMP': timestamp,
            'ACCESS-PASSPHRASE': self.password,
            'ACCESS-SIGN': signature,
            "Locale": "en-US"
        }

        response = requests.get(base_url + request_path, headers=headers)
        data = response.json()
        return self._check_get_withdraw_list(data, order_id)

    def _check_response_withdraw(self, res):
        response = {'success': False, 'id': None}
        status_code = res.status_code
        content = res.content
        if status_code == 200:
            if content.code == "00000":
                response['success'] = True
                response['id'] = content.data
        return response

    def _check_get_withdraw_list(self, res, order_id):
        response = {'success': False, 'status': None, 'command': 0}
        status_code = res.status_code
        content = res.content
        if status_code == 200:
            if content.code == "00000":
                response['success'] = True
                record = self.find_record_by_id(content.data, order_id)
                if record:
                    if record.status is 'cancel' or record.status is 'success' or record.status is 'reject':
                        response['status'] = record.status
                        response['command'] = 2
                    else:
                        response['status'] = record.status
                        response['command'] = 1
                    return response
        return response

    def parse_params_to_str(self, params):
        url = '?'
        for key, value in params.items():
            url = url + str(key) + '=' + str(value) + '&'

        return url[0:-1]

    def find_record_by_id(self, data, record_id):
        for record in data:
            if record['id'] == record_id:
                return record
        return None