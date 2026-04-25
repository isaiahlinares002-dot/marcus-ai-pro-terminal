import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from plotly.subplots import make_subplots
from datetime import datetime
from supabase import create_client, Client
import hashlib
from streamlit_autorefresh import st_autorefresh

# 1. 12-SECOND AUTO-REFRESH (Fast but stable)
st_autorefresh(interval=12 * 1000, key="terminal_pulse")

# 2. CLOUD CONNECTION
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

# 3. MODERN TERMINAL STYLING (The "Glass" UI)
st.set_page_config(page_title="Marcus.Ai Elite V4", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; font-family: 'Inter', sans-serif; }
    div[data-testid="stMetricValue"] { font-size: 28px; font-weight: 800; color: #58a6ff; }
    .stButton>button { 
        width: 100%; border-radius: 12px; height: 3.5em; 
        background: linear-gradient(145deg, #1f242d, #161b22);
        color: white; border: 1px solid #30363d; transition: 0.3s;
    }
    .stButton>button:hover { border-color: #58a6ff; box-shadow: 0px 0px 15px rgba(88, 166, 255, 0.3); }
    .trade-card { background: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# 4. LOGIN / SIGNUP
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🛡️ Marcus.Ai Secure Access")
    mode = st.sidebar.selectbox("Gate", ["Login", "Sign Up"])
    u = st.text_input("User")
    p = st.text_input("Pass", type='password')
    if st.button("Initialize Terminal"):
        if mode == "Login":
            res = supabase.table("users").select("password").eq("username", u).execute()
            if res.data and check_hashes(p, res.data[0]['password']):
                st.session_state.logged_in, st.session_state.username = True, u
                st.rerun()
            else: st.error("Access Denied")
        else:
            supabase.table("users").insert({"username": u, "password": make_hashes(p), "balance": 100000.0}).execute()
            st.success("Access Granted. Switch to Login.")
    st.stop()

# 5. FETCH DATA & LIVE PRICE
user_name = st.session_state.username
user_data = supabase.table("users").select("balance").eq("username", user_name).execute().data[0]
current_balance = float(user_data['balance'])

tickers = ["BTC-USD", "ETH-USD", "SOL-USD", "NVDA", "TSLA", "AAPL", "PLTR", "BABB", "LFVN"]
ticker = st.sidebar.selectbox("🎯 Active Ticker", sorted(tickers))
qty = st.sidebar.number_input("Order Quantity", min_value=1, value=10)

@st.cache_data(ttl=10)
def get_data(symbol):
    data = yf.download(symbol, period="1d", interval="1m", progress=False)
    if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
    return data

df = get_data(ticker)

if df is not None and not df.empty:
    curr_price = float(df['Close'].values[-1])
    
    # 6. AI SIGNAL LOGIC
    df_ai = df.tail(15).reset_index()
    X = np.array(df_ai.index).reshape(-1, 1)
    y = df_ai['Close'].values.flatten()
    slope = LinearRegression().fit(X, y).coef_[0]
    
    # UI HEADER
    st.title(f"⚡ {user_name}'s Terminal")
    st.write(f"Monitoring **{ticker}** | Auto-Refresh: 12s")
    
    # TOP METRICS BAR
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Live Price", f"${curr_price:,.2f}")
    m2.metric("Portfolio Cash", f"${current_balance:,.2f}")
    
    # 7. PROFIT/LOSS CALCULATION
    history_res = supabase.table("trades").select("*").eq("username", user_name).execute()
    history_df = pd.DataFrame(history_res.data)
    
    total_pl = 0
    if not history_df.empty:
        # Simple Logic: Current Value of all BUYS vs Sells
        buys = history_df[history_df['type'] == 'BUY']
        sells = history_df[history_df['type'] == 'SELL']
        # You can expand this logic, but for now we'll show total cash flow
        total_pl = current_balance - 100000.0
    
    pl_color = "normal" if total_pl >= 0 else "inverse"
    m3.metric("Total P/L", f"${total_pl:,.2f}", delta=f"{total_pl:,.2f}", delta_color=pl_color)
    
    with m4:
        if slope > 0.001: st.success("📈 STRONG BUY")
        elif slope < -0.001: st.error("📉 STRONG SELL")
        else: st.warning("⚖️ HOLD")

    # 8. TRADING CONTROLS
    col_main, col_side = st.columns([3, 1])
    
    with col_main:
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(height=450, template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_side:
        st.markdown('<div class="trade-card">', unsafe_allow_html=True)
        st.write("### Execution")
        if st.button("🚀 EXECUTE BUY"):
            cost = curr_price * qty
            if current_balance >= cost:
                supabase.table("users").update({"balance": current_balance - cost}).eq("username", user_name).execute()
                supabase.table("trades").insert({
                    "username": user_name, "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.now().strftime("%H:%M:%S"), "symbol": ticker,
                    "type": "BUY", "qty": qty, "price": curr_price, "total": cost
                }).execute()
                st.rerun()
        
        if st.button("🔥 EXECUTE SELL"):
            gain = curr_price * qty
            supabase.table("users").update({"balance": current_balance + gain}).eq("username", user_name).execute()
            supabase.table("trades").insert({
                "username": user_name, "date": datetime.now().strftime("%Y-%m-%d"),
                "time": datetime.now().strftime("%H:%M:%S"), "symbol": ticker,
                "type": "SELL", "qty": qty, "price": curr_price, "total": gain
            }).execute()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # 9. MODERN LEDGER
    st.divider()
    st.subheader("📜 Live Trading Ledger")
    if not history_df.empty:
        # Calculate Live Gain/Loss per row
        history_df = history_df.sort_values('id', ascending=False)
        st.dataframe(history_df[['date', 'time', 'symbol', 'type', 'qty', 'price', 'total']], use_container_width=True)
    else:
        st.info("No trades detected. Execute your first order to see the ledger.")

if st.sidebar.button("Secure Logout"):
    st.session_state.logged_in = False
    st.rerun()
