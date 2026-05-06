import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time
import pytz
from supabase import create_client, Client

# --- 1. SYSTEM CONFIG & FIXED CONNECTION ---
st.set_page_config(page_title="MARCUS ELITE V7.4", layout="wide")
toronto_tz = pytz.timezone('America/Toronto')

SUPABASE_URL = "https://xhxzhnzwvxmycdskjarr.supabase.co".strip()
SUPABASE_KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo".strip()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Supabase Connection Error: {e}")

# --- 2. ASSET LIBRARY ---
STOCK_LIBRARY = sorted([
    "NVDA", "TSLA", "AAPL", "BTC-USD", "ETH-USD", "GOOGL", "MSFT", "AMZN", "META", "NFLX", 
    "AMD", "INTC", "PYPL", "SQ", "SHOP", "PLTR", "SNOW", "COIN", "MARA", "RIOT",
    "DKNG", "HOOD", "SOFI", "U", "RBLX", "VNCE", "DNUT", "CGTX", "IH", "LUMN"
])

# --- 3. THE BRAINS: ADVANCED EMA MATH ---
def calculate_marcus_signals(df):
    if len(df) < 21: return "🟡 WAIT", df['close'].iloc[-1], 0
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['slope'] = df['EMA9'].diff()
    last_ema9, last_ema21 = df['EMA9'].iloc[-1], df['EMA21'].iloc[-1]
    last_slope = df['slope'].iloc[-1]
    
    # BUY SIGNAL: EMA 9 over EMA 21 + Positive Slope
    if (last_ema9 > last_ema21) and (last_slope > 0.05): 
        return "🔥 ULTRA BUY", df['close'].iloc[-1], abs(last_slope)
    # SELL SIGNAL: EMA 9 under EMA 21 or Negative Slope
    if (last_ema9 < last_ema21) or (last_slope < -0.02):
        return "🔴 ULTRA SELL", df['close'].iloc[-1], abs(last_slope)
        
    return "🟡 NEUTRAL", df['close'].iloc[-1], 0

# --- 4. THE SCANNER ENGINE ---
def scan_all_markets():
    best_ticker = None
    max_slope = 0
    sample = np.random.choice(STOCK_LIBRARY, 8, replace=False)
    for ticker in sample:
        temp_df = pd.DataFrame({'close': np.random.uniform(10, 500, 30)})
        sig, px, slope = calculate_marcus_signals(temp_df)
        if sig == "🔥 ULTRA BUY" and slope > max_slope:
            max_slope, best_ticker = slope, ticker
    return best_ticker, max_slope

# --- 5. CORE TRADING ACTIONS ---
def log_trade(ticker, side, price, qty):
    clean_qty = round(float(qty), 4) # Fractional Fix
    if clean_qty <= 0: return
    try:
        supabase.table("trades").insert({
            "username": st.session_state.username, "ticker": ticker, "side": side,
            "price": float(price), "quantity": clean_qty, "cost": float(price * clean_qty),
            "created_at": datetime.now(toronto_tz).isoformat(), "status": "OPEN"
        }).execute()
        st.toast(f"✅ {side}: {ticker}")
    except: pass

def close_position(trade_id, ticker, current_price, qty):
    try:
        val = current_price * qty
        supabase.table("trades").update({"status": "CLOSED"}).eq("id", trade_id).execute()
        st.session_state.balance += val
        st.toast(f"💰 PROFIT TAKEN: {ticker} (+${val:.2f})")
    except: pass

# --- 6. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'balance' not in st.session_state: st.session_state.balance = 113.0
if 'start_balance' not in st.session_state: st.session_state.start_balance = 113.0

# --- 7. MAIN UI & SIDEBAR ---
if not st.session_state.logged_in:
    st.title("🚀 Marcus Elite Terminal")
    u, p = st.text_input("User ID"), st.text_input("Password", type="password")
    if st.button("Access"):
        res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
        if res.data: st.session_state.logged_in, st.session_state.username = True, u; st.rerun()
else:
    now = datetime.now(toronto_tz)
    is_live = time(9, 30) <= now.time() <= time(16, 0) and now.weekday() < 5
    
    with st.sidebar:
        st.header(f"Op: {st.session_state.username}")
        scan_target, scan_slope = scan_all_markets()
        
        session_pl = st.session_state.balance - st.session_state.start_balance
        pl_col = "green" if session_pl >= 0 else "red"
        st.markdown(f"### Performance: :{pl_col}[${session_pl:,.2f}]")
        
        try:
            active_data = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
            open_count = len(active_data.data)
        except: open_count, active_data = 0, None
            
        st.metric("WALLET", f"${st.session_state.balance:,.2f}")
        st.metric("ACTIVE SLOTS", f"{open_count} / 4")
        
        autopilot_active = st.toggle("🤖 CLASSROOM AUTOPILOT", value=True)
        active_ticker = st.selectbox("View Feed:", STOCK_LIBRARY)
        if st.button("Logout"): st.session_state.logged_in = False; st.rerun()

    # --- 8. THE MASTER ENGINE ---
    @st.fragment(run_every=5)
    def engine(ticker_view):
        st.title(f"📊 {ticker_view} | {'LIVE' if is_live else 'SIM'}")
        
        # Real-time Chart Simulation
        df = pd.DataFrame({
            'date': pd.date_range(end=datetime.now(), periods=50, freq='min'),
            'open': np.random.uniform(100, 500, 50),
            'high': np.random.uniform(100, 505, 50),
            'low': np.random.uniform(95, 500, 50),
            'close': np.random.uniform(100, 500, 50)
        })
        sig, current_px, slope = calculate_marcus_signals(df)

        # 🔄 AUTOMATED SELL LOGIC (The "Exit" Brain)
        if autopilot_active and open_count > 0:
            for t in active_data.data:
                # If the stock we are holding hits a SELL signal, dump it!
                if t['ticker'] == ticker_view and sig == "🔴 ULTRA SELL":
                    close_position(t['id'], t['ticker'], current_px, t['quantity'])
                    st.rerun()

        # 📋 LIVE POSITION MONITOR
        if open_count > 0:
            st.subheader("📋 Live Position Monitor")
            monitor_list = []
            for t in active_data.data:
                live_val = current_px if t['ticker'] == ticker_view else t['price'] * np.random.uniform(0.99, 1.01)
                pnl = (live_val - t['price']) * t['quantity']
                monitor_list.append({"Ticker": t['ticker'], "Entry": f"${t['price']:.2f}", "Profit": f"${pnl:.2f}"})
            st.table(pd.DataFrame(monitor_list))

        # 🎯 GLOBAL BUY LOGIC
        if autopilot_active and is_live and open_count < 4:
            if scan_target and scan_slope > 0.05:
                # Verify we aren't already holding this ticker
                if not any(d['ticker'] == scan_target for d in active_data.data):
                    budget = st.session_state.balance * 0.25
                    log_trade(scan_target, "BUY", current_px, budget/current_px)
                    st.session_state.balance -= budget
                    st.rerun()

        # PLOTLY CHART
        fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

        # HUD
        c1, c2, c3 = st.columns(3)
        c1.metric("Price", f"${current_px:.2f}")
        c2.metric("Signal", sig)
        c3.metric("Slope", f"{slope:.4f}")

    engine(active_ticker)
