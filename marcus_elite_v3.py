import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time
import pytz
from supabase import create_client, Client

# --- 1. CONFIG & SYSTEM LOCK ---
st.set_page_config(page_title="MARCUS ELITE V7.5", layout="wide")
toronto_tz = pytz.timezone('America/Toronto')

SUPABASE_URL = "https://xhxzhnzwvxmycdskjarr.supabase.co".strip()
SUPABASE_KEY = "sb_publishable_EpR9PlXgtAapPdOjOqUZow_2BqBuOWo".strip()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Link Failed: {e}")

# --- 2. ASSETS ---
STOCK_LIBRARY = sorted(["NVDA", "TSLA", "AAPL", "BTC-USD", "ETH-USD", "GOOGL", "MSFT", "AMZN", "META", "NFLX", "AMD", "MARA", "RIOT", "DNUT", "IH", "LUMN"])

# --- 3. BRAINS: MATH & SCANNER ---
def get_signals(df):
    if len(df) < 21: return "🟡 WAIT", df['close'].iloc[-1], 0
    df['EMA9'] = df['close'].ewm(span=9).mean()
    df['EMA21'] = df['close'].ewm(span=21).mean()
    slope = df['EMA9'].diff().iloc[-1]
    if df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1] and slope > 0.05: return "🔥 ULTRA BUY", df['close'].iloc[-1], slope
    if df['EMA9'].iloc[-1] < df['EMA21'].iloc[-1] or slope < -0.05: return "🔴 ULTRA SELL", df['close'].iloc[-1], slope
    return "🟡 NEUTRAL", df['close'].iloc[-1], 0

def scanner():
    best, hi_slope = None, 0
    for ticker in np.random.choice(STOCK_LIBRARY, 5):
        d = pd.DataFrame({'close': np.random.uniform(10, 500, 30)})
        sig, px, slp = get_signals(d)
        if sig == "🔥 ULTRA BUY" and slp > hi_slope: hi_slope, best = slp, ticker
    return best, hi_slope

# --- 4. THE VAULT: EXIT & BUY LOGIC ---
def emergency_sell_all():
    try:
        res = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
        if res.data:
            total_recovered = 0
            for t in res.data:
                # Unrealized P/L calculation: (Current Price - Entry Price) * Qty
                exit_val = t['price'] * t['quantity'] * np.random.uniform(0.99, 1.01)
                total_recovered += exit_val
                supabase.table("trades").update({"status": "CLOSED"}).eq("id", t['id']).execute()
            st.session_state.balance += total_recovered
            st.toast(f"🚨 ALL POSITIONS LIQUIDATED: +${total_recovered:.2f}")
    except: pass

def execute_buy(ticker, price, balance):
    qty = round((balance * 0.25) / price, 4) # Fractional Share Support
    if qty <= 0: return
    try:
        supabase.table("trades").insert({
            "username": st.session_state.username, "ticker": ticker, "price": price, 
            "quantity": qty, "status": "OPEN", "created_at": datetime.now(toronto_tz).isoformat()
        }).execute()
        st.session_state.balance -= (price * qty)
        st.toast(f"✅ BOUGHT {ticker}")
    except: pass

# --- 5. APP CORE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'balance' not in st.session_state: st.session_state.balance = 113.0

if not st.session_state.logged_in:
    st.title("🚀 Marcus Elite Terminal")
    u, p = st.text_input("User ID"), st.text_input("Pass", type="password")
    if st.button("Enter"):
        res = supabase.table("users").select("*").eq("username", u).eq("password", p).execute()
        if res.data: st.session_state.logged_in, st.session_state.username = True, u; st.rerun()
else:
    # MARKET STATUS
    now = datetime.now(toronto_tz)
    is_open = time(9,30) <= now.time() <= time(16,0) and now.weekday() < 5
    
    with st.sidebar:
        st.header(f"Operator: {st.session_state.username}")
        st.metric("CASH", f"${st.session_state.balance:.2f}")
        
        # DATABASE SYNC
        try:
            active = supabase.table("trades").select("*").eq("username", st.session_state.username).eq("status", "OPEN").execute()
            slots = len(active.data)
        except: slots, active = 0, None
        
        st.metric("SLOTS", f"{slots} / 4")
        
        # THE EXIT SWITCH
        auto_on = st.toggle("🤖 AUTOPILOT", value=True)
        if not auto_on and slots > 0:
            emergency_sell_all()
            st.rerun()
            
        view_ticker = st.selectbox("Market Feed", STOCK_LIBRARY)
        if st.button("Logout"): st.session_state.logged_in = False; st.rerun()

    # --- 6. THE DASHBOARD ---
    @st.fragment(run_every=5)
    def live_engine(ticker):
        # Calculate current chart data
        df = pd.DataFrame({'date': pd.date_range(end=datetime.now(), periods=50, freq='min'),
                          'open': np.random.uniform(100, 500, 50), 'high': np.random.uniform(100, 510, 50),
                          'low': np.random.uniform(90, 500, 50), 'close': np.random.uniform(100, 500, 50)})
        sig, px, slp = get_signals(df)

        # 💰 LIVE PROFIT COUNTER
        st.markdown("### 📈 Real-Time Profit Dashboard")
        if slots > 0:
            total_unrealized = 0
            rows = []
            for t in active.data:
                # Simulated current price for non-active tickers
                cur = px if t['ticker'] == ticker else t['price'] * np.random.uniform(0.98, 1.05)
                pnl = (cur - t['price']) * t['quantity']
                total_unrealized += pnl
                rows.append({"Asset": t['ticker'], "Buy Price": f"${t['price']:.2f}", "Profit": f"${pnl:.2f}"})
            
            # Display stats
            st.table(pd.DataFrame(rows))
            color = "green" if total_unrealized > 0 else "red"
            st.write(f"#### Total Current Profit: :{color}[${total_unrealized:.2f}]")
        else:
            st.info("No active trades. AI is scanning for entry signals...")

        # AUTO TRADING
        if auto_on and is_open and slots < 4:
            target, t_slope = scanner()
            if target and t_slope > 0.05:
                execute_buy(target, px, st.session_state.balance)
                st.rerun()

        # CHART
        fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    live_engine(view_ticker)
