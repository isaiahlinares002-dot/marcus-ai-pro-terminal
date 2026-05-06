import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time
import pytz
from supabase import create_client, Client

# --- 1. SYSTEM CONFIG & FIXED CONNECTION ---
st.set_page_config(page_title="MARCUS ELITE V7.2", layout="wide")
toronto_tz = pytz.timezone('America/Toronto')

# Credentials with .strip() to prevent "Invalid URL" errors
SUPABASE_URL = "https://xhxzhnzwvxmycdskjarr.supabase.co".strip()
SUPABASE_KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo".strip()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Supabase Connection Error: {e}")

# --- 2. ASSET LIBRARY ---
RUNNERS = ["NVDA", "TSLA", "AAPL", "BTC-USD", "ETH-USD"]
STOCK_LIBRARY = sorted([
    "GOOGL", "MSFT", "AMZN", "META", "NFLX", "AMD", "INTC", "PYPL", "SQ", "SHOP",
    "CRWD", "PLTR", "SNOW", "TSM", "ASML", "SBUX", "DIS", "BA", "CAT", "GE",
    "JPM", "GS", "V", "MA", "UBER", "LYFT", "ABNB", "COIN", "MARA", "RIOT",
    "PFE", "MRNA", "UNH", "XOM", "CVX", "COST", "WMT", "TGT", "NKE", "F",
    "GM", "RIVN", "LCID", "BABA", "JD", "PDD", "BIDU", "NTES", "LI", "XPEV",
    "DKNG", "PENN", "PLUG", "FCEL", "SPCE", "AMC", "GME", "HOOD", "SOFI", "U",
    "NET", "OKTA", "DDOG", "ZS", "CRSR", "LOGI", "RBLX", "SE", "MELI",
    "VNCE", "DNUT", "CGTX", "IH", "LUMN"
])
ALL_ASSETS = list(set(RUNNERS + STOCK_LIBRARY))

# --- 3. THE BRAINS: ADVANCED EMA MATH ---
def calculate_marcus_signals(df, price_range):
    last_price = np.random.uniform(price_range[0], price_range[1])
    if len(df) < 21: return "🟡 WAIT", last_price, 0
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['slope'] = df['EMA9'].diff()
    last_ema9, last_ema21 = df['EMA9'].iloc[-1], df['EMA21'].iloc[-1]
    last_slope = df['slope'].iloc[-1]
    if (last_ema9 > last_ema21) and (last_slope > 0.05): return "🔥 ULTRA BUY", last_price, abs(last_slope)
    if (last_ema9 < last_ema21) and (last_slope < -0.05): return "🔴 ULTRA SELL", last_price, abs(last_slope)
    return "🟡 NEUTRAL", last_price, 0

# --- 4. EXIT LOGIC & QUANTITY FIXES ---
def close_all_active_positions():
    try:
        res = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
        if res.data:
            recouped = 0
            for t in res.data:
                # Calculate value based on current simulated price drift
                val = t['price'] * t['quantity'] * np.random.uniform(0.998, 1.002)
                recouped += val
                supabase.table("trades").update({"status": "CLOSED"}).eq("id", t['id']).execute()
            st.session_state.balance += recouped
            st.toast(f"🚨 EMERGENCY EXIT: Recouped ${recouped:.2f}")
    except: pass

def log_trade(ticker, side, price, qty):
    clean_qty = round(float(qty), 4) # Fixes 0.000 bug
    if clean_qty <= 0: return
    try:
        supabase.table("trades").insert({
            "username": st.session_state.username, "ticker": ticker, "side": side,
            "price": float(price), "quantity": clean_qty, "cost": float(price * clean_qty),
            "created_at": datetime.now(toronto_tz).isoformat(), "status": "OPEN"
        }).execute()
        st.toast(f"✅ ENTRY: {ticker}")
    except: pass

# --- 5. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'balance' not in st.session_state: st.session_state.balance = 113.0
if 'start_balance' not in st.session_state: st.session_state.start_balance = 113.0

# --- 6. AUTHENTICATION ---
if not st.session_state.logged_in:
    st.title("🚀 Marcus Elite Terminal")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    with t1:
        u, p = st.text_input("User ID"), st.text_input("Password", type="password")
        if st.button("Access"):
            res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data: st.session_state.logged_in, st.session_state.username = True, u; st.rerun()
    with t2:
        nu, npw = st.text_input("New ID"), st.text_input("New Pass", type="password")
        if st.button("Create Account"): 
            supabase.table("users").insert({"username": nu, "password": npw}).execute(); st.success("Done!")

else:
    # --- 7. SIDEBAR HUD ---
    now = datetime.now(toronto_tz)
    # Market Hours: 9:30 AM - 4:00 PM EST
    is_live = time(9, 30) <= now.time() <= time(16, 0) and now.weekday() < 5
    
    with st.sidebar:
        st.header(f"Operator: {st.session_state.username}")
        session_pl = st.session_state.balance - st.session_state.start_balance
        pl_color = "green" if session_pl >= 0 else "red"
        st.markdown(f"### Performance: :{pl_color}[${session_pl:,.2f}]")
        
        st.session_state.balance = st.number_input("Vault ($)", value=float(st.session_state.balance))
        st.session_state.risk_per_trade = st.slider("Risk (%)", 5, 100, 25)
        
        try:
            # Hard check on database for 6/4 slot bug fix
            active_data = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
            open_count = len(active_data.data)
        except: 
            open_count, active_data = 0, None
            
        st.metric("CASH ON HAND", f"${st.session_state.balance:,.2f}")
        st.metric("ACTIVE SLOTS", f"{open_count} / 4")
        
        autopilot_active = st.toggle("🤖 CLASSROOM AUTOPILOT", value=True)
        if not autopilot_active and open_count > 0:
            close_all_active_positions()
            st.rerun()

        st.markdown("---")
        active_ticker = st.selectbox("Market Feed:", ALL_ASSETS)
        if st.button("Logout"): 
            st.session_state.logged_in = False
            st.rerun()

    # --- 8. THE MASTER ENGINE + LIVE MONITOR ---
    @st.fragment(run_every=5)
    def engine(ticker_view):
        c1, c2 = st.columns([3, 1])
        with c1: st.title(f"📊 {ticker_view} | {'LIVE' if is_live else 'SIMULATION'}")
        with c2: st.metric("STATUS", "OPEN" if is_live else "CLOSED")

        # Dynamic Price Scaling
        p_range = (1, 15) if ticker_view in ["DNUT", "VNCE", "CGTX", "IH", "LUMN"] else (100, 500)
        df = pd.DataFrame({
            'date': pd.date_range(end=datetime.now(), periods=50, freq='min'),
            'open': np.random.uniform(p_range[0], p_range[1], 50),
            'high': np.random.uniform(p_range[0]+2, p_range[1]+5, 50),
            'low': np.random.uniform(p_range[0]-5, p_range[1]-2, 50),
            'close': np.random.uniform(p_range[0], p_range[1], 50)
        })
        sig, current_px, slope = calculate_marcus_signals(df, p_range)

        # NEW ABILITY: LIVE POSITION MONITOR
        st.subheader("📋 Live Position Monitor")
        if open_count > 0:
            monitor_list = []
            unrealized_total = 0
            for t in active_data.data:
                # Match current price if ticker is active, else simulate minor drift
                live_val = current_px if t['ticker'] == ticker_view else t['price'] * np.random.uniform(0.99, 1.01)
                pnl = (live_val - t['price']) * t['quantity']
                unrealized_total += pnl
                monitor_list.append({
                    "Ticker": t['ticker'], 
                    "Entry": f"${t['price']:.2f}", 
                    "Current": f"${live_val:.2f}", 
                    "Profit": f"${pnl:.2f}"
                })
            st.table(pd.DataFrame(monitor_list))
            u_color = "green" if unrealized_total > 0 else "red"
            st.markdown(f"#### Total Unrealized Profit: :{u_color}[${unrealized_total:.2f}]")
        else:
            st.info("Scanning markets for entry signals...")

        # AUTOMATED TRADING LOGIC
        if autopilot_active and is_live and open_count < 4:
            if "ULTRA" in sig:
                budget = st.session_state.balance * (st.session_state.risk_per_trade / 100)
                log_trade(ticker_view, "BUY", current_px, budget/current_px)
                st.session_state.balance -= budget

        # PROFESSIONAL PLOTLY CANDLESTICK CHART
        fig = go.Figure(data=[go.Candlestick(
            x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close']
        )])
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Current Price", f"${current_px:,.2f}")
        h2.metric("AI Signal", sig)
        h3.metric("EMA Slope", f"{slope:.4f}")
        if h4.button(f"FORCE LOG: {ticker_view}"):
            log_trade(ticker_view, "MANUAL", current_px, (st.session_state.balance * 0.25)/current_px)

    engine(active_ticker)
