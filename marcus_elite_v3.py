import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time as dt_time
import pytz
from supabase import create_client, Client

# --- 1. CONFIGURATION & SUPABASE SETUP ---
st.set_page_config(page_title="MARCUS ELITE V5.4.1", layout="wide")
ALERT_URL = "https://www.soundjay.com/buttons/beep-07a.mp3"
toronto_tz = pytz.timezone('America/Toronto')

# --- REPLACE WITH YOUR SUPABASE CREDENTIALS ---
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_KEY = "your-anon-public-key"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Trading Bot Rules
SCAN_INTERVAL = 60 
MAX_OPEN_TRADES = 3
SLOPE_THRESHOLD = 0.05 

# --- 2. SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'balance' not in st.session_state:
    st.session_state.balance = 100000.0
if 'trading_journal' not in st.session_state:
    st.session_state.trading_journal = []

TICKERS = ["GOOGL", "NVDA", "AAPL", "SBUX", "CRWD", "TSLA", "MSFT", "AMZN", "META", "ETH-USD", "BTC-USD"]

# --- 3. DATABASE & AUTH FUNCTIONS ---
def check_login(u, p):
    """Verifies credentials against Supabase profiles table."""
    try:
        res = supabase.table("profiles").select("*").eq("username", u).eq("password", p).execute()
        return len(res.data) > 0
    except: return False

def create_user(u, p):
    """Registers a new user in Supabase."""
    try:
        supabase.table("profiles").insert({"username": u, "password": p}).execute()
        return True
    except: return False

def wipe_supabase_history():
    """Clears trade history for the logged-in user."""
    try:
        supabase.table("trading_journal").delete().eq("username", st.session_state.username).execute()
        st.session_state.trading_journal = []
        st.session_state.balance = 100000.0
        st.success("🔥 DATABASE PURGED: Starting Quest at #1.")
    except Exception as e:
        st.error(f"Wipe Failed: {e}")

def log_trade(ticker, side, price):
    """Saves trade to Supabase tied to the username."""
    try:
        data = {
            "username": st.session_state.username,
            "ticker": ticker,
            "side": side,
            "price": float(price),
            "balance": st.session_state.balance,
            "created_at": datetime.now(toronto_tz).isoformat()
        }
        supabase.table("trading_journal").insert(data).execute()
        st.session_state.trading_journal.append(data)
        st.toast(f"Logged {side} for {ticker}")
    except Exception as e:
        st.error(f"Log Error: {e}")

# --- 4. AUTHENTICATION UI ---
def render_auth():
    st.title("🚀 Marcus Elite Terminal")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        u = st.text_input("User ID", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Access Terminal"):
            if check_login(u, p):
                st.session_state.logged_in = True
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Invalid Credentials")
    
    with tab2:
        new_u = st.text_input("Choose User ID", key="sig_u")
        new_p = st.text_input("Choose Password", type="password", key="sig_p")
        if st.button("Create Account"):
            if create_user(new_u, new_p):
                st.success("Account Created! You can now log in.")
            else:
                st.error("User ID already exists or connection error.")

# --- 5. MAIN TERMINAL FRAGMENT ---
@st.fragment(run_every=5)
def market_dashboard(active_ticker):
    now_toronto = datetime.now(toronto_tz)
    
    # 1. Header Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("USER", st.session_state.username)
    m2.metric("TORONTO TIME", now_toronto.strftime("%I:%M:%S %p"))
    m3.metric("100-TRADE QUEST", f"{len(st.session_state.trading_journal)} / 100")

    # 2. Chart Logic (Placeholder Data)
    df = pd.DataFrame({
        'Date': pd.date_range(end=now_toronto, periods=50, freq='min'),
        'open': np.random.uniform(150, 160, 50), 'high': np.random.uniform(160, 165, 50),
        'low': np.random.uniform(145, 150, 50), 'close': np.random.uniform(150, 160, 50)
    })
    
    fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # 3. Journal & Wipe
    st.subheader("📓 QUEST JOURNAL")
    c1, c2 = st.columns(2)
    if c1.button("📝 Log Trade"):
        log_trade(active_ticker, "MANUAL", df['close'].iloc[-1])
    if c2.button("⚠️ WIPE OLD HISTORY", type="primary"):
        wipe_supabase_history()
    
    if st.session_state.trading_journal:
        st.table(pd.DataFrame(st.session_state.trading_journal).tail(5))

# --- 6. MAIN EXECUTION ---
if not st.session_state.logged_in:
    render_auth()
else:
    with st.sidebar:
        st.header("⚡ MOMENTUM")
        sel = st.radio("Top 5 Runners:", TICKERS[:5])
        lib = st.selectbox("Search 75+ Stocks:", ["Select..."] + TICKERS[5:])
        active_ticker = lib if lib != "Select..." else sel
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
    market_dashboard(active_ticker)
