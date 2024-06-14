import hmac
import hashlib
import requests
import json
import time
from datetime import datetime, timezone, timedelta
import base64
from exchange.util.sync_core.exchange_sync_base import AbstractExchange


class GateExchange(AbstractExchange):
    def __init__(self, api_key, secret, password=None):
        super(GateExchange, self).__init__(api_key, secret, password)

    def withdraw(self, payload):
        host = "https://api.gateio.ws"
        prefix = "/api/v4"
        payload['currency'] = payload['coin']
        del payload['coin']
        if payload['currency'] == 'USDT':
            payload['network'] = payload['chain']
            del payload['chain']

        common_headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        url = '/withdrawals'
        request_content = json.dumps(payload)
        sign_headers = self.gen_sign('POST', prefix + url, "", request_content)
        sign_headers.update(common_headers)
        print('signature headers: %s' % sign_headers)
        res = requests.post(host + prefix + url, headers=sign_headers, data=request_content)
        return self._check_response_withdraw(res.json())

    def get_withdraw_list(self, order_id):
        host = "https://api.gateio.ws"
        prefix = "/api/v4"
        common_headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        url = '/wallet/withdrawals'
        sign_headers = self.gen_sign('GET', prefix + url, "")
        sign_headers.update(common_headers)
        print('signature headers: %s' % sign_headers)
        res = requests.get(host + prefix + url, headers=sign_headers)
        return self._check_get_withdraw_list(res.json(), order_id)

    def gen_sign(self, method, url, query_string=None, payload_string=None):
        key = self.api_key  # api_key
        secret = self.secret  # api_secret
        t = time.time()
        m = hashlib.sha512()
        m.update((payload_string or "").encode('utf-8'))
        hashed_payload = m.hexdigest()
        s = '%s\n%s\n%s\n%s\n%s' % (method, url, query_string or "", hashed_payload, t)
        sign = hmac.new(secret.encode('utf-8'), s.encode('utf-8'), hashlib.sha512).hexdigest()
        return {'KEY': key, 'Timestamp': str(t), 'SIGN': sign}

    def _check_response_withdraw(self, res):
        response = {'success': False, 'id': None}
        status_code = res.status_code
        content = res.content
        if status_code == 200:
            if content.status == "REQUEST":
                response['success'] = True
                response['id'] = content.id
        return response

    def _check_get_withdraw_list(self, res, order_id):
        response = {'success': False, 'status': None, 'command': 0}
        status_code = res.status_code
        content = res.content
        if status_code == 200:
            response['success'] = True
            record = self.find_record_by_id(content, order_id)
            if record:
                if record.status == 'DONE' or record.status == 'CANCEL' or record.status == 'FAIL':
                    response['status'] = record.status
                    response['command'] = 2
                else:
                    response['status'] = record.status
                    response['command'] = 1
                return response
        return response
    def find_record_by_id(self, data, record_id):
        for record in data:
            if record['id'] == record_id:
                return record
        return None