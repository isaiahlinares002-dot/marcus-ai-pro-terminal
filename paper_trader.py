import yfinance as yf
import pandas as pd
import ta

# Download stock data
ticker = "AAPL"
data = yf.download(ticker, period="1y")

# Ensure Close is a 1D Series
close = data["Close"].squeeze()

# Calculate RSI
rsi_indicator = ta.momentum.RSIIndicator(close=close)
data["RSI"] = rsi_indicator.rsi()

# Example simple trading logic
for i in range(len(data)):
    if data["RSI"].iloc[i] < 30:
        print(f"BUY signal on {data.index[i]} | RSI: {data['RSI'].iloc[i]:.2f}")
    elif data["RSI"].iloc[i] > 70:
        print(f"SELL signal on {data.index[i]} | RSI: {data['RSI'].iloc[i]:.2f}")

# Show last rows
print(data.tail())