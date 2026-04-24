import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from plotly.subplots import make_subplots
from datetime import datetime

# 1. PAGE CONFIG & ELITE THEME
st.set_page_config(page_title="Marcus.Ai Elite V3", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1a1c23; padding: 15px; border-radius: 12px; border: 1px solid #30363d; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# 2. INITIALIZE SESSION STATE (The Trading Brain)
if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []
if 'balance' not in st.session_state:
    st.session_state.balance = 100000.0  # Start with $100k Paper Money

# 3. MEGA WATCHLIST (75+ Assets)
tickers = [
    "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", # Crypto
    "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "AMD", "NFLX", "JPM", "COST", # Big Tech & Finance
    "BABB", "LFVN", "VFF", "TKNO", "MAPS", "LX", "FINV", "III", "GGRO.U", "SIGA", # Penny & Small Cap
    "ARAI", "CHGG", "PDSB", "HURA", "CURV", "DSWL", "AHCO", "GHG", "TZOO", "YRD", # More Pennies
    "PLTR", "SOFI", "HOOD", "RIVN", "LCID", "NIO", "XPEV", "LI", "F", "GM", "DIS", "PYPL",
    "BABA", "JD", "PDD", "MSTR", "COIN", "MARA", "RIOT", "CLSK", "WMT", "TGT", "HD", "LOW",
    "UNH", "LLY", "V", "MA", "ORCL", "CRM", "ADBE", "INTC", "MU", "AVGO", "QCOM", "TXN"
]

st.sidebar.header("🕹️ Marcus.Ai Control")
ticker = st.sidebar.selectbox("🎯 Target Asset", sorted(list(set(tickers))))
qty = st.sidebar.number_input("Order Quantity", min_value=1, value=10)

# 4. LIVE DATA ENGINE
def get_live_data(symbol):
    try:
        data = yf.download(symbol, period="1d", interval="1m", progress=False)
        if data.empty: return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data['MA10'] = data['Close'].rolling(10).mean()
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        data['RSI'] = 100 - (100 / (1 + gain/loss))
        return data
    except:
        return None

df = get_live_data(ticker)

if df is not None and len(df) > 10:
    # --- AI CALCULATIONS ---
    df_ai = df.tail(20).reset_index()
    X = np.array(df_ai.index).reshape(-1, 1)
    y = df_ai['Close'].values.flatten()
    ai_model = LinearRegression().fit(X, y)
    prediction = float(ai_model.predict(np.array([[len(df_ai) + 5]]))[0])
    slope = ai_model.coef_[0]

    # --- DASHBOARD HEADER ---
    curr_price = float(df['Close'].values[-1])
    rsi = float(df['RSI'].values[-1])
    
    st.title(f"🚀 Marcus.Ai Elite Terminal: {ticker}")
    
    # --- TRADING INTERFACE ---
    col_a, col_b, col_c = st.columns([2, 1, 1])
    
    with col_a:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='cyan', opacity=0.4), row=2, col=1)
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("💳 Wallet")
        st.metric("Paper Balance", f"${st.session_state.balance:,.2f}")
        
        if st.button("🟢 BUY EXECUTION"):
            cost = curr_price * qty
            if st.session_state.balance >= cost:
                st.session_state.balance -= cost
                st.session_state.trade_log.append({
                    "Time": datetime.now().strftime("%H:%M:%S"),
                    "Symbol": ticker, "Type": "BUY", "Qty": qty, "Price": round(curr_price, 4), "Total": round(cost, 2)
                })
                st.success(f"Bought {qty} {ticker}")
            else:
                st.error("Insufficient Funds!")

    with col_c:
        st.subheader("🤖 AI Advice")
        if slope > 0.001 and rsi < 65: st.success("SIGNAL: STRONG BUY")
        elif slope < -0.001 and rsi > 35: st.error("SIGNAL: STRONG SELL")
        else: st.warning("SIGNAL: HOLD")
        
        if st.button("🔴 SELL EXECUTION"):
            revenue = curr_price * qty
            st.session_state.balance += revenue
            st.session_state.trade_log.append({
                "Time": datetime.now().strftime("%H:%M:%S"),
                "Symbol": ticker, "Type": "SELL", "Qty": qty, "Price": round(curr_price, 4), "Total": round(revenue, 2)
            })
            st.info(f"Sold {qty} {ticker}")

    # --- METRICS BAR ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Live Price", f"${round(curr_price, 4)}")
    m2.metric("AI Target (5m)", f"${round(prediction, 4)}")
    m3.metric("RSI Momentum", f"{round(rsi, 1)}")
    m4.metric("Order Value", f"${round(curr_price * qty, 2):,}")

    # --- TRADE LOGS ---
    st.subheader("📜 Live Trade Logs")
    if st.session_state.trade_log:
        log_df = pd.DataFrame(st.session_state.trade_log).iloc[::-1] # Show newest first
        st.table(log_df)
    else:
        st.write("No trades executed in this session yet.")

else:
    st.info("🌙 Market is Closed for this asset. Switch to **BTC-USD** to test the Buy/Sell and Logs!")