import ccxt
import telebot
from config.config import TelegramSetting, TradeEnv
from config.profit_tracker import load_trading_data, save_trading_data
_fee_cache = {}


PRIMARY_COIN_ADDRESS = TradeEnv.PRIMARY_COIN_ADDRESS
PRIMARY_USDT_ADDRESS = TradeEnv.PRIMARY_USDT_ADDRESS
SECONDARY_COIN_ADDRESS = TradeEnv.SECONDARY_COIN_ADDRESS
SECONDARY_USDT_ADDRESS = TradeEnv.SECONDARY_USDT_ADDRESS
COIN_NETWORK = TradeEnv.COIN_NETWORK
USDT_NETWORK = TradeEnv.USDT_NETWORK
COIN_RATIO = TradeEnv.COIN_RATIO
COIN_REBALANCE_THRESHOLD = TradeEnv.COIN_REBALANCE_THRESHOLD

def rebalancing(primary: ccxt.Exchange, secondary: ccxt.Exchange, symbol: str, 
                primary_order_book, secondary_order_book, 
                auto_rebalance: bool, threshold: float):
    """
    Rebalance USDT and coin between two exchanges

    Args:
        primary: Primary exchange instance
        secondary: Secondary exchange instance
        symbol: Trading pair symbol (e.g., "BTC/USDT")
        trend: trading trend, e.g. "sell_primary" or "buy_primary"
    """
    if not auto_rebalance:
        print("Auto rebalance if OFF")
        return
    trend = detect_trend(primary_order_book, secondary_order_book, threshold)
    trading_data = load_trading_data()
    total_fees = trading_data.get("total_fees", 0)
    if (
        not PRIMARY_COIN_ADDRESS
        or not SECONDARY_COIN_ADDRESS
        or not PRIMARY_USDT_ADDRESS
        or not SECONDARY_USDT_ADDRESS
        or not COIN_NETWORK
        or not USDT_NETWORK
    ):
        raise ValueError("One or more addresses/networks are not configured")

    bot = telebot.TeleBot(TelegramSetting.TOKEN)
    global _fee_cache
    base_coin = symbol.replace("/USDT", "")
    primary_fee = get_fee(primary, base_coin, COIN_NETWORK)
    secondary_fee = get_fee(secondary, base_coin, COIN_NETWORK)
    try:
        primary_balance = primary.fetch_balance()
        secondary_balance = secondary.fetch_balance()

        primary_usdt = primary_balance.get("USDT", {}).get("total", 0)
        primary_coin = primary_balance.get(base_coin, {}).get("total", 0)
        secondary_usdt = secondary_balance.get("USDT", {}).get("total", 0)
        secondary_coin = secondary_balance.get(base_coin, {}).get("total", 0)

        total_usdt = primary_usdt + secondary_usdt
        total_coin = primary_coin + secondary_coin

        # 30% threshold
        # Transfer USDT: secondary -> primary
        if primary_usdt < total_usdt * 0.3:
            if can_withdraw(secondary, "USDT"):
                transfer_amount = total_usdt / 2 - primary_usdt
                transaction = secondary.withdraw(
                    "USDT",
                    round(transfer_amount, 4),
                    PRIMARY_USDT_ADDRESS,
                    tag=None,
                    params={"network": USDT_NETWORK},
                )
                print(f"USDT withdrawal transaction: {transaction}")
            else:
                print(f"Pending USDT withdrawal detected on {secondary.id}, skip withdraw")

        # Transfer USDT: primary -> secondary
        elif secondary_usdt < total_usdt * 0.3:
            if can_withdraw(primary, "USDT"):
                transfer_amount = total_usdt / 2 - secondary_usdt
                transaction = primary.withdraw(
                    "USDT",
                    round(transfer_amount, 4),
                    SECONDARY_USDT_ADDRESS,
                    tag=None,
                    params={"network": USDT_NETWORK},
                )
                print(f"USDT withdrawal transaction: {transaction}")
            else:
                print(f"Pending USDT withdrawal detected on {primary.id}, skip withdraw")

        if not trend:
            print("No Trend arbitrage.")
            return
        # Transfer coin: secondary -> primary
        if trend == "sell_primary" and primary_coin <= COIN_REBALANCE_THRESHOLD:
            transfer_amount = total_coin * COIN_RATIO - primary_coin
            if can_withdraw(secondary, base_coin):
                if transfer_amount > 0 and transfer_amount <= secondary_coin:
                    transaction = secondary.withdraw(
                        base_coin,
                        round(transfer_amount, 4),
                        PRIMARY_COIN_ADDRESS,
                        tag=None,
                        params={"network": COIN_NETWORK},
                    )
                    total_fees += secondary_fee
                    message = f"{base_coin}: {secondary.id} -> {primary.id}\nAmount: {transfer_amount:.2f}\nFees: {secondary_fee} {base_coin}\nTotal Fees: {total_fees} {base_coin}"
                    bot.send_message(TelegramSetting.CHAT_ID, message)
                    print(message)
            else:
                print(f"Pending Coin withdrawal detected on {secondary.id}, skip withdraw")

        # Transfer coin: primary -> secondary
        elif  trend == "buy_primary" and secondary_coin <= COIN_REBALANCE_THRESHOLD:
            if can_withdraw(primary, base_coin):
                transfer_amount = total_coin * COIN_RATIO - secondary_coin
                if transfer_amount > 0 and transfer_amount <= primary_coin:
                    transaction = primary.withdraw(
                        base_coin,
                        round(transfer_amount, 4),
                        SECONDARY_COIN_ADDRESS,
                        tag=None,
                        params={"network": COIN_NETWORK},
                    )
                    total_fees += primary_fee
                    message = f"{base_coin}: {primary.id} -> {secondary.id}\nAmount: {transfer_amount:.2f}\nFees: {primary_fee} {base_coin}\nTotal Fees: {total_fees} {base_coin}"
                    bot.send_message(TelegramSetting.CHAT_ID, message)
                    print(message)
            else:
                print(f"Pending Coin withdrawal detected on {primary.id}, skip withdraw")
        
        save_trading_data(total_fees=total_fees)

    except ccxt.NetworkError as e:
        error_msg = f"Network error during rebalancing: {str(e)}"
        print(error_msg)
        raise

    except ccxt.ExchangeError as e:
        error_msg = f"Exchange error during rebalancing: {str(e)}"
        print(error_msg)
        raise

    except Exception as e:
        error_msg = f"Unexpected error during rebalancing: {str(e)}"
        print(error_msg)
        raise


def get_fee(exchange: ccxt.Exchange, coin: str, network: str):
    global _fee_cache
    key = f"{coin}_{exchange.id}"
    if key not in _fee_cache:
        try:
            currencies = exchange.fetch_currencies()
            _fee_cache[key] = currencies[coin]["networks"][network]["fee"]
        except:
            _fee_cache[key] = 0.001  # default

    return _fee_cache[key]

def can_withdraw(exchange: ccxt.Exchange, currency: str):
    """
    Check if there are no pending withdrawals for a given currency
    """
    try:
        withdrawals = exchange.fetch_withdrawals(code=currency, since=None, limit=5)
        for wd in withdrawals:
            status = wd.get("status", "").lower()
            if status not in ["ok", "completed", "canceled", "rejected", "failed"]:
                return False
        return True
    except Exception as e:
        print(f"Warning: fetch_withdrawals not supported on {exchange.id}, {e}")
        return True

def detect_trend(primary_order_book, secondary_order_book, threshold: float = 1.002):
    try:
        primary_bid = primary_order_book["bids"][0][0] if primary_order_book["bids"] else None
        primary_ask = primary_order_book["asks"][0][0] if primary_order_book["asks"] else None
        secondary_bid = secondary_order_book["bids"][0][0] if secondary_order_book["bids"] else None
        secondary_ask = secondary_order_book["asks"][0][0] if secondary_order_book["asks"] else None

        if not all([primary_bid, primary_ask, secondary_bid, secondary_ask]):
            return None

        # Trigger earlier than the strict threshold
        if primary_bid > secondary_ask * threshold * 0.9:
            return "sell_primary"
        elif secondary_bid > primary_ask * threshold * 0.9:
            return "buy_primary"
        else:
            return None

    except Exception as e:
        print(f"Error detecting trend: {e}")
        return None
