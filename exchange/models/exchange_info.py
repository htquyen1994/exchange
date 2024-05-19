class ExchangeInfo:
    def __init__(self, code, private_key, secret_key, password=None):
        self.exchange_code = code
        self.private_key = private_key
        self.secret_key = secret_key
        self.password = password
