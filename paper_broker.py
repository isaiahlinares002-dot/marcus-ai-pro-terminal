import database

balance = 10000

def buy(symbol, price, risk_percent):
    global balance

    risk_amount = balance * risk_percent
    size = risk_amount / price

    trade = {
        "symbol": symbol,
        "entry": price,
        "size": size,
        "type": "BUY"
    }

    database.save_open_trade(trade)
    return trade


def sell(symbol, price):
    trade = database.get_open_trade(symbol)

    if trade is None:
        return None

    entry = trade["entry"]
    size = trade["size"]

    profit = (price - entry) * size

    database.close_trade(symbol, price, profit)

    global balance
    balance += profit

    return profit