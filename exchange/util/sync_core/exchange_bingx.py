from exchange.util.sync_core.exchange_sync_base import AbstractExchange
import hmac
import hashlib
import requests
import json
import time
# from datetime import datetime
from datetime import datetime, timezone, timedelta
import base64


class BingXExchange(AbstractExchange):
    API_URL = "https://open-api.bingx.com"

    def __init__(self, api_key, secret, password=None):
        super(BingXExchange, self).__init__(api_key, secret, password)

    def withdraw(self, param):
        payload = {}
        path = '/openApi/wallets/v1/capital/withdraw/apply'
        method = "POST"
        params_map = {
            "address": param['address'],
            "addressTag": "None",
            "amount": param['amount'],
            "coin": param['coin'],
            "network": param['chain'],
            "walletType": "1"
        }
        params_str = self.parseParam(params_map)
        response = self.send_request(method, path, params_str, payload)
        return self._check_response_withdraw(response)

    def gen_sign(self, payload):
        signature = hmac.new(self.secret.encode("utf-8"), payload.encode("utf-8"), digestmod='sha256').hexdigest()
        return signature

    def send_request(self, method, path, urlpa, payload):
        url = "%s%s?%s&signature=%s" % (self.API_URL, path, urlpa, self.gen_sign(urlpa))
        print(url)
        headers = {
            'X-BX-APIKEY': self.api_key,
        }
        response = requests.request(method, url, headers=headers, data=payload)
        return response.text

    def parseParam(self, params_map):
        sorted_keys = sorted(params_map)
        params_str = "&".join(["%s=%s" % (x, params_map[x]) for x in sorted_keys])
        if params_str != "":
            return params_str + "&timestamp=" + str(int(time.time() * 1000))
        else:
            return params_str + "timestamp=" + str(int(time.time() * 1000))

    def get_withdraw_list(self, order_id):
        payload = {}
        path = '/openApi/api/v3/capital/withdraw/history'
        method = "GET"
        params_map = {
            "id": order_id,
            "endTime": str(int(time.time() * 1000)),
            "recvWindow": "60",
            "startTime": str(int((time.time() - 2 * 3600) * 1000)),
        }
        paramsStr = self.parseParam(params_map)
        data = self.send_request(method, path, paramsStr, payload)
        return self._check_get_withdraw_list(data, order_id)

    def _check_response_withdraw(self, res):
        response = {'success': False, 'id': None}
        status_code = res.code
        content = res.data
        if status_code == 200:
            response['success'] = True
            response['id'] = content.id
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
                    if record.status == 5 or record.status == 6:
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