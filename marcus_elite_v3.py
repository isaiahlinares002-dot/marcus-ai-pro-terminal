import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, time
import pytz
from supabase import create_client
from alpaca_trade_api.rest import REST

# --- 1. INITIAL SETUP & APP CONFIG ---
st.set_page_config(page_title="Marcus Elite Master Terminal v7", layout="wide")
toronto_tz = pytz.timezone("America/Toronto")

# SUPABASE CONNECTION (Cloud Ledger Database)
URL = "https://xhxzhnzwvxmycdskjarr.supabase.co"
KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo"
supabase = create_client(URL, KEY)

# 🔐 LIVE USER CHIP CERTIFICATES REGISTERED
PAPER_API_KEY = "PKKJYWAN6ZEDTBPTWHQRV26Q4Y"
PAPER_SECRET_KEY = "GnsyXG84eJ4C5YEbjdFSdZYC2pyiDb6ZNGDLGnHcYvo9"

LIVE_API_KEY = "YOUR_LIVE_KEY_HERE"
LIVE_SECRET_KEY = "YOUR_LIVE_SECRET_HERE"

# --- ACTIVE LIBRARY TRACKER ---
STOCK_LIBRARY = [
    "ETH-USD", "BTC-USD", "SOL-USD", "AAPL", "TSLA", "NVDA", "PLTR", "COIN", "VNCE", "AMD",
    "MSFT", "GOOGL", "META", "AMZN", "NFLX", "INTC", "PYPL", "SQ", "SHOP", "RIVN"
]

# --- 2. BROKERAGE CONNECTION MANAGER ---
def get_alpaca_client(mode):
    if mode == "🚀 LIVE TRADING":
        base_url = "https://api.alpaca.markets"
        return REST(LIVE_API_KEY, LIVE_SECRET_KEY, base_url, api_version='v2')
    else:
        base_url = "https://paper-api.alpaca.markets"
        return REST(PAPER_API_KEY, PAPER_SECRET_KEY, base_url, api_version='v2')

# --- 3. HIGH-FREQUENCY INTRA-DAY SIGNAL ENGINE ---
def get_signals(df):
    """Calculates ultra-fast 3/8 EMA parameters to catch intra-day micro-swings"""
    if len(df) < 15:
        return "⚪ SCANNING", df['close'].iloc[-1] if not df.empty else 100.0, 0.0
        
    df['ema_fast'] = df['close'].ewm(span=3, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=8, adjust=False).mean()
    
    last_px = df['close'].iloc[-1]
    prev_fast, last_fast = df['ema_fast'].iloc[-2], df['ema_fast'].iloc[-1]
    prev_slow, last_slow = df['ema_slow'].iloc[-2], df['ema_slow'].iloc[-1]
    
    slope = (last_fast - prev_fast) / prev_fast
    
    # Fast-reaction crossover logic
    if prev_fast <= prev_slow and last_fast > last_slow:
        return "🟢 ULTRA BUY", last_px, slope
    elif prev_fast >= prev_slow and last_fast < last_slow:
        return "🔴 ULTRA SELL", last_px, slope
        
    # Micro-trend retention scanning
    if last_fast > last_slow and slope > 0.0005:
        return "🟢 ULTRA BUY", last_px, slope
        
    return "⚪ SCANNING", last_px, slope

# --- 4. REAL-TIME DATA INGESTION ENGINE ---
def fetch_real_data(api, ticker):
    """Streams live candlestick chunks directly out of Alpaca core data servers"""
    try:
        alpaca_ticker = ticker.replace("-", "/") if "USD" in ticker else ticker
        
        # ⏱️ Roll back the end timestamp 15 minutes to clear Alpaca's free data subscription constraints
        end_dt = datetime.now(toronto_tz) - timedelta(minutes=15)
        start_dt = end_dt - timedelta(hours=3) # Grabbing a wider historical block for stable calculations
        
        bars = api.get_bars(
            alpaca_ticker, 
            '1Min', 
            start=start_dt.isoformat(), 
            end=end_dt.isoformat(), 
            adjustment='raw'
        ).df
        
        if bars.empty:
            return pd.DataFrame({'close': [100.0]*30, 'open':[100.0]*30, 'high':[100.0]*30, 'low':[100.0]*30, 'date': pd.date_range(end=datetime.now(), periods=30, freq='min')})
            
        bars = bars.reset_index()
        bars = bars.rename(columns={'timestamp': 'date'})
        return bars[['date', 'open', 'high', 'low', 'close']]
    except Exception:
        return pd.DataFrame({'close': [100.0]*30, 'open':[100.0]*30, 'high':[100.0]*30, 'low':[100.0]*30, 'date': pd.date_range(end=datetime.now(), periods=30, freq='min')})

# --- 5. AUTOMATED EXECUTION HANDSHAKES ---
def execute_smart_buy(ticker, price):
    try:
        risk_mod = 1.0 if st.session_state.balance >= 100 else 0.5
        risk_amount = st.session_state.balance * (st.session_state.risk_percent / 100) * risk_mod
        
        qty = int(risk_amount / price) if price > 0 else 0
        if qty <= 0: return

        trade_data = {
            "username": st.session_state.username,
            "ticker": ticker,
            "price": float(price),
            "quantity": qty,
            "status": "OPEN",
            "date": datetime.now(toronto_tz).strftime("%Y-%m-%d"),
            "time": datetime.now(toronto_tz).strftime("%H:%M:%S")
        }
        
        supabase.table("trades").insert(trade_data).execute()
        st.toast(f"🚀 LEDGER INTERACT: Position Logged for {ticker} @ ${price:.2f}")
    except Exception as e:
        st.error(f"Ledger Sync Broken: {e}")

def emergency_sell_all(api):
    try:
        active = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
        for t in active.data:
            try:
                alpaca_ticker = t['ticker'].replace("-", "/") if "USD" in t['ticker'] else t['ticker']
                api.submit_order(symbol=alpaca_ticker, qty=t['quantity'], side='sell', type='market', time_in_force='gtc')
            except: pass
            
            supabase.table("trades").update({
                "status": "CLOSED",
                "exit_price": t['price'],
                "exit_time": datetime.now(toronto_tz).strftime("%H:%M:%S")
            }).eq("id", t['id']).execute()
        st.toast("🚨 CORE EMERGENCY CLEAR UNWOUND ALL BLOCKS.")
        st.rerun()
    except Exception as e:
        st.error(f"Liquidation Error: {e}")

# --- 6. AUTHENTICATION GATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'balance' not in st.session_state: st.session_state.balance = 100000.0

if not st.session_state.logged_in:
    st.title("🚀 Marcus Elite Terminal")
    auth_mode = st.radio("Choose Action", ["Sign In", "Sign Up/Register"], horizontal=True)
    
    if auth_mode == "Sign In":
        st.subheader("Login to your Operator Terminal")
        u = st.text_input("User ID", key="login_user")
        p = st.text_input("Pass", type="password", key="login_pass")
        if st.button("Enter"):
            try:
                res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
                if res.data: 
                    st.session_state.logged_in, st.session_state.username = True, u
                    st.rerun()
                else: st.error("Invalid Operator ID or Password.")
            except Exception as e: st.error(f"Authentication Database Disconnected: {e}")
                
    elif auth_mode == "Sign Up/Register":
        st.subheader("Register New Profile")
        new_u = st.text_input("Choose User ID", key="reg_user")
        new_p = st.text_input("Choose Password", type="password", key="reg_pass")
        confirm_p = st.text_input("Confirm Password", type="password", key="reg_confirm")
        if st.button("Register Account"):
            if new_p == confirm_p and new_u and new_p:
                try:
                    supabase.table("users").insert({"username": new_u, "password": new_p}).execute()
                    st.success("🎉 Registration Confirmed! Flip back to Sign In.")
                except Exception as e: st.error(f"Sync Interrupted: {e}")
else:
    # --- 7. ACTIVE DASHBOARD SYSTEM ---
    now = datetime.now(toronto_tz)
    is_market_open = time(9,30) <= now.time() <= time(16,0) and now.weekday() < 5
    
    try:
        history = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "CLOSED").execute()
        total_closed = len(history.data)
        wins = len([x for x in history.data if x.get('exit_price', 0) > x['price']])
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
    except: total_closed, win_rate, history = 0, 0.0, None

    with st.sidebar:
        st.header(f"Operator: {st.session_state.username}")
        trade_mode = st.radio("💰 TERMINAL ENVIRONMENT", ["🛠️ PAPER TRADING", "🚀 LIVE TRADING"], horizontal=False)
        alpaca_api = get_alpaca_client(trade_mode)
        
        try:
            account = alpaca_api.get_account()
            st.session_state.balance = float(account.cash)
            st.metric("BROKERAGE CASH", f"${st.session_state.balance:.2f}")
        except Exception as api_err:
            st.metric("MOCK CASH (API Locked)", f"${st.session_state.balance:.2f}")

        st.markdown("---")
        st.write(f"🏆 **Mathematical Win Rate:** {win_rate:.1f}%")
        st.caption(f"Historical Settlements: {total_closed}")
        st.markdown("---")

        st.session_state.risk_percent = st.slider("Trade Power %", 5, 100, 100)
        st.session_state.target_profit = st.slider("Take Profit %", 0.5, 5.0, 1.5)
        auto_on = st.toggle("🤖 AUTOPILOT SCANNING", value=True)
        
        if st.button("🚨 EMERGENCY portfolio UNWIND", use_container_width=True):
            emergency_sell_all(alpaca_api)
            st.rerun()
        if st.button("TERMINAL LOGOUT"): 
            st.session_state.logged_in = False
            st.rerun()

    selected_ticker = st.selectbox("Focus Asset Tracker", STOCK_LIBRARY, key="focus_asset_selector")

    @st.fragment(run_every=5)
    def live_engine(ticker):
        try:
            active_res = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
            slots = len(active_res.data)
        except: slots, active_res = 0, None

        df = fetch_real_data(alpaca_api, ticker)
        sig, px, slp = get_signals(df)

        st.markdown(f"### 📡 Monitoring Interface: {ticker} (Buffered Price: ${px:.2f})")
        st.write(f"**Signal State:** `{sig}` | **Active Positions:** {slots} / 4")
        
        # --- POSITION LEDGER GRID ---
        if slots > 0:
            total_unrealized = 0
            rows = []
            for t in active_res.data:
                if t['ticker'] == ticker:
                    cur = float(round(px, 2))
                else:
                    bg_df = fetch_real_data(alpaca_api, t['ticker'])
                    cur = float(round(bg_df['close'].iloc[-1], 2)) if not bg_df.empty else t['price']
                
                pnl = (cur - t['price']) * t['quantity']
                total_unrealized += pnl
                
                stop_price = round(t['price'] * 0.985, 2)
                target_price = round(t['price'] * (1 + st.session_state.target_profit / 100), 2)
                
                rows.append({
                    "Asset": t['ticker'], "Entry Px": f"${t['price']:.2f}", "Current Px": f"${cur:.2f}", "Qty": t['quantity'], "Unrealized Profit": f"${pnl:.2f}"
                })
                
                # SELLING AUTOMATION RULES
                if auto_on:
                    if cur <= stop_price or cur >= target_price or (t['ticker'] == ticker and sig == "🔴 ULTRA SELL"):
                        try:
                            alpaca_ticker = t['ticker'].replace("-", "/") if "USD" in t['ticker'] else t['ticker']
                            alpaca_api.submit_order(symbol=alpaca_ticker, qty=t['quantity'], side='sell', type='market', time_in_force='gtc')
                            supabase.table("trades").update({"status": "CLOSED", "exit_price": cur, "exit_time": datetime.now(toronto_tz).strftime("%H:%M:%S")}).eq("id", t['id']).execute()
                            st.rerun()
                        except: pass
            
            st.table(pd.DataFrame(rows))
            pnl_color = "green" if total_unrealized >= 0 else "red"
            st.markdown(f"#### Total Unrealized PnL Profile: :{pnl_color}[${total_unrealized:.2f}]")
        else:
            st.info("Autopilot Active: Searching streaming structures for entry markers...")

        # BUYING AUTOMATION RULES
        is_crypto = "USD" in ticker
        if auto_on and (is_market_open or is_crypto) and slots < 4:
            if sig == "🟢 ULTRA BUY":
                already_holding = any(d['ticker'] == ticker for d in (active_res.data if active_res.data else []))
                if not already_holding:
                    try:
                        alpaca_ticker = ticker.replace("-", "/") if "USD" in ticker else ticker
                        risk_amount = st.session_state.balance * (st.session_state.risk_percent / 100)
                        qty = int(risk_amount / px)
                        
                        if qty > 0:
                            alpaca_api.submit_order(symbol=alpaca_ticker, qty=qty, side='buy', type='market', time_in_force='gtc')
                            execute_smart_buy(ticker, px)
                            st.rerun()
                    except Exception as api_err:
                        st.error(f"Alpaca Order Desk Deflected: {api_err}")

        # CHARTING CANVAS
        fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(template="plotly_dark", height=320, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # RECENT SELLING LOG
        st.markdown("### 📜 Recent Order Settlements Ledger")
        try:
            if history and history.data:
                closed_df = pd.DataFrame(history.data).tail(5)
                if not closed_df.empty:
                    st.dataframe(closed_df[['ticker', 'price', 'exit_price', 'date', 'exit_time']], use_container_width=True)
        except: pass

    live_engine(selected_ticker)
