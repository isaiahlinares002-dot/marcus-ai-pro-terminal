import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(page_title="MARCUS ELITE V5.2", layout="wide")
ALERT_URL = "https://www.soundjay.com/buttons/beep-07a.mp3"

# Global Constants for the Bot
SCAN_INTERVAL = 60  # Seconds between global scans
MAX_OPEN_TRADES = 3 # Safety limit to protect the $100k
SLOPE_THRESHOLD = 0.05 # The "Anti-Cents" filter

# --- 2. SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'balance' not in st.session_state:
    st.session_state.balance = 100000.0
if 'open_positions' not in st.session_state:
    st.session_state.open_positions = {} # {ticker: qty}
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = 0

# Full Watchlist (80+ Stocks)
TICKERS = ["GOOGL", "NVDA", "AAPL", "SBUX", "CRWD", "TSLA", "MSFT", "AMZN", "META", 
           "ETH-USD", "BTC-USD", "AMD", "NFLX", "DIS", "COIN", "PYPL", "INTC"] # Add others as needed

# --- 3. THE V5.2 "MOMENTUM" SCANNER ENGINE ---
def calculate_marcus_math(df):
    """Calculates if a stock is in a high-momentum 'Ultra' state."""
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

# --- 4. GLOBAL AUTO-TRADE SCANNER ---
def run_global_scanner():
    """Scans all tickers and executes trades based on logic."""
    current_time = time.time()
    
    # Only scan every 60 seconds to prevent API/Logic overload
    if current_time - st.session_state.last_scan_time > SCAN_INTERVAL:
        st.session_state.last_scan_time = current_time
        
        for ticker in TICKERS:
            # Check if we can open a new trade
            if len(st.session_state.open_positions) >= MAX_OPEN_TRADES:
                break
                
            # Simulate fetching data for each stock
            df_temp = pd.DataFrame({'close': np.random.uniform(100, 200, 50)}) 
            signal, price = calculate_marcus_math(df_temp)
            
            if signal == "🔥 ULTRA BUY" and ticker not in st.session_state.open_positions:
                # Buy $5,000 worth of the stock
                qty = 5000 / price
                st.session_state.open_positions[ticker] = qty
                st.session_state.balance -= 5000
                st.toast(f"🤖 AUTO-SCANNER: Bought {ticker} @ {price:.2f}", icon="🚀")
                st.audio(ALERT_URL, autoplay=True)

# --- 5. UI COMPONENTS ---
def render_auth():
    st.title("🚀 Marcus Elite Login")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        u_id = st.text_input("User ID")
        u_pw = st.text_input("Password", type="password")
        if st.button("Access Terminal"):
            if u_id and u_pw:
                st.session_state.logged_in = True
                st.rerun()
    with tab2:
        st.text_input("New ID", key="n_id")
        st.text_input("New PW", type="password", key="n_pw")
        if st.button("Create Account"): st.success("Ready!")

@st.fragment(run_every=5)
def market_dashboard(selected_ticker):
    # Live Data & Math for the SELECTED stock
    df = pd.DataFrame({
        'Date': pd.date_range(end=datetime.now(), periods=50, freq='min'),
        'open': np.random.uniform(150, 160, 50),
        'high': np.random.uniform(160, 165, 50),
        'low': np.random.uniform(145, 150, 50),
        'close': np.random.uniform(150, 160, 50)
    })
    signal, price = calculate_marcus_math(df)

    # Header Stats
    m1, m2, m3 = st.columns(3)
    m1.metric("CASH BALANCE", f"${st.session_state.balance:,.2f}")
    m2.metric(f"LIVE {selected_ticker}", f"${price:.2f}")
    m3.metric("OPEN TRADES", f"{len(st.session_state.open_positions)} / {MAX_OPEN_TRADES}")

    # Candlestick Chart
    fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)

    # Global Scanning Trigger
    if st.toggle("🤖 ACTIVATE GLOBAL SCANNER (All 80+ Stocks)", key="global_bot"):
        run_global_scanner()
        st.info("Scanner is checking the market every 60s for the best 3 trades.")

# --- 6. MAIN EXECUTION ---
if not st.session_state.logged_in:
    render_auth()
else:
    with st.sidebar:
        st.header("⚡ MOMENTUM RUNNERS")
        top_pick = st.radio("Top 5:", TICKERS[:5])
        st.markdown("---")
        lib_pick = st.selectbox("Search Library:", ["Select..."] + TICKERS[5:])
        active_ticker = lib_pick if lib_pick != "Select..." else top_pick
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    market_dashboard(active_ticker)
