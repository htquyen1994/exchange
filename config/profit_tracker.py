import json
import os
from threading import Lock

DATA_FILE = "trading_data.json"
file_lock = Lock()

def load_trading_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data
        except:
            return {}
    return {}

def save_trading_data(**kwargs):
    """
    kwargs: total_profit=..., total_fees=...
    """
    with file_lock:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
            except:
                data = {}
        else:
            data = {}

        data.update(kwargs)

        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
