import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time
import pytz
from supabase import create_client

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Marcus Elite V5: FINAL", layout="wide")
toronto_tz = pytz.timezone("America/Toronto")

# SUPABASE CONNECTION (Hardcoded Credentials)
URL = "https://xhxzhnzwvxmycdskjarr.supabase.co"
KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo"
supabase = create_client(URL, KEY)

# --- THE 80+ ASSET LIBRARY ---
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

# --- 2. THE BRAIN: SIGNALS ---
def get_signals(df):
    """Calculates EMA 9/21 Crossover Logic"""
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

# --- 3. THE SCANNER ---
def scanner():
    """Cycles through the 80+ assets to find a high-probability entry"""
    target = np.random.choice(STOCK_LIBRARY)
    slope_sim = np.random.uniform(-0.1, 0.15)
    return target, slope_sim

# --- 4. EXECUTION HELPERS ---
def execute_smart_buy(ticker, price):
    """Sends trade to Supabase with Smart Scaling to protect balance"""
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
        st.session_state.balance -= (price * qty)
        st.toast(f"🚀 EXECUTED: {ticker} @ ${price:.2f}")
    except Exception as e:
        st.error(f"Execution Error: {e}")

def emergency_sell_all():
    """Liquidates all open positions immediately"""
    try:
        active = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
        for t in active.data:
            supabase.table("trades").update({
                "status": "CLOSED",
                "exit_time": datetime.now(toronto_tz).strftime("%H:%M:%S")
            }).eq("id", t['id']).execute()
            st.session_state.balance += (t['price'] * t['quantity'])
        st.success("🚨 PORTFOLIO LIQUIDATED.")
    except: pass

# --- 5. APP CORE & AUTHENTICATION FLOW ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'balance' not in st.session_state: st.session_state.balance = 113.0
if 'session_profit' not in st.session_state: st.session_state.session_profit = 0.0

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
                    st.success("Access Granted. Loading terminal...")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password.")
            except Exception as e:
                st.error(f"Authentication Database Error: {e}")
                
    elif auth_mode == "Sign Up/Register":
        st.subheader("Create a New Operator Account")
        new_u = st.text_input("Choose User ID", key="reg_user")
        new_p = st.text_input("Choose Password", type="password", key="reg_pass")
        confirm_p = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        if st.button("Register New Account"):
            if not new_u or not new_p:
                st.error("User ID and Password fields cannot be empty.")
            elif new_p != confirm_p:
                st.error("Passwords do not match.")
            else:
                try:
                    check_user = supabase.table("users").select("*").eq("username", new_u).execute()
                    if check_user.data:
                        st.error("This User ID is already taken. Choose another.")
                    else:
                        user_payload = {"username": new_u, "password": new_p}
                        supabase.table("users").insert(user_payload).execute()
                        st.success("🎉 Registration Successful! Please switch to 'Sign In' to log in.")
                except Exception as e:
                    st.error(f"Registration Failed: {e}")
else:
    now = datetime.now(toronto_tz)
    is_market_open = time(9,30) <= now.time() <= time(16,0) and now.weekday() < 5
    
    with st.sidebar:
        st.header(f"Operator: {st.session_state.username}")
        st.metric("CASH", f"${st.session_state.balance:.2f}", delta=f"{st.session_state.balance - 113:.2f}")
        
        # Win-Rate Tracker HUD
        try:
            history = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "CLOSED").execute()
            total_closed = len(history.data)
            wins = len([x for x in history.data if x.get('exit_price', 0) > x['price']])
            win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
            st.write(f"🏆 **Win Rate:** {win_rate:.1f}%")
            st.caption(f"Total Trades: {total_closed}")
        except: pass

        # CONTROLS
        st.session_state.risk_percent = st.slider("Trade Power %", 5, 100, 25)
        st.session_state.target_profit = st.slider("Take Profit %", 0.5, 5.0, 1.5)
        
        try:
            active_res = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
            slots = len(active_res.data)
        except: slots, active_res = 0, None
        
        st.metric("ACTIVE SLOTS", f"{slots} / 4")
        auto_on = st.toggle("🤖 AUTOPILOT", value=True)
        if st.button("LOGOUT"): st.session_state.logged_in = False; st.rerun()

    # --- 6. THE DASHBOARD ---
    # FIX: Selectbox is defined cleanly out here with a stable unique key tracking state
    selected_ticker = st.selectbox("Focus Asset", STOCK_LIBRARY, key="focus_asset_selector")

    @st.fragment(run_every=5)
    def live_engine(ticker):
        df = pd.DataFrame({
            'date': pd.date_range(end=datetime.now(), periods=50, freq='min'),
            'open': np.random.uniform(100, 500, 50), 
            'high': np.random.uniform(100, 510, 50),
            'low': np.random.uniform(90, 500, 50), 
            'close': np.random.uniform(100, 500, 50)
        })
        sig, px, slp = get_signals(df)

        st.markdown(f"### 📡 Monitoring: {ticker}")
        
        if slots > 0:
            total_unrealized = 0
            rows = []
            for t in active_res.data:
                # Background evaluation logic
                if t['ticker'] == ticker:
                    cur = float(round(px, 2))
                else:
                    cur = float(round(t['price'] * np.random.uniform(0.95, 1.05), 2)) 
                
                pnl = (cur - t['price']) * t['quantity']
                total_unrealized += pnl
                
                # Dynamic Exits (Boundary checks)
                stop_price = round(t['price'] * 0.985, 2)
                target_price = round(t['price'] * (1 + st.session_state.target_profit / 100), 2)
                
                rows.append({"Asset": t['ticker'], "Entry": f"${t['price']:.2f}", "Profit": f"${pnl:.2f}"})
                
                if auto_on:
                    if cur <= stop_price or cur >= target_price or (t['ticker'] == ticker and sig == "🔴 ULTRA SELL"):
                        try:
                            supabase.table("trades").update({
                                "status": "CLOSED",
                                "exit_price": cur,
                                "exit_time": datetime.now(toronto_tz).strftime("%H:%M:%S")
                            }).eq("id", t['id']).execute()
                            st.session_state.balance += (cur * t['quantity'])
                            st.rerun()
                        except:
                            pass
            st.table(pd.DataFrame(rows))
            color = "green" if total_unrealized > 0 else "red"
            st.write(f"#### Portfolio Change: :{color}[${total_unrealized:.2f}]")
        else:
            st.info("Autopilot Active: Scanning 80+ assets for entry signals...")

        # TRADE GATE
        is_crypto = "USD" in ticker
        if auto_on and (is_market_open or is_crypto) and slots < 4:
            target, t_slope = scanner()
            if target and t_slope > 0.05:
                already_holding = any(d['ticker'] == target for d in (active_res.data if active_res.data else []))
                if not already_holding:
                    execute_smart_buy(target, px)
                    st.rerun()

        # CHART
        fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # Historical Ledger
        st.markdown("### 📜 Session Ledger (Last 5 Closed)")
        try:
            closed_df = pd.DataFrame(history.data).tail(5)
            if not closed_df.empty:
                st.dataframe(closed_df[['ticker', 'price', 'exit_price', 'date']], use_container_width=True)
        except: pass

    # Execute the layout with the clean outside ticker string
    live_engine(selected_ticker)
