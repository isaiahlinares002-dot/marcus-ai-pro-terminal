import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import pytz
from supabase import create_client, Client

# --- 1. CONFIG & SYSTEM KEYS ---
st.set_page_config(page_title="MARCUS ELITE V5.7.2", layout="wide")
toronto_tz = pytz.timezone('America/Toronto')

# Credentials - Synced to your xhxzhnzwvxmycdskjarr project
SUPABASE_URL = "https://xhxzhnzwvxmycdskjarr.supabase.co"
SUPABASE_KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. THE IMPROVED MATH (ULTRA LOGIC) ---
def calculate_marcus_signals(df):
    """
    V5.7.2 Math: EMA9/21 Cross + Slope Velocity.
    Ensures momentum is high enough to avoid 'flat' noise.
    """
    if len(df) < 21:
        return "🟡 INITIALIZING", df['close'].iloc[-1]
    
    # Calculate EMAs
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # Velocity (Slope) check
    df['slope'] = df['EMA9'].diff()
    
    last_ema9 = df['EMA9'].iloc[-1]
    last_ema21 = df['EMA21'].iloc[-1]
    last_slope = df['slope'].iloc[-1]
    last_price = df['close'].iloc[-1]
    
    # Logic: Cross + Threshold (0.05)
    if (last_ema9 > last_ema21) and (last_slope > 0.05):
        return "🔥 ULTRA BUY", last_price
    elif (last_ema9 < last_ema21) and (last_slope < -0.05):
        return "🔴 ULTRA SELL", last_price
        
    return "🟡 NEUTRAL", last_price

# --- 3. ASSET LIBRARIES ---
RUNNERS = ["NVDA", "TSLA", "AAPL", "BTC-USD", "ETH-USD"]
STOCK_LIBRARY = sorted([
    "GOOGL", "MSFT", "AMZN", "META", "NFLX", "AMD", "INTC", "PYPL", "SQ", "SHOP",
    "CRWD", "PLTR", "SNOW", "TSM", "ASML", "SBUX", "DIS", "BA", "CAT", "GE",
    "JPM", "GS", "V", "MA", "UBER", "LYFT", "ABNB", "COIN", "MARA", "RIOT",
    "PFE", "MRNA", "UNH", "XOM", "CVX", "COST", "WMT", "TGT", "NKE", "F",
    "GM", "RIVN", "LCID", "BABA", "JD", "PDD", "BIDU", "NTES", "LI", "XPEV",
    "DKNG", "PENN", "PLUG", "FCEL", "SPCE", "AMC", "GME", "HOOD", "SOFI", "U",
    "NET", "OKTA", "DDOG", "ZS", "CRSR", "LOGI", "RBLX", "SE", "MELI"
])

# --- 4. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = None
if 'balance' not in st.session_state: st.session_state.balance = 100000.0
if 'auto_pilot' not in st.session_state: st.session_state.auto_pilot = False

# --- 5. DATABASE FUNCTIONS ---
def check_login(u, p):
    try:
        res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
        return len(res.data) > 0
    except: return False

def log_trade(ticker, side, price):
    try:
        data = {
            "username": st.session_state.username,
            "ticker": ticker,
            "side": side,
            "price": float(price),
            "balance": float(st.session_state.balance),
            "created_at": datetime.now(toronto_tz).isoformat()
        }
        supabase.table("trades").insert(data).execute()
        st.toast(f"✅ {side} {ticker} Logged to DB")
    except Exception as e: st.error(f"Sync Error: {e}")

# --- 6. USER INTERFACE ---
if not st.session_state.logged_in:
    st.title("🚀 Marcus Elite Terminal")
    u = st.text_input("User ID")
    p = st.text_input("Password", type="password")
    if st.button("Enter Terminal"):
        if check_login(u, p):
            st.session_state.logged_in, st.session_state.username = True, u
            st.rerun()
        else: st.error("Access Denied.")
else:
    # --- Sidebar ---
    with st.sidebar:
        st.header(f"Elite: {st.session_state.username}")
        st.metric("WALLET", f"${st.session_state.balance:,.2f}")
        if st.button("🔄 RESET BALANCE TO $100K"): 
            st.session_state.balance = 100000.0
            st.rerun()
        
        st.markdown("---")
        st.session_state.auto_pilot = st.toggle("🤖 ACTIVATE GLOBAL AI PILOT")
        
        st.subheader("⚡ Runners")
        sel_runner = st.radio("Momentum:", RUNNERS)
        st.subheader("🔍 Library")
        sel_lib = st.selectbox("Search 80+ Stocks:", ["None"] + STOCK_LIBRARY)
        
        active_ticker = sel_lib if sel_lib != "None" else sel_runner
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # --- Main Dashboard ---
    now_toronto = datetime.now(toronto_tz)
    c1, c2 = st.columns([3, 1])
    c1.title(f"📊 {active_ticker} Terminal")
    c2.metric("TORONTO (EDT)", now_toronto.strftime("%I:%M:%S %p"))

    # Generate Simulated Chart Data (50 periods for Math)
    df = pd.DataFrame({
        'Date': pd.date_range(end=now_toronto, periods=50, freq='min'),
        'open': np.random.uniform(150, 160, 50),
        'high': np.random.uniform(160, 165, 50),
        'low': np.random.uniform(145, 150, 50),
        'close': np.random.uniform(150, 160, 50)
    })
    
    # Run Math
    signal, price = calculate_marcus_signals(df)
    
    # Plotly Candles
    fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # AI Execution
    if st.session_state.auto_pilot and "ULTRA" in signal:
        log_trade(active_ticker, signal, price)

    # Dashboard HUD
    st.markdown("---")
    h1, h2, h3 = st.columns(3)
    h1.metric("Live Price", f"${price:,.2f}")
    h2.metric("AI Signal", signal)
    if h3.button(f"📝 MANUAL LOG: {active_ticker}"):
        log_trade(active_ticker, "MANUAL", price)

    if st.button("⚠️ WIPE ALL TRADES", type="primary"):
        supabase.table("trades").delete().eq("username", st.session_state.username).execute()
        st.success("Database Purged.")
