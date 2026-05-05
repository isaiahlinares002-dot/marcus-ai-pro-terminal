import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time
import pytz
from supabase import create_client, Client

# --- 1. SYSTEM CONFIG & TIMEZONE ---
st.set_page_config(page_title="MARCUS ELITE V7.1", layout="wide")
toronto_tz = pytz.timezone('America/Toronto')

SUPABASE_URL = "https://xhxzhnzwvxmycdskjarr.supabase.co"
SUPABASE_KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. ASSET LIBRARY (Big Tech & Penny Stocks) ---
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

# --- 3. THE BRAINS: ADVANCED EMA SLOPE MATH ---
def calculate_marcus_signals(df, price_range):
    last_price = np.random.uniform(price_range[0], price_range[1])
    if len(df) < 21: return "🟡 WAIT", last_price, 0
    
    # Advanced 9/21 EMA Strategy
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['slope'] = df['EMA9'].diff()
    
    last_ema9 = df['EMA9'].iloc[-1]
    last_ema21 = df['EMA21'].iloc[-1]
    last_slope = df['slope'].iloc[-1]
    
    if (last_ema9 > last_ema21) and (last_slope > 0.05):
        return "🔥 ULTRA BUY", last_price, abs(last_slope)
    if (last_ema9 < last_ema21) and (last_slope < -0.05):
        return "🔴 ULTRA SELL", last_price, abs(last_slope)
    return "🟡 NEUTRAL", last_price, 0

# --- 4. THE AUTO-EXIT & QUANTITY LOGIC ---
def close_all_active_positions():
    try:
        res = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
        if res.data:
            recouped = 0
            for t in res.data:
                # 0.2% variance for slippage during panic exit
                val = t['price'] * t['quantity'] * np.random.uniform(0.998, 1.002)
                recouped += val
                supabase.table("trades").update({"status": "CLOSED"}).eq("id", t['id']).execute()
            st.session_state.balance += recouped
            st.toast(f"🚨 EMERGENCY EXIT: Recouped ${recouped:.2f}")
    except: pass

def log_trade(ticker, side, price, qty):
    clean_qty = round(float(qty), 4) # FIX: No more 0.000 units
    if clean_qty <= 0: return
    try:
        supabase.table("trades").insert({
            "username": st.session_state.username, "ticker": ticker, "side": side,
            "price": float(price), "quantity": clean_qty, "cost": float(price * clean_qty),
            "created_at": datetime.now(toronto_tz).isoformat(), "status": "OPEN"
        }).execute()
        st.toast(f"✅ AUTO-LOG: {ticker} ({side})")
    except: pass

# --- 5. SYSTEM STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'balance' not in st.session_state: st.session_state.balance = 113.0
if 'start_balance' not in st.session_state: st.session_state.start_balance = 113.0

# --- 6. AUTHENTICATION TABS ---
if not st.session_state.logged_in:
    st.title("🚀 Marcus Elite Terminal")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    with t1:
        u, p = st.text_input("User ID"), st.text_input("Password", type="password")
        if st.button("Access Hub"):
            res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data: st.session_state.logged_in, st.session_state.username = True, u; st.rerun()
    with t2:
        nu, npw = st.text_input("New ID"), st.text_input("New Pass", type="password")
        if st.button("Create Elite Account"): 
            supabase.table("users").insert({"username": nu, "password": npw}).execute(); st.success("Created!")

else:
    # --- 7. SIDEBAR HUD & "CLUTTER" UI ---
    now = datetime.now(toronto_tz)
    is_live = time(9, 30) <= now.time() <= time(16, 0) and now.weekday() < 5
    
    with st.sidebar:
        st.header(f"Operator: {st.session_state.username}")
        st.markdown(f"**System Time:** {now.strftime('%I:%M:%S %p')}")
        
        # P/L Visual Tracker
        session_pl = st.session_state.balance - st.session_state.start_balance
        pl_color = "green" if session_pl >= 0 else "red"
        st.markdown(f"### Performance: :{pl_color}[${session_pl:,.2f}]")
        
        st.markdown("---")
        st.session_state.balance = st.number_input("Vault Balance ($)", value=float(st.session_state.balance))
        st.session_state.risk_per_trade = st.slider("Risk Per Slot (%)", 5, 100, 25)
        
        # Slot Status
        try:
            active_data = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
            open_count = len(active_data.data)
        except: open_count = 0
            
        st.metric("WALLET", f"${st.session_state.balance:,.2f}", f"{session_pl:,.2f}")
        st.metric("ACTIVE SLOTS", f"{open_count} / 4")
        
        # UI Control: The Switch
        autopilot_active = st.toggle("🤖 CLASSROOM AUTOPILOT", value=True)
        if not autopilot_active and open_count > 0:
            close_all_active_positions()
            st.rerun()

        st.markdown("---")
        active_ticker = st.selectbox("Market Feed:", ALL_ASSETS)
        if st.button("Secure Logout"): st.session_state.logged_in = False; st.rerun()

    # --- 8. THE PRO ENGINE & CANDLESTICK UI ---
    @st.fragment(run_every=5)
    def engine(ticker_view):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.title(f"📊 {ticker_view} | {'LIVE FEED' if is_live else 'SIMULATION'}")
        with c2:
            st.metric("MARKET STATUS", "OPEN" if is_live else "CLOSED")

        # Pro Chart Data Scaling
        p_range = (1, 15) if ticker_view in ["DNUT", "VNCE", "CGTX", "IH", "LUMN"] else (100, 500)
        df = pd.DataFrame({
            'date': pd.date_range(end=datetime.now(), periods=50, freq='min'),
            'open': np.random.uniform(p_range[0], p_range[1], 50),
            'high': np.random.uniform(p_range[0]+2, p_range[1]+5, 50),
            'low': np.random.uniform(p_range[0]-5, p_range[1]-2, 50),
            'close': np.random.uniform(p_range[0], p_range[1], 50)
        })
        
        # AUTO-TRADING MATH
        if autopilot_active and is_live:
            db_check = len(supabase.table("trades").select("id").eq("username", st.session_state.username).eq("status", "OPEN").execute().data)
            if db_check < 4:
                budget = st.session_state.balance * (st.session_state.risk_per_trade / 100)
                sig, px, score = calculate_marcus_signals(df, p_range)
                if "ULTRA" in sig:
                    log_trade(ticker_view, "BUY", px, budget/px)
                    st.session_state.balance -= budget

        # PROFESSIONAL CANDLESTICK VISUALS
        fig = go.Figure(data=[go.Candlestick(
            x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#00ff00', decreasing_line_color='#ff0000'
        )])
        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # ENGINE HUD
        st.markdown("---")
        h1, h2, h3, h4 = st.columns(4)
        sig_val, px_val, slope_val = calculate_marcus_signals(df, p_range)
        h1.metric("Current Price", f"${px_val:,.2f}")
        h2.metric("AI Signal", sig_val)
        h3.metric("EMA Slope", f"{slope_val:.4f}")
        if h4.button(f"FORCE LOG: {ticker_view}"):
            log_trade(ticker_view, "MANUAL", px_val, (st.session_state.balance * 0.25)/px_val)

    engine(active_ticker)
