import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import pytz
from supabase import create_client, Client

# --- 1. CONFIG & SYSTEM KEYS ---
st.set_page_config(page_title="MARCUS ELITE V6.1", layout="wide")
toronto_tz = pytz.timezone('America/Toronto')

SUPABASE_URL = "https://xhxzhnzwvxmycdskjarr.supabase.co"
SUPABASE_KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. GLOBAL ASSET LIBRARY ---
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
ALL_ASSETS = list(set(RUNNERS + STOCK_LIBRARY))

# --- 3. MATH & DATABASE ---
def calculate_marcus_signals(df):
    if len(df) < 21: return "🟡 WAIT", df['close'].iloc[-1], 0
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['slope'] = df['EMA9'].diff()
    last_ema9, last_ema21, last_slope = df['EMA9'].iloc[-1], df['EMA21'].iloc[-1], df['slope'].iloc[-1]
    last_price = df['close'].iloc[-1]
    
    # Return signal, price, and "conviction score" (abs slope)
    if (last_ema9 > last_ema21) and (last_slope > 0.05): return "🔥 ULTRA BUY", last_price, abs(last_slope)
    if (last_ema9 < last_ema21) and (last_slope < -0.05): return "🔴 ULTRA SELL", last_price, abs(last_slope)
    return "🟡 NEUTRAL", last_price, 0

def log_trade(ticker, side, price):
    try:
        supabase.table("trades").insert({
            "username": st.session_state.username,
            "ticker": ticker,
            "side": side,
            "price": float(price),
            "balance": float(st.session_state.balance),
            "created_at": datetime.now(toronto_tz).isoformat()
        }).execute()
        st.session_state.open_positions += 1
        st.toast(f"🚀 AUTO-TRADE: {side} {ticker}")
    except: pass

# --- 4. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'balance' not in st.session_state: st.session_state.balance = 100000.0
if 'auto_pilot' not in st.session_state: st.session_state.auto_pilot = False
if 'open_positions' not in st.session_state: st.session_state.open_positions = 0

# --- 5. AUTHENTICATION ---
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
                st.success("Account Created!")
            except: st.error("Error creating account.")

else:
    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.header(f"Elite: {st.session_state.username}")
        
        # P/L Logic
        try:
            trade_res = supabase.table("trades").select("*").eq("username", st.session_state.username).execute()
            total_pl = sum([(np.random.uniform(0.98, 1.05) - 1) * t['price'] for t in trade_res.data])
            color = "inverse" if total_pl >= 0 else "normal"
            st.metric("TOTAL P/L", f"${total_pl:,.2f}", delta=f"{total_pl:,.2f}", delta_color=color)
        except: st.metric("TOTAL P/L", "$0.00")

        st.metric("WALLET", f"${st.session_state.balance:,.2f}")
        st.metric("OPEN SLOTS", f"{st.session_state.open_positions} / 4")
        
        if st.button("🔄 RESET ALL"): 
            st.session_state.balance = 100000.0
            st.session_state.open_positions = 0
            st.rerun()
        
        st.markdown("---")
        st.session_state.auto_pilot = st.toggle("🤖 ACTIVATE GLOBAL AI SCANNER")
        sel_runner = st.radio("Momentum View:", RUNNERS)
        sel_lib = st.selectbox("Library Search:", ["None"] + STOCK_LIBRARY)
        active_ticker = sel_lib if sel_lib != "None" else sel_runner
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # --- 7. THE GLOBAL SCANNER ENGINE ---
    @st.fragment(run_every=5)
    def global_execution_engine(ticker_view):
        now_toronto = datetime.now(toronto_tz)
        
        c1, c2 = st.columns([3, 1])
        c1.title(f"📊 {ticker_view} Terminal")
        c2.metric("TORONTO (EDT)", now_toronto.strftime("%I:%M:%S %p"))

        df_ui = pd.DataFrame({
            'Date': pd.date_range(end=now_toronto, periods=50, freq='min'),
            'open': np.random.uniform(150, 160, 50), 'high': np.random.uniform(160, 165, 50),
            'low': np.random.uniform(145, 150, 50), 'close': np.random.uniform(150, 160, 50)
        })
        
        # 🤖 SELECTIVE SCANNER
        if st.session_state.auto_pilot and st.session_state.open_positions < 4:
            potential_trades = []
            for asset in ALL_ASSETS:
                sim_close = np.random.uniform(100, 500, 25)
                df_scan = pd.DataFrame({'close': sim_close})
                sig, px, conviction = calculate_marcus_signals(df_scan)
                if "ULTRA" in sig:
                    potential_trades.append({'ticker': asset, 'sig': sig, 'px': px, 'score': conviction})
            
            # Sort by highest conviction score and take top available slots
            top_trades = sorted(potential_trades, key=lambda x: x['score'], reverse=True)
            for t in top_trades[:(4 - st.session_state.open_positions)]:
                log_trade(t['ticker'], t['sig'], t['px'])

        fig = go.Figure(data=[go.Candlestick(x=df_ui['Date'], open=df_ui['open'], high=df_ui['high'], low=df_ui['low'], close=df_ui['close'])])
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        h1, h2, h3 = st.columns(3)
        ui_sig, ui_px, _ = calculate_marcus_signals(df_ui)
        h1.metric("Live Price", f"${ui_px:,.2f}")
        h2.metric("AI Signal", ui_sig)
        if h3.button(f"📝 MANUAL LOG: {ticker_view}"):
            log_trade(ticker_view, "MANUAL", ui_px)

    global_execution_engine(active_ticker)
