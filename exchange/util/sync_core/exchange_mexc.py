# import hmac
# import hashlib
# import requests
# import json
# import time
# from datetime import datetime, timezone, timedelta
# import base64
# from mexcpy import MexcAPI
#
# from exchange.util.sync_core.exchange_sync_base import AbstractExchange
#
#
# class MexcExchange(AbstractExchange):
#     def __init__(self, api_key, secret, password=None):
#         super(MexcExchange, self).__init__(api_key, secret, password)
#
#
#     def withdraw(self, payload):
#         mexc = MexcAPI(self.api_key, self.secret)
#
#     def get_withdraw_list(self, params={}):
#         # host = "https://api.gateio.ws"
#         # prefix = "/api/v4"
#         # common_headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
#         # url = '/wallet/withdrawals' #/wallet/withdrawals withdrawals
#         # sign_headers = gen_sign('GET', prefix + url, "")
#         # sign_headers.update(common_headers)
#         # print('signature headers: %s' % sign_headers)
#         # res = requests.get(host + prefix + url, headers=sign_headers)
#         # print(res.status_code)
#         # print("Response {0}".format(res.json()))
#         # return res
#
#     def gen_sign(method, url, query_string=None, payload_string=None):
#         # key = self.api_key       # api_key
#         # secret = self.secret    # api_secret
#         # t = time.time()
#         # m = hashlib.sha512()
#         # m.update((payload_string or "").encode('utf-8'))
#         # hashed_payload = m.hexdigest()
#         # s = '%s\n%s\n%s\n%s\n%s' % (method, url, query_string or "", hashed_payload, t)
#         # sign = hmac.new(secret.encode('utf-8'), s.encode('utf-8'), hashlib.sha512).hexdigest()
#         # return {'KEY': key, 'Timestamp': str(t), 'SIGN': sign}
#
#     def _check_response(self, ret):
#         # response = {}
#         # data = ret.content
#         # if (data.status_code == 200):
#         #     if data.code == "00000":
#         #         response['success'] = True
#         #         response['orderId'] = data.data.orderId
#         #     else
#         #         response['success'] = False
#         #         response['orderId'] = None
#         #
#         #     return response
#         # response['success'] = False
#         # response['orderId'] = None
#         # return response