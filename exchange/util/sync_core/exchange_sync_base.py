from abc import ABC, abstractmethod


class AbstractExchange(ABC):
    def __init__(self, api_key, secret, password=None):
        self.api_key = api_key
        self.secret = secret
        self.password = password
        self.exchange = None

    @abstractmethod
    def withdraw(self, payload):
        raise NotImplementedError("withdraw() not implemented")

    @abstractmethod
    def get_withdraw_list(self, order_id):
        raise NotImplementedError("get_withdraw_list() not implemented")

