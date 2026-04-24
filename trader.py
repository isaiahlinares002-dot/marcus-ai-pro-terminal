import yfinance as yf
import pandas as pd
import numpy as np
import model
import database

STOCKS = [
    "AAPL","MSFT","NVDA","TSLA","AMZN","META","GOOGL",
    "AMD","NFLX","INTC","PLTR","COIN",
    "SPY","QQQ",
    "BTC-USD","ETH-USD","XRP-USD"
]

def get_data(symbol):
    data = yf.download(
        symbol,
        period="3mo",
        interval="5m",
        progress=False
    )

    if data is None or data.empty:
        return None

    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA50"] = data["Close"].rolling(50).mean()

    delta = data["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss

    data["RSI"] = 100 - (100 / (1 + rs))

    exp1 = data["Close"].ewm(span=12).mean()
    exp2 = data["Close"].ewm(span=26).mean()

    data["MACD"] = exp1 - exp2
    data["Signal"] = data["MACD"].ewm(span=9).mean()

    data["Return"] = data["Close"].pct_change()
    data["Target"] = (data["Return"].shift(-1) > 0).astype(int)

    return data.dropna()


def get_ai_signal(data):

    features = [
        "RSI",
        "MACD",
        "Signal",
        "MA20",
        "MA50",
        "Volume"
    ]

    X = data[features]
    y = data["Target"]

    model_trained = model.train_model(X, y)

    latest = data.iloc[-1:][features]

    pred = model_trained.predict(latest)[0]
    prob = model_trained.predict_proba(latest)[0].max()

    win_rate = database.get_win_rate()

    risk = 1 - prob

    if pred == 1:
        signal = "BUY"
    else:
        signal = "SELL"

    confidence = round(prob * 100, 2)
    risk_percent = round(risk * 100, 2)

    return signal, confidence, risk_percent, win_rate