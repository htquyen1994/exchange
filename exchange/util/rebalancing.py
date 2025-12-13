import ccxt
import telebot
import datetime
from config.config import TelegramSetting, TradeEnv
from config.profit_tracker import load_trading_data, save_trading_data
from exchange.util.orderbook_tools import maximum_quantity_trade_able
_fee_cache = {}


PRIMARY_COIN_ADDRESS = TradeEnv.PRIMARY_COIN_ADDRESS
PRIMARY_USDT_ADDRESS = TradeEnv.PRIMARY_USDT_ADDRESS
SECONDARY_COIN_ADDRESS = TradeEnv.SECONDARY_COIN_ADDRESS
SECONDARY_USDT_ADDRESS = TradeEnv.SECONDARY_USDT_ADDRESS
COIN_NETWORK = TradeEnv.COIN_NETWORK
USDT_NETWORK = TradeEnv.USDT_NETWORK

class RebalancingManager:
    def __init__(self):
        self.is_rebalancing = False
        self.last_warning_time = None
        self.bot = telebot.TeleBot(TelegramSetting.TOKEN)

    def should_send_warning(self, warning_interval_seconds=600):
        if self.last_warning_time is None:
            return True
        return (datetime.datetime.now() - self.last_warning_time).total_seconds() >= warning_interval_seconds
    
    def check_wallet_conditions(self, primary_balance, secondary_balance, 
                                primary_buy_price, secondary_buy_price,
                                rebalance_config):
        primary_usdt = primary_balance.get("amount_usdt", {}).get("total", 0)
        primary_coin = primary_balance.get('amount_coin', {}).get("total", 0)
        secondary_usdt = secondary_balance.get("amount_usdt", {}).get("total", 0)
        secondary_coin = secondary_balance.get('amount_coin', {}).get("total", 0)
        wallet_not_enough = (
            primary_usdt < rebalance_config.usdt_threshold or 
            secondary_usdt < rebalance_config.usdt_threshold or 
            secondary_coin * secondary_buy_price < rebalance_config.coin_threshold or 
            primary_coin * primary_buy_price < rebalance_config.coin_threshold
        )
        
        return wallet_not_enough
    
    def handle_low_balance(self, primary_ccxt, secondary_ccxt, symbol,
                          primary_orderbook, secondary_orderbook,
                          primary_balance, secondary_balance,
                          rebalance_config, arbitrage_threshold):
        if self.should_send_warning():
            primary_code = primary_ccxt.id
            secondary_code = secondary_ccxt.id
            msg = f"Warning exchange {primary_code}/{secondary_code}"
            msg += f"\n COIN {primary_balance['amount_coin']['total']:.2f} / {secondary_balance['amount_coin']['total']:.2f}"
            msg += f"\n USDT {primary_balance['amount_usdt']['total']:.2f} / {secondary_balance['amount_usdt']['total']:.2f}"
            self.bot.send_message(TelegramSetting.CHAT_WARNING_ID, msg)
            self.last_warning_time = datetime.datetime.now()
        if not self.is_rebalancing:
            try:
                _is_rebalancing = rebalancing(primary_ccxt, secondary_ccxt, symbol,
                          primary_orderbook, secondary_orderbook,
                          primary_balance, secondary_balance,
                          rebalance_config, arbitrage_threshold)
                self.is_rebalancing = _is_rebalancing
            except Exception as ex:
                self.is_rebalancing = False
                from exchange.util.telegram_utils import send_error_telegram
                send_error_telegram(ex, "Rebalancing Failed", self.bot)
                raise
    
    def reset_rebalancing_state(self):
        self.is_rebalancing = False

current_time = datetime.datetime.now()
def rebalancing(primary: ccxt.Exchange, secondary: ccxt.Exchange, symbol: str, 
                primary_order_book, secondary_order_book,
                primary_balance, secondary_balance,
                rebalance_config, arbitrage_threshold):
    global current_time
    if not rebalance_config.enabled:
        print("Auto rebalance is OFF")
        return False
    trend = detect_trend(primary_order_book, secondary_order_book, TradeEnv.TREND_THRESHOLD)
    if not trend:
        print("No Trend arbitrage.")
        return False
    trading_data = load_trading_data()
    total_fees = trading_data.get("total_fees", 0)
    is_withdraw = False
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
        primary_bid = primary_order_book["bids"][0][0] if primary_order_book["bids"] else None
        secondary_bid = secondary_order_book["bids"][0][0] if secondary_order_book["bids"] else None

        primary_usdt = primary_balance.get("amount_usdt", {}).get("total", 0)
        primary_coin = primary_balance.get('amount_coin', {}).get("total", 0)
        secondary_usdt = secondary_balance.get("amount_usdt", {}).get("total", 0)
        secondary_coin = secondary_balance.get('amount_coin', {}).get("total", 0)

        total_usdt = primary_usdt + secondary_usdt
        total_coin = primary_coin + secondary_coin

        if trend == "sell_primary":
            # Transfer coin: secondary -> primary
            if primary_coin * primary_bid < rebalance_config.coin_threshold:
                transfer_amount = total_coin * rebalance_config.coin_ratio - primary_coin
                available_balance = secondary_balance.get('amount_coin', {}).get("free", 0)
                if transfer_amount > available_balance:
                    if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                        message = f"[{secondary.id.upper()}] ⚠️ Available balance not enough to withdraw.\n" \
                                  f"Withdraw Amount: {transfer_amount:.4f} {base_coin}, Available: {available_balance:.4f} {base_coin}"
                        bot.send_message(TelegramSetting.CHAT_WARNING_ID, message)
                        current_time = datetime.datetime.now()
                elif transfer_amount > 0:
                    trade_info = maximum_quantity_trade_able(secondary_order_book, primary_order_book, arbitrage_threshold)
                    quantity_trade_able = trade_info["quantity"]
                    if quantity_trade_able > available_balance:
                        # Nếu lượng có thể trade > lượng coin đang có → chuyển gần hết luôn trừ lại $10
                        transfer_amount = available_balance - 10 / secondary_bid
                    transaction = secondary.withdraw(
                        base_coin,
                        round(transfer_amount, 4),
                        PRIMARY_COIN_ADDRESS,
                        tag=None,
                        params={"network": COIN_NETWORK},
                    )
                    total_fees += secondary_fee
                    is_withdraw = True
                    message = f"{base_coin}: {secondary.id} -> {primary.id}\nAmount: {transfer_amount:.4f}\nFees: {secondary_fee} {base_coin}\nTotal Fees: {total_fees} {base_coin}"
                    bot.send_message(TelegramSetting.CHAT_WARNING_ID, message)
                    print(message)

            # Transfer USDT: primary -> secondary
            if secondary_usdt < rebalance_config.usdt_threshold:
                transfer_amount = total_usdt * rebalance_config.usdt_ratio - secondary_usdt
                available_balance = primary_balance.get('amount_usdt', {}).get("free", 0)
                if transfer_amount > available_balance:
                    if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                        message = f"[{primary.id.upper()}] ⚠️ Available balance not enough to withdraw.\n" \
                            f"Withdraw Amount: {transfer_amount:.4f} USDT, Available: {available_balance:.4f} USDT"
                        bot.send_message(TelegramSetting.CHAT_WARNING_ID, message)
                        current_time = datetime.datetime.now()
                elif transfer_amount > 0:
                    transaction = primary.withdraw(
                        "USDT",
                        round(transfer_amount, 4),
                        SECONDARY_USDT_ADDRESS,
                        tag=None,
                        params={"network": USDT_NETWORK},
                    )
                    is_withdraw = True
                    print(f"USDT withdrawal transaction: {transaction}")

        elif trend == "buy_primary":
            # Transfer coin: primary -> secondary
            if secondary_coin * secondary_bid < rebalance_config.coin_threshold:
                transfer_amount = total_coin * rebalance_config.coin_ratio - secondary_coin
                available_balance = primary_balance.get('amount_coin', {}).get("free", 0)
                if transfer_amount > available_balance:
                    if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                        message = f"[{primary.id.upper()}] ⚠️ Available balance not enough to withdraw.\n" \
                                  f"Withdraw Amount: {transfer_amount:.4f} {base_coin}, Available: {available_balance:.4f} {base_coin}"
                        bot.send_message(TelegramSetting.CHAT_WARNING_ID, message)
                        current_time = datetime.datetime.now()
                elif transfer_amount > 0:
                    trade_info = maximum_quantity_trade_able(primary_order_book, secondary_order_book, arbitrage_threshold)
                    quantity_trade_able = trade_info["quantity"]
                    if quantity_trade_able > available_balance:
                        # Nếu lượng có thể trade > lượng coin đang có → chuyển gần hết luôn trừ lại $10
                        transfer_amount = available_balance - 10 / primary_bid
                    transaction = primary.withdraw(
                        base_coin,
                        round(transfer_amount, 4),
                        SECONDARY_COIN_ADDRESS,
                        tag=None,
                        params={"network": COIN_NETWORK},
                    )
                    total_fees += primary_fee
                    is_withdraw = True
                    message = f"{base_coin}: {primary.id} -> {secondary.id}\nAmount: {transfer_amount:.2f}\nFees: {primary_fee} {base_coin}\nTotal Fees: {total_fees} {base_coin}"
                    bot.send_message(TelegramSetting.CHAT_WARNING_ID, message)
                    print(message)

            # Transfer USDT: secondary -> primary
            
            if primary_usdt < rebalance_config.usdt_threshold:
                transfer_amount = total_usdt * rebalance_config.usdt_ratio - primary_usdt
                available_balance = secondary_balance.get('amount_usdt', {}).get("free", 0)
                if transfer_amount > available_balance:
                    if (datetime.datetime.now() - current_time).total_seconds() >= 600:
                        message = f"[{secondary.id.upper()}] ⚠️ Available balance not enough to withdraw.\n" \
                                f"Withdraw Amount: {transfer_amount:.4f} USDT, Available: {available_balance:.4f} USDT"
                        bot.send_message(TelegramSetting.CHAT_WARNING_ID, message)
                        current_time = datetime.datetime.now()
                elif transfer_amount > 0:
                    transaction = secondary.withdraw(
                        "USDT",
                        round(transfer_amount, 4),
                        PRIMARY_USDT_ADDRESS,
                        tag=None,
                        params={"network": USDT_NETWORK},
                    )
                    is_withdraw = True
                    print(f"USDT withdrawal transaction: {transaction}")

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
    return is_withdraw

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

def detect_trend(primary_order_book, secondary_order_book, threshold=1.006):
    try:
        primary_bid = primary_order_book["bids"][0][0] if primary_order_book["bids"] else None
        primary_ask = primary_order_book["asks"][0][0] if primary_order_book["asks"] else None
        secondary_bid = secondary_order_book["bids"][0][0] if secondary_order_book["bids"] else None
        secondary_ask = secondary_order_book["asks"][0][0] if secondary_order_book["asks"] else None

        if not all([primary_bid, primary_ask, secondary_bid, secondary_ask]):
            return None

        # Trigger earlier than the strict threshold
        if primary_bid > secondary_ask * threshold:
            return "sell_primary"
        elif secondary_bid > primary_ask * threshold:
            return "buy_primary"
        else:
            return None

    except Exception as e:
        print(f"Error detecting trend: {e}")
        return None
