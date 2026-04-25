import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from plotly.subplots import make_subplots
from datetime import datetime
import sqlite3
import hashlib

# 1. DATABASE ENGINE (Permanent Memory)
conn = sqlite3.connect('marcus_pro.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users 
             (username TEXT PRIMARY KEY, password TEXT, balance REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS trades 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT, time TEXT, symbol TEXT, type TEXT, qty INTEGER, price REAL, total REAL)''')
conn.commit()

# 2. ELITE STYLING
st.set_page_config(page_title="Marcus.Ai Elite Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1a1c23; padding: 15px; border-radius: 12px; border: 1px solid #30363d; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #21262d; color: white; border: 1px solid #30363d; }
    .stButton>button:hover { border-color: #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

# 3. AUTHENTICATION LOGIC
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 Marcus.Ai Secure Gateway")
    auth_mode = st.sidebar.selectbox("Access Mode", ["Login", "Sign Up"])

    if auth_mode == "Login":
        user = st.text_input("Username")
        pw = st.text_input("Password", type='password')
        if st.button("Enter Terminal"):
            c.execute('SELECT password FROM users WHERE username =?', (user,))
            data = c.fetchone()
            if data and check_hashes(pw, data[0]):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.rerun()
            else:
                st.error("Invalid Credentials")
    
    else:
        new_user = st.text_input("New Username")
        new_pw = st.text_input("New Password", type='password')
        if st.button("Create Account"):
            try:
                c.execute('INSERT INTO users(username, password, balance) VALUES (?,?,?)', 
                          (new_user, make_hashes(new_pw), 100000.0))
                conn.commit()
                st.success("Account Created! Switch to Login Mode.")
            except:
                st.error("Username already exists.")
    st.stop()

# 4. LOAD ACTIVE USER SESSION
user_name = st.session_state.username
c.execute('SELECT balance FROM users WHERE username=?', (user_name,))
current_balance = c.fetchone()[0]

# 5. MEGA WATCHLIST (75+ Tickers)
tickers = [
    "BTC-USD", "ETH-USD", "SOL-USD", "PEPE-USD", "DOGE-USD", # Crypto
    "BABB", "LFVN", "VFF", "TKNO", "MAPS", "LX", "FINV", "III", "GGRO.U", # Pennies
    "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "AMD", "PLTR", # Tech
    "SOFI", "HOOD", "RIVN", "LCID", "NIO", "MSTR", "COIN", "MARA", "RIOT",
    "JPM", "GS", "V", "MA", "PYPL", "SQ", "WMT", "TGT", "COST", "HD", "LOW"
]

ticker = st.sidebar.selectbox("🎯 Target Asset", sorted(list(set(tickers))))
qty = st.sidebar.number_input("Units", min_value=1, value=10)

# 6. LIVE DATA ENGINE
def get_live_data(symbol):
    try:
        data = yf.download(symbol, period="1d", interval="1m", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data['MA10'] = data['Close'].rolling(10).mean()
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        data['RSI'] = 100 - (100 / (1 + gain/loss))
        return data
    except: return None

df = get_live_data(ticker)

if df is not None and len(df) > 10:
    curr_price = float(df['Close'].values[-1])
    
    # AI PREDICTION (Linear Regression)
    df_ai = df.tail(20).reset_index()
    X = np.array(df_ai.index).reshape(-1, 1)
    y = df_ai['Close'].values.flatten()
    ai_model = LinearRegression().fit(X, y)
    prediction = float(ai_model.predict(np.array([[len(df_ai) + 5]]))[0])
    slope = ai_model.coef_[0]

    st.title(f"🚀 {user_name}'s Terminal: {ticker}")

    # 7. DASHBOARD LAYOUT
    col_a, col_b, col_c = st.columns([2.5, 1, 1])
    with col_a:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='cyan', opacity=0.3), row=2, col=1)
        fig.update_layout(height=450, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("💰 Vault")
        st.metric("Balance", f"${current_balance:,.2f}")
        if st.button("🟢 BUY EXECUTION"):
            total_cost = curr_price * qty
            if current_balance >= total_cost:
                new_balance = current_balance - total_cost
                c.execute('UPDATE users SET balance=? WHERE username=?', (new_balance, user_name))
                c.execute('INSERT INTO trades(username, date, time, symbol, type, qty, price, total) VALUES (?,?,?,?,?,?,?,?)',
                          (user_name, datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), ticker, "BUY", qty, curr_price, total_cost))
                conn.commit()
                st.rerun()

    with col_c:
        st.subheader("🤖 AI Signal")
        rsi = float(df['RSI'].values[-1])
        if slope > 0.001 and rsi < 65: st.success("STRONG BUY")
        elif slope < -0.001 and rsi > 35: st.error("STRONG SELL")
        else: st.warning("HOLD")
        
        if st.button("🔴 SELL EXECUTION"):
            total_gain = curr_price * qty
            new_balance = current_balance + total_gain
            c.execute('UPDATE users SET balance=? WHERE username=?', (new_balance, user_name))
            c.execute('INSERT INTO trades(username, date, time, symbol, type, qty, price, total) VALUES (?,?,?,?,?,?,?,?)',
                      (user_name, datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), ticker, "SELL", qty, curr_price, total_gain))
            conn.commit()
            st.rerun()

    # 8. PERMANENT LEDGER
    st.divider()
    st.subheader("📊 Trade History")
    history = pd.read_sql_query(f'SELECT date, time, symbol, type, qty, price, total FROM trades WHERE username="{user_name}" ORDER BY id DESC', conn)
    st.dataframe(history, use_container_width=True)

else:
    st.info("Market Closed. Use **BTC-USD** to test the Vault and History.")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()