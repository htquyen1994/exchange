from collections import deque

def maximum_quantity_trade_able(buy_order_book, sell_order_book, threshold, max_trade_quantity=None):
    """
    Find the maximum tradable quantity between two order books
    while satisfying the arbitrage threshold condition.

    Args:
        buy_order_book: {"asks": deque([(price, quantity), ...])}
        sell_order_book: {"bids": deque([(price, quantity), ...])}
        threshold: arbitrage threshold (multiplier)
        max_trade_quantity: optional, maximum trade quantity limit.
                            If None, trade as much as order books allow.

    Returns:
        {"buy_price": float, "sell_price": float, "quantity": float}
    """
    asks = deque([list(x) for x in buy_order_book.get("asks", [])])  # [price, qty]
    bids = deque([list(x) for x in sell_order_book.get("bids", [])])

    if not asks or not bids:
        return {"buy_price": 0.0, "sell_price": 0.0, "quantity": 0.0}

    result = {
        "buy_price": asks[0][0],
        "sell_price": bids[0][0],
        "quantity": 0.0
    }

    while asks and bids:
        buy_price, buy_quantity = asks[0]
        sell_price, sell_quantity = bids[0]

        if sell_price <= buy_price * threshold:
            break

        result["buy_price"] = buy_price
        result["sell_price"] = sell_price

        # nếu có giới hạn trade thì tính phần còn lại, nếu không thì vô hạn
        remain = float("inf") if max_trade_quantity is None else max_trade_quantity - result["quantity"]
        if remain <= 0:
            break

        # chọn khối lượng giao dịch nhỏ nhất có thể
        trade_qty = min(buy_quantity, sell_quantity, remain)
        result["quantity"] += trade_qty

        # trừ khối lượng đã dùng
        if buy_quantity > trade_qty:
            asks[0][1] = buy_quantity - trade_qty
        else:
            asks.popleft()

        if sell_quantity > trade_qty:
            bids[0][1] = sell_quantity - trade_qty
        else:
            bids.popleft()

    return result