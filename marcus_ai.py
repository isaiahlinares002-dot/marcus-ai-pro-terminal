import yfinance as yf
import pandas as pd
import numpy as np
import model
import database

class MarcusAI:

    def __init__(self):
        self.features = [
            "RSI",
            "MACD",
            "Signal",
            "SMA20",
            "SMA50",
            "Volume"
        ]

    def get_data(self, symbol):
        data = yf.download(symbol, period="3mo", interval="5m", progress=False)
        return data

    def indicators(self, data):

        data["SMA20"] = data["Close"].rolling(20).mean()
        data["SMA50"] = data["Close"].rolling(50).mean()

        # RSI
        delta = data["Close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        data["RSI"] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = data["Close"].ewm(span=12).mean()
        exp2 = data["Close"].ewm(span=26).mean()

        data["MACD"] = exp1 - exp2
        data["Signal"] = data["MACD"].ewm(span=9).mean()

        # ML target
        data["Return"] = data["Close"].pct_change()
        data["Target"] = (data["Return"].shift(-1) > 0).astype(int)

        return data.dropna()

    def analyze(self, symbol):

        data = self.get_data(symbol)

        if data is None or len(data) < 100:
            return None

        data = self.indicators(data)

        X = data[self.features]
        y = data["Target"]

        ml_model = model.train_model(X, y)

        latest = data.iloc[-1:][self.features]

        prediction = ml_model.predict(latest)[0]
        probability = ml_model.predict_proba(latest)[0].max()

        if prediction == 1:
            signal = "BUY"
        else:
            signal = "SELL"

        confidence = round(probability * 100, 2)
        risk = round((1 - probability) * 100, 2)

        win_rate = database.get_win_rate()

        latest_row = data.iloc[-1]

        reasons = []

        if latest_row["SMA20"] > latest_row["SMA50"]:
            reasons.append("Uptrend")

        if latest_row["RSI"] < 30:
            reasons.append("Oversold")

        if latest_row["MACD"] > latest_row["Signal"]:
            reasons.append("MACD Bullish")

        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "risk": risk,
            "win_rate": win_rate,
            "price": float(latest_row["Close"]),
            "reasons": reasons
        }