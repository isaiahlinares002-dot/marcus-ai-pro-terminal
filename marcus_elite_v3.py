import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time
import pytz
from supabase import create_client, Client

# --- 1. CONFIG & SYSTEM KEYS ---
st.set_page_config(page_title="MARCUS ELITE V6.7", layout="wide")
toronto_tz = pytz.timezone('America/Toronto')

# Database Credentials
SUPABASE_URL = "https://xhxzhnzwvxmycdskjarr.supabase.co"
SUPABASE_KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. ASSET LIBRARY (Big Tech + Small-Caps Under $100) ---
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

# --- 3. MARKET STATUS LOGIC (Toronto/NY Time) ---
def check_market_status():
    now = datetime.now(toronto_tz)
    # 2026 Holidays (Closed)
    holidays_2026 = ["2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25"]
    current_date = now.strftime("%Y-%m-%d")
    is_weekend = now.weekday() >= 5 
    is_holiday = current_date in holidays_2026
    
    market_open = time(9, 30)
    market_close = time(16, 0)
    current_time = now.time()
    
    is_within_hours = market_open <= current_time <= market_close
    
    if is_weekend or is_holiday:
        return "🔴 CLOSED (Weekend/Holiday)", False
    elif not is_within_hours:
        return "🌙 CLOSED (After Hours)", False
    else:
        return "🟢 LIVE MARKET OPEN", True

# --- 4. THE ULTRA MATH ENGINE ---
def calculate_marcus_signals(df, price_range=(100, 500)):
    # Simulates realistic last price based on the stock's typical range
    last_price = np.random.uniform(price_range[0], price_range[1])
    if len(df) < 21: return "🟡 WAIT", last_price, 0
    
    # EMA 9/21 Crossover Logic
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

def log_trade(ticker, side, price, qty):
    try:
        supabase.table("trades").insert({
            "username": st.session_state.username,
            "ticker": ticker,
            "side": side,
            "price": float(price),
            "quantity": float(qty),
            "cost": float(price * qty),
            "created_at": datetime.now(toronto_tz).isoformat(),
            "status": "OPEN"
        }).execute()
        st.toast(f"✅ AUTO-ENTRY: {ticker} ({qty:.3f} units)")
    except:
        st.error("Trade Log Error")

# --- 5. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'balance' not in st.session_state: st.session_state.balance = 100.0
if 'risk_per_trade' not in st.session_state: st.session_state.risk_per_trade = 25
if 'auto_pilot' not in st.session_state: st.session_state.auto_pilot = False

# --- 6. AUTHENTICATION (Full Tabs) ---
if not st.session_state.logged_in:
    st.title("🚀 Marcus Elite Terminal")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        u = st.text_input("User ID")
        p = st.text_input("Password", type="password")
        if st.button("Access Terminal"):
            res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
            if res.data:
                st.session_state.logged_in, st.session_state.username = True, u
                st.rerun()
            else: st.error("Invalid Credentials")
    with tab2:
        new_u = st.text_input("Create User ID")
        new_p = st.text_input("Create Password", type="password")
        if st.button("Register Elite Account"):
            try:
                supabase.table("users").insert({"username": new_u, "password": new_p}).execute()
                st.success("Account Created! Use the Login tab.")
            except: st.error("Username taken.")
else:
    # --- 7. SIDEBAR (Full UI & Risk HUD) ---
    market_label, is_live = check_market_status()
    with st.sidebar:
        st.header(f"Elite: {st.session_state.username}")
        st.subheader(f"Status: {market_label}")
        
        # Risk Management for Small Accounts
        st.session_state.balance = st.number_input("Wallet ($)", value=float(st.session_state.balance))
        st.session_state.risk_per_trade = st.slider("Risk Per Trade (%)", 5, 100, 25)
        
        # P/L & Slot Management
        try:
            trade_res = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
            open_count = len(trade_res.data)
            
            # Simulated Exit Strategy
            for t in trade_res.data:
                change = np.random.uniform(-0.01, 0.02)
                if change >= 0.01 or change <= -0.005:
                    supabase.table("trades").update({"status": "CLOSED"}).eq("id", t['id']).execute()
                    st.session_state.balance += (t['price'] * t['quantity'] * (1 + change))
        except:
            open_count = 0

        st.metric("WALLET", f"${st.session_state.balance:,.2f}")
        st.metric("ACTIVE SLOTS", f"{open_count} / 4")
        st.session_state.auto_pilot = st.toggle("🤖 CLASSROOM AUTOPILOT", value=st.session_state.auto_pilot)
        
        # Navigation
        sel_runner = st.radio("Momentum:", RUNNERS)
        sel_lib = st.selectbox("Library Search:", ["None"] + STOCK_LIBRARY)
        active_ticker = sel_lib if sel_lib != "None" else sel_runner
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # --- 8. THE ENGINE ---
    @st.fragment(run_every=5)
    def engine(ticker_view):
        now = datetime.now(toronto_tz)
        st.title(f"📊 {ticker_view} | {'LIVE' if is_live else 'SIMULATION'}")
        
        # Chart Scaling for Penny vs Big Stocks
        p_range = (1, 10) if ticker_view in ["DNUT", "VNCE", "CGTX", "IH", "LUMN"] else (100, 500)
        df_ui = pd.DataFrame({
            'Date': pd.date_range(end=now, periods=50, freq='min'),
            'open': np.random.uniform(p_range[0], p_range[1], 50),
            'high': np.random.uniform(p_range[0], p_range[1]+5, 50),
            'low': np.random.uniform(p_range[0]-5, p_range[1], 50),
            'close': np.random.uniform(p_range[0], p_range[1], 50)
        })
        
        # AUTO-TRADING ENGINE
        if st.session_state.auto_pilot:
            if is_live and open_count < 4:
                budget = st.session_state.balance * (st.session_state.risk_per_trade / 100)
                potential = []
                for asset in ALL_ASSETS:
                    asset_range = (1, 15) if asset in ["DNUT", "VNCE", "CGTX", "IH", "LUMN"] else (100, 1000)
                    sig, px, score = calculate_marcus_signals(pd.DataFrame({'close': np.random.uniform(asset_range[0], asset_range[1], 25)}), asset_range)
                    if "ULTRA" in sig:
                        potential.append({'ticker': asset, 'sig': sig, 'px': px, 'score': score, 'qty': budget / px})
                
                # Execute Top High-Conviction Trades
                top = sorted(potential, key=lambda x: x['score'], reverse=True)
                for t in top[:(4 - open_count)]:
                    log_trade(t['ticker'], t['sig'], t['px'], t['qty'])
                    st.session_state.balance -= (t['px'] * t['qty'])
            elif not is_live:
                st.warning(f"Standby Mode: Market is {market_label}. Active hunt begins Monday 9:30 AM.")

        # Main Visualization
        fig = go.Figure(data=[go.Candlestick(x=df_ui['Date'], open=df_ui['open'], high=df_ui['high'], low=df_ui['low'], close=df_ui['close'])])
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        h1, h2, h3 = st.columns(3)
        ui_sig, ui_px, _ = calculate_marcus_signals(df_ui, p_range)
        h1.metric("Live Price", f"${ui_px:,.2f}")
        h2.metric("AI Signal", ui_sig)
        if h3.button(f"📝 MANUAL LOG: {ticker_view}"):
            qty = (st.session_state.balance * (st.session_state.risk_per_trade / 100)) / ui_px
            log_trade(ticker_view, "MANUAL", ui_px, qty)

    engine(active_ticker)
