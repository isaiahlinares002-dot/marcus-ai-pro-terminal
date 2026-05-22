import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time
import pytz
import requests
from supabase import create_client

# --- 1. INITIAL SETUP & APP CONFIG ---
st.set_page_config(page_title="Marcus Elite Master Terminal v7", layout="wide")
toronto_tz = pytz.timezone("America/Toronto")

# SUPABASE CONNECTION (Cloud Ledger Database)
URL = "https://xhxzhnzwvxmycdskjarr.supabase.co"
KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo"
supabase = create_client(URL, KEY)

# 🔐 HIGH-SPEED USER PAPER CERTIFICATES REGISTERED
PAPER_API_KEY = "PKKJYWAN6ZEDTBPTWHQRV26Q4Y"
PAPER_SECRET_KEY = "GnsyXG84eJ4C5YEbjdFSdZYC2pyiDb6ZNGDLGnHcYvo9"

# --- ACTIVE LIBRARY TRACKER ---
STOCK_LIBRARY = [
    "ETH-USD", "BTC-USD", "SOL-USD", "AAPL", "TSLA", "NVDA", "PLTR", "COIN", "VNCE", "AMD",
    "MSFT", "GOOGL", "META", "AMZN", "NFLX", "INTC", "PYPL", "SQ", "SHOP", "RIVN"
]

# --- 2. HIGH-FREQUENCY INTRA-DAY SIGNAL ENGINE ---
def get_signals(df):
    """Calculates ultra-fast 3/8 EMA parameters to catch intra-day micro-swings"""
    if df.empty or len(df) < 10:
        return "⚪ SCANNING", 100.0, 0.0
        
    df['ema_fast'] = df['close'].ewm(span=3, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=8, adjust=False).mean()
    
    last_px = float(df['close'].iloc[-1])
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

# --- 3. HIGH-SPEED DIRECT YAHOO ENDPOINT STREAM (NO YFINANCE PACKET REQUIRED) ---
def fetch_real_data(ticker):
    """Hits Yahoo's raw public endpoint via native requests to completely bypass rate-blocks"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1m"
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return pd.DataFrame()
            
        data = response.json()
        result = data['chart']['result'][0]
        
        timestamps = result['timestamp']
        indicators = result['indicators']['quote'][0]
        
        df = pd.DataFrame({
            'date': pd.to_datetime(timestamps, unit='s', utc=True),
            'open': indicators['open'],
            'high': indicators['high'],
            'low': indicators['low'],
            'close': indicators['close']
        })
        
        # Clean out any empty missing market micro-ticks safely
        df = df.dropna().reset_index(drop=True)
        df['date'] = df['date'].dt.tz_convert("America/Toronto")
        return df[['date', 'open', 'high', 'low', 'close']]
    except Exception:
        return pd.DataFrame()

# --- 4. AUTOMATED API EXECUTION HANDSHAKES ---
def alpaca_order(symbol, qty, side):
    """Submits raw order execution structures directly to Alpaca paper desks"""
    try:
        url = "https://paper-api.alpaca.markets/v2/orders"
        headers = {
            "Apca-Api-Key-Id": PAPER_API_KEY,
            "Apca-Api-Secret-Key": PAPER_SECRET_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "symbol": symbol.replace("-", "/") if "USD" in symbol else symbol,
            "qty": str(qty),
            "side": side,
            "type": "market",
            "time_in_force": "gtc"
        }
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        return r.status_code == 200 or r.status_code == 201
    except:
        return False

def execute_smart_buy(ticker, price):
    """Saves executed order configurations safely into the Supabase accounting matrix"""
    try:
        power_ratio = 1 / 5 
        risk_amount = st.session_state.balance * (st.session_state.risk_percent / 100) * power_ratio
        
        qty = int(risk_amount / price) if price > 0 else 0
        if qty <= 0: return False

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
        st.toast(f"🟢 AUTO ENTRY RECORDED: {ticker} ({qty} units) @ ${price:.2f}")
        return True
    except Exception as e:
        st.error(f"Ledger Sync Broken: {e}")
        return False

def emergency_sell_all():
    """Instantly liquidates all positions across every open channel to cash out"""
    try:
        active = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
        for t in active.data:
            alpaca_order(t['ticker'], t['quantity'], 'sell')
            supabase.table("trades").update({
                "status": "CLOSED",
                "exit_price": t['price'],
                "exit_time": datetime.now(toronto_tz).strftime("%H:%M:%S")
            }).eq("id", t['id']).execute()
        st.toast("💰 CASH-OUT SUCCESSFUL: All structural assets liquidated cleanly.")
        st.rerun()
    except Exception as e:
        st.error(f"Liquidation Error: {e}")

# --- 5. AUTHENTICATION GATE ---
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
            except Exception as e: st.error(f"Authentication Error: {e}")
                
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
    # --- 6. ACTIVE DASHBOARD SYSTEM ---
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
        st.markdown("💰 ENVIRONMENT: **REAL-TIME SWAP AUTOMATION**")
        
        try:
            url = "https://paper-api.alpaca.markets/v2/account"
            headers = {"Apca-Api-Key-Id": PAPER_API_KEY, "Apca-Api-Secret-Key": PAPER_SECRET_KEY}
            acct_res = requests.get(url, headers=headers, timeout=5).json()
            st.session_state.balance = float(acct_res.get('cash', 100000.0))
            st.metric("BROKERAGE CASH BALANCE", f"${st.session_state.balance:.2f}")
        except:
            st.metric("BROKERAGE CASH BALANCE", f"${st.session_state.balance:.2f}")

        st.markdown("---")
        st.write(f"🏆 **System Win Rate:** {win_rate:.1f}%")
        st.caption(f"Settled Trades: {total_closed}")
        st.markdown("---")

        st.session_state.risk_percent = st.slider("Total Engine Power %", 5, 100, 100)
        st.session_state.target_profit = st.slider("Take Profit Target %", 0.5, 5.0, 1.2)
        auto_on = st.toggle("🤖 ENGINE AUTOPILOT MAIN SWITCH", value=True)
        
        if st.button("🚨 CASH-OUT & UNWIND PORTFOLIO", use_container_width=True):
            emergency_sell_all()
            st.rerun()
        if st.button("TERMINAL LOGOUT"): 
            st.session_state.logged_in = False
            st.rerun()

    selected_ticker = st.selectbox("Focal Analytics Display View", STOCK_LIBRARY, key="focus_asset_selector")

    @st.fragment(run_every=5)
    def live_engine(ticker):
        try:
            active_res = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
            slots = len(active_res.data)
            current_held_tickers = [d['ticker'] for d in active_res.data] if active_res.data else []
        except: 
            slots, active_res, current_held_tickers = 0, None, []

        # --- 📈 7. PARALLEL CALCULATION ENGINE & TOP FINDER ---
        st.markdown("### 📡 Live Calculation Radar (Scanning Entire Library via Free Live Streams)")
        radar_data = []
        valid_buys = []
        
        # Free Live Stocks run Mon-Fri market hours; Crypto runs 24/7/365
        active_scan_list = STOCK_LIBRARY if is_market_open else ["ETH-USD", "BTC-USD", "SOL-USD"]
        
        for asset in active_scan_list:
            asset_df = fetch_real_data(asset)
            if not asset_df.empty:
                sig, px, slp = get_signals(asset_df)
                radar_data.append({"Asset": asset, "Price": f"${px:.2f}", "Calculated State": sig, "Slope Momentum": slp})
                
                if sig == "🟢 ULTRA BUY" and asset not in current_held_tickers:
                    valid_buys.append({"ticker": asset, "price": px, "slope": slp})
                    
        if radar_data:
            radar_df = pd.DataFrame(radar_data).sort_values(by="Slope Momentum", ascending=False)
            st.dataframe(radar_df, use_container_width=True)
        else:
            st.warning("Synchronizing multi-channel real-time arrays...")

        # Get data chunk for the selected focal chart view
        df = fetch_real_data(ticker)
        if df.empty:
            st.info("Loading visualization stream candles...")
            return

        _, focus_px, _ = get_signals(df)
        st.markdown(f"#### 📊 Focal Chart Feed: {ticker} (${focus_px:.2f})")
        st.write(f"**Autonomous Channels Active:** {slots} / 5 Running Positions")
        
        # --- POSITION LEDGER GRID ---
        if slots > 0:
            total_unrealized = 0
            rows = []
            for t in active_res.data:
                if t['ticker'] == ticker:
                    cur = float(round(focus_px, 2))
                else:
                    bg_df = fetch_real_data(t['ticker'])
                    cur = float(round(bg_df['close'].iloc[-1], 2)) if not bg_df.empty else t['price']
                
                pnl = (cur - t['price']) * t['quantity']
                total_unrealized += pnl
                
                stop_price = round(t['price'] * 0.985, 2)
                target_price = round(t['price'] * (1 + st.session_state.target_profit / 100), 2)
                
                rows.append({
                    "Asset": t['ticker'], "Entry Px": f"${t['price']:.2f}", "Current Px": f"${cur:.2f}", "Qty": t['quantity'], "Unrealized Profit": f"${pnl:.2f}"
                })
                
                # SELLING AUTOMATION RULES (Evaluated directly across parallel structures)
                if auto_on:
                    asset_chk = next((item for item in radar_data if item["Asset"] == t['ticker']), None)
                    current_sig = asset_chk["Calculated State"] if asset_chk else "⚪ SCANNING"
                    
                    if cur <= stop_price or cur >= target_price or current_sig == "🔴 ULTRA SELL":
                        alpaca_order(t['ticker'], t['quantity'], 'sell')
                        supabase.table("trades").update({"status": "CLOSED", "exit_price": cur, "exit_time": datetime.now(toronto_tz).strftime("%H:%M:%S")}).eq("id", t['id']).execute()
                        st.toast(f"🔴 AUTO EXIT TRIGGERED: Closed position for {t['ticker']} at ${cur:.2f}")
                        st.rerun()
            
            st.table(pd.DataFrame(rows))
            pnl_color = "green" if total_unrealized >= 0 else "red"
            st.markdown(f"#### Total Unrealized PnL Profile: :{pnl_color}[${total_unrealized:.2f}]")
        else:
            st.info("Autopilot Active: System searching live calculations to populate free tracks...")

        # MULTI-SLOT AUTONOMOUS BUY RULES (Fires automatically on top calculated slots)
        if auto_on and slots < 5 and valid_buys:
            sorted_buys = sorted(valid_buys, key=lambda x: x['slope'], reverse=True)
            
            for potential_buy in sorted_buys:
                if slots >= 5:
                    break
                    
                alpaca_ticker = potential_buy['ticker']
                px = potential_buy['price']
                
                power_ratio = 1 / 5
                risk_amount = st.session_state.balance * (st.session_state.risk_percent / 100) * power_ratio
                qty = int(risk_amount / px)
                
                if qty > 0:
                    success = alpaca_order(alpaca_ticker, qty, 'buy')
                    if success:
                        execute_smart_buy(alpaca_ticker, px)
                        st.rerun()

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
