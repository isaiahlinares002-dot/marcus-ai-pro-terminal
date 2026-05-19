import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, time
import pytz
from supabase import create_client
from alpaca_trade_api.rest import REST
from alpaca_trade_api import TimeFrame

# --- 1. INITIAL SETUP & APP CONFIG ---
st.set_page_config(page_title="Marcus Elite Master Terminal v7", layout="wide")
toronto_tz = pytz.timezone("America/Toronto")

# SUPABASE CONNECTION (Cloud Ledger Database)
URL = "https://xhxzhnzwvxmycdskjarr.supabase.co"
KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo"
supabase = create_client(URL, KEY)

# 🔐 LIVE LIVE-MARKET CREDENTIALS SYNCHRONIZED
PAPER_API_KEY = "PKVWJEGXBXQZVDF5V3SHG4W5UW"
PAPER_SECRET_KEY = "E2UMkjdSdQMHfi2o2oi3AcasDpj9yaCcckzkyv1c7fit"

LIVE_API_KEY = "YOUR_LIVE_KEY_HERE"
LIVE_SECRET_KEY = "YOUR_LIVE_SECRET_HERE"

# --- FULL 80+ ASSET LIBRARY ---
STOCK_LIBRARY = [
    "ETH-USD", "BTC-USD", "SOL-USD", "AAPL", "TSLA", "NVDA", "PLTR", "COIN", "VNCE", "AMD",
    "MSFT", "GOOGL", "META", "AMZN", "NFLX", "INTC", "PYPL", "SQ", "SHOP", "RIVN",
    "LCID", "BABA", "NIO", "XPEV", "PFE", "MRNA", "JPM", "GS", "V", "MA",
    "DIS", "SBUX", "NKE", "F", "GM", "AMC", "GME", "BB", "AI", "SOFI",
    "ROKU", "SNAP", "U", "DKNG", "HOOD", "UPST", "AFRM", "MARA", "RIOT", "CLSK",
    "MSTR", "T", "VZ", "TMUS", "WMT", "TGT", "COST", "HD", "LOW", "UNH",
    "CRM", "SNOW", "PLD", "AMT", "CAT", "DE", "BA", "LMT", "RTX", "GE",
    "XOM", "CVX", "OXY", "SLB", "RIG", "FCX", "NEM", "GOLD", "TLT", "SPY"
]

# --- 2. BROKERAGE CONNECTION MANAGER ---
def get_alpaca_client(mode):
    """Switches connection endpoints seamlessly depending on UI selection"""
    if mode == "🚀 LIVE TRADING":
        base_url = "https://api.alpaca.markets"
        return REST(LIVE_API_KEY, LIVE_SECRET_KEY, base_url, api_version='v2')
    else:
        base_url = "https://paper-api.alpaca.markets"
        return REST(PAPER_API_KEY, PAPER_SECRET_KEY, base_url, api_version='v2')

# --- 3. THE MATH BRAIN: ALGORITHMIC SIGNALS ---
def get_signals(df):
    """Calculates Exponential Moving Averages & Trend Directions"""
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    last_px = df['close'].iloc[-1]
    prev_9, last_9 = df['ema9'].iloc[-2], df['ema9'].iloc[-1]
    prev_21, last_21 = df['ema21'].iloc[-2], df['ema21'].iloc[-1]
    
    slope = (last_9 - prev_9) / prev_9
    
    if prev_9 < prev_21 and last_9 > last_21:
        return "🟢 ULTRA BUY", last_px, slope
    elif prev_9 > prev_21 and last_9 < last_21:
        return "🔴 ULTRA SELL", last_px, slope
    return "⚪ SCANNING", last_px, slope

# --- 4. REAL-TIME DATA INGESTION ENGINE ---
def fetch_real_data(api, ticker):
    """Streams actual historical 1-minute candlestick data from Alpaca"""
    try:
        alpaca_ticker = ticker.replace("-", "/") if "USD" in ticker else ticker
        end_dt = datetime.now(toronto_tz)
        start_dt = end_dt - timedelta(hours=3)
        
        bars = api.get_bars(
            alpaca_ticker, 
            TimeFrame.Minute, 
            start=start_dt.isoformat(), 
            end=end_dt.isoformat(), 
            adjustment='raw'
        ).df
        
        if bars.empty:
            return pd.DataFrame({'close': [100.0]*50, 'open':[100.0]*50, 'high':[100.0]*50, 'low':[100.0]*50, 'date': pd.date_range(end=datetime.now(), periods=50, freq='min')})
            
        bars = bars.reset_index()
        bars = bars.rename(columns={'timestamp': 'date'})
        return bars[['date', 'open', 'high', 'low', 'close']]
    except Exception:
        return pd.DataFrame({'close': [100.0]*50, 'open':[100.0]*50, 'high':[100.0]*50, 'low':[100.0]*50, 'date': pd.date_range(end=datetime.now(), periods=50, freq='min')})

# --- 5. AUTOMATED EXECUTION HANDSHAKES ---
def execute_smart_buy(ticker, price):
    """Dispatches trade signals directly onto the cloud ledger database"""
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
        st.toast(f"🚀 LEDGER OVERRIDE: Position Opened for {ticker} @ ${price:.2f}")
    except Exception as e:
        st.error(f"Ledger Sync Interrupted: {e}")

def emergency_sell_all(api):
    """Instantly unwinds and liquidates every active position across the board"""
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
        st.toast("🚨 PORTFOLIO LIQUIDATED IN LEDGER & CORES.")
        st.rerun()
    except Exception as e:
        st.error(f"Liquidation Override Failed: {e}")

# --- 6. AUTHENTICATION GATE (SIGN IN & REGISTER FULLY RESTORED) ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'balance' not in st.session_state: st.session_state.balance = 113.0

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
                    st.success("Access Granted. Loading terminal architecture...")
                    st.rerun()
                else:
                    st.error("Invalid Operator ID or Password.")
            except Exception as e:
                st.error(f"Database Security Authentication Error: {e}")
                
    elif auth_mode == "Sign Up/Register":
        st.subheader("Register a New Terminal Operator Profile")
        new_u = st.text_input("Choose User ID", key="reg_user")
        new_p = st.text_input("Choose Password", type="password", key="reg_pass")
        confirm_p = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        if st.button("Register Account"):
            if not new_u or not new_p:
                st.error("User ID and Password fields cannot be empty.")
            elif new_p != confirm_p:
                st.error("Confirmation passwords do not match.")
            else:
                try:
                    check_user = supabase.table("users").select("*").eq("username", new_u).execute()
                    if check_user.data:
                        st.error("This Operator ID is already taken. Choose another.")
                    else:
                        user_payload = {"username": new_u, "password": new_p}
                        supabase.table("users").insert(user_payload).execute()
                        st.success("🎉 Registration Confirmed! Flip back to 'Sign In' to log into your terminal.")
                except Exception as e:
                    st.error(f"Registration Sync Failed: {e}")
else:
    # --- 7. ACTIVE DASHBOARD SYSTEM ---
    now = datetime.now(toronto_tz)
    is_market_open = time(9,30) <= now.time() <= time(16,0) and now.weekday() < 5
    
    # ADVANCED STATISTICS MATRICES (Win Percentage Engine)
    try:
        history = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "CLOSED").execute()
        total_closed = len(history.data)
        wins = len([x for x in history.data if x.get('exit_price', 0) > x['price']])
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
    except:
        total_closed, win_rate, history = 0, 0.0, None

    with st.sidebar:
        st.header(f"Operator: {st.session_state.username}")
        
        # ENVIRONMENT MANAGEMENT SWITCH
        trade_mode = st.radio("💰 TERMINAL ENVIRONMENT", ["🛠️ PAPER TRADING", "🚀 LIVE TRADING"], horizontal=False)
        alpaca_api = get_alpaca_client(trade_mode)
        
        # ACCOUNT FUND STREAM TRACKING
        try:
            account = alpaca_api.get_account()
            st.session_state.balance = float(account.cash)
            st.metric("BROKERAGE CASH", f"${st.session_state.balance:.2f}")
        except Exception as api_err:
            st.metric("MOCK CASH (API Disconnected)", f"${st.session_state.balance:.2f}")
            st.error(f"Connection Blocked on this mode: {api_err}")

        # METRICS STATS SUB-BAR
        st.markdown("---")
        st.write(f"🏆 **Mathematical Win Rate:** {win_rate:.1f}%")
        st.caption(f"Total Historical Trades Documented: {total_closed}")
        st.markdown("---")

        # ENGINE DIALS
        st.session_state.risk_percent = st.slider("Trade Power %", 5, 100, 100)
        st.session_state.target_profit = st.slider("Take Profit %", 0.5, 5.0, 1.5)
        auto_on = st.toggle("🤖 AUTOPILOT SCANNING", value=True)
        
        if st.button("🚨 EMERGENCY portfolio UNWIND", use_container_width=True):
            emergency_sell_all(alpaca_api)
            st.rerun()
                
        if st.button("TERMINAL LOGOUT"): 
            st.session_state.logged_in = False
            st.rerun()

    # MAIN CONTROL DECK INTERFACE
    selected_ticker = st.selectbox("Focus Asset Tracker", STOCK_LIBRARY, key="focus_asset_selector")

    @st.fragment(run_every=5)
    def live_engine(ticker):
        try:
            active_res = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
            slots = len(active_res.data)
        except: 
            slots, active_res = 0, None

        # PULL RAW BARS FOR CANDLESTICKS
        df = fetch_real_data(alpaca_api, ticker)
        sig, px, slp = get_signals(df)

        st.markdown(f"### 📡 Monitoring Interface: {ticker} (Real-Time: ${px:.2f})")
        st.write(f"**Current Position Capacities:** {slots} / 4 Active Allocations")
        
        # --- UNREALIZED PROFIT/LOSS SECTION ---
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
                    "Asset": t['ticker'], 
                    "Entry Px": f"${t['price']:.2f}", 
                    "Current Px": f"${cur:.2f}", 
                    "Qty": t['quantity'],
                    "Unrealized Profit": f"${pnl:.2f}"
                })
                
                # AUTOMATED REBALANCING ROUTINE EXECUTION
                if auto_on:
                    if cur <= stop_price or cur >= target_price or (t['ticker'] == ticker and sig == "🔴 ULTRA SELL"):
                        try:
                            alpaca_ticker = t['ticker'].replace("-", "/") if "USD" in t['ticker'] else t['ticker']
                            alpaca_api.submit_order(symbol=alpaca_ticker, qty=t['quantity'], side='sell', type='market', time_in_force='gtc')
                            supabase.table("trades").update({
                                "status": "CLOSED",
                                "exit_price": cur,
                                "exit_time": datetime.now(toronto_tz).strftime("%H:%M:%S")
                            }).eq("id", t['id']).execute()
                            st.rerun()
                        except: pass
            
            st.table(pd.DataFrame(rows))
            pnl_color = "green" if total_unrealized >= 0 else "red"
            st.markdown(f"#### Total Unrealized PnL Profile: :{pnl_color}[${total_unrealized:.2f}]")
        else:
            st.info("Autopilot Standing By: Parsing active streaming feeds for valid trade entry triggers...")

        # ALGORITHMIC ENTRY ROUTINES
        is_crypto = "USD" in ticker
        if auto_on and (is_market_open or is_crypto) and slots < 4:
            if sig == "🟢 ULTRA BUY" and slp > 0.01:
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

        # INTERACTIVE CHART SYSTEM
        fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(template="plotly_dark", height=320, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # HISTORICAL TRANSACTION LOG (Shows last 5 closed trades)
        st.markdown("### 📜 Recent Order Settlements Ledger")
        try:
            if history and history.data:
                closed_df = pd.DataFrame(history.data).tail(5)
                if not closed_df.empty:
                    st.dataframe(closed_df[['ticker', 'price', 'exit_price', 'date', 'exit_time']], use_container_width=True)
            else:
                st.caption("No closed transactions recorded yet for this operational session.")
        except: pass

    live_engine(selected_ticker)
