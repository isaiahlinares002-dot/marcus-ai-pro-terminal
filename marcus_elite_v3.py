import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time as dt_time
import pytz
from supabase import create_client, Client

# --- 1. SETTINGS & SYSTEM KEYS ---
st.set_page_config(page_title="MARCUS ELITE V5.4.4", layout="wide")
ALERT_URL = "https://www.soundjay.com/buttons/beep-07a.mp3"
toronto_tz = pytz.timezone('America/Toronto')

# Verified credentials for your specific Supabase project
SUPABASE_URL = "https://xhxzhnzwvxmycdskjarr.supabase.co"
SUPABASE_KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Trading Bot Rules
SCAN_INTERVAL = 60 
MAX_OPEN_TRADES = 3
SLOPE_THRESHOLD = 0.05 # Marcus Elite V5 math

# --- 2. SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'balance' not in st.session_state:
    st.session_state.balance = 100000.0
if 'trading_journal' not in st.session_state:
    st.session_state.trading_journal = []

TICKERS = ["GOOGL", "NVDA", "AAPL", "SBUX", "CRWD", "TSLA", "MSFT", "AMZN", "META", "ETH-USD", "BTC-USD"]

# --- 3. DATABASE & AUTH (Synced to your 'users' and 'trades' tables) ---
def check_login(u, p):
    try:
        res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
        return len(res.data) > 0
    except: return False

def create_user(u, p):
    try:
        supabase.table("users").insert({"username": u, "password": p}).execute()
        return True
    except: return False

def wipe_history():
    """Permanently clears the 'trades' table to reset the 100-trade quest."""
    try:
        # Deletes only the trades belonging to you
        supabase.table("trades").delete().eq("username", st.session_state.username).execute()
        st.session_state.trading_journal = []
        st.session_state.balance = 100000.0
        st.success("🔥 Database Purged. Quest Reset to 0/100.")
        st.audio(ALERT_URL, autoplay=True)
    except Exception as e:
        st.error(f"Wipe Failed: {e}")

def log_trade_to_db(ticker, side, price):
    try:
        data = {
            "username": st.session_state.username,
            "ticker": ticker,
            "side": side,
            "price": float(price),
            "balance": st.session_state.balance,
            "created_at": datetime.now(toronto_tz).isoformat()
        }
        supabase.table("trades").insert(data).execute()
        st.session_state.trading_journal.append(data)
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- 4. THE MOMENTUM ENGINE ---
def calculate_marcus_math(df):
    if len(df) < 21: return "🟡 INIT", df['close'].iloc[-1]
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['slope'] = df['EMA9'].diff()
    last_price = df['close'].iloc[-1]
    last_slope = df['slope'].iloc[-1]
    
    if (df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1]) and (last_slope > SLOPE_THRESHOLD):
        return "🔥 ULTRA BUY", last_price
    elif (df['EMA9'].iloc[-1] < df['EMA21'].iloc[-1]) and (last_slope < -SLOPE_THRESHOLD):
        return "🔴 ULTRA SELL", last_price
    return "🟡 NEUTRAL", last_price

# --- 5. THE TERMINAL UI ---
@st.fragment(run_every=5)
def market_dashboard(active_ticker):
    now_toronto = datetime.now(toronto_tz)
    
    # Header Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("TORONTO TIME", now_toronto.strftime("%I:%M:%S %p"))
    m2.metric("QUEST PROGRESS", f"{len(st.session_state.trading_journal)} / 100")
    m3.info("MARKET OPEN" if (9 <= now_toronto.hour < 16) else "MARKET CLOSED (Simulation Mode)")

    # Charting
    df = pd.DataFrame({
        'Date': pd.date_range(end=now_toronto, periods=50, freq='min'),
        'open': np.random.uniform(150, 160, 50), 'high': np.random.uniform(160, 165, 50),
        'low': np.random.uniform(145, 150, 50), 'close': np.random.uniform(150, 160, 50)
    })
    signal, price = calculate_marcus_math(df)
    
    fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # Controls
    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button(f"📝 Log Trade: {active_ticker}"):
        log_trade_to_db(active_ticker, signal, price)
        st.toast("Trade Synced to Supabase!")
    
    if c2.button("⚠️ WIPE MY DATA", type="primary"):
        wipe_history()

    # Live Journal View
    if st.session_state.trading_journal:
        st.subheader("📓 Live Trading Journal")
        st.table(pd.DataFrame(st.session_state.trading_journal).tail(5))

# --- 6. MAIN FLOW ---
if not st.session_state.logged_in:
    st.title("🚀 Marcus Elite Terminal")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        u = st.text_input("User ID", key="l_u")
        p = st.text_input("Password", type="password", key="l_p")
        if st.button("Enter Terminal"):
            if check_login(u, p):
                st.session_state.logged_in = True
                st.session_state.username = u
                st.rerun()
            else: st.error("Invalid ID/Password")
    with tab2:
        nu = st.text_input("New ID", key="s_u")
        np = st.text_input("New PW", type="password", key="s_p")
        if st.button("Create Account"):
            if create_user(nu, np): st.success("Account Created! Use Login tab.")
else:
    with st.sidebar:
        st.header(f"Elite: {st.session_state.username}")
        active_ticker = st.selectbox("Select Asset", TICKERS)
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    market_dashboard(active_ticker)
