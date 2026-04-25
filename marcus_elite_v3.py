import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client, Client
import hashlib
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
st.set_page_config(page_title="Marcus.Ai Elite V4", layout="wide")

# Custom CSS for the Glow and Center Login
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    h1 { 
        text-align: center; 
        color: #ff4b4b; 
        text-shadow: 0px 0px 15px #ff4b4b; 
        font-family: 'Monaco', monospace;
        letter-spacing: 2px;
    }
    .login-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding-top: 100px;
    }
    div[data-testid="stMetricValue"] { color: #00FF00 !important; }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=12000, key="datarefresh")

def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        st.error("Check Streamlit Secrets.")
        st.stop()

supabase: Client = init_supabase()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- SHARED STATE ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
if 'user' not in st.session_state:
    st.session_state.user = ""

# --- LOGIN SCREEN (CENTERED) ---
if not st.session_state.auth:
    st.markdown("<h1>MARCUS ELITE V4</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        mode = st.radio("GATEWAY MODE", ["Login", "Sign Up"], horizontal=True)
        user_input = st.text_input("ID")
        pass_input = st.text_input("ACCESS KEY", type="password")
        
        if mode == "Login":
            if st.button("BYPASS GATEWAY"):
                res = supabase.table("users").select("*").eq("username", user_input).execute()
                if res.data and res.data[0]['password'] == make_hashes(pass_input):
                    st.session_state.auth = True
                    st.session_state.user = user_input
                    st.rerun()
                else:
                    st.error("ACCESS DENIED")
        else:
            if st.button("INITIALIZE ID"):
                try:
                    h_p = make_hashes(pass_input)
                    supabase.table("users").insert({"username": user_input, "password": h_p, "balance": 100000.0}).execute()
                    st.success("ID CREATED. SWITCH TO LOGIN.")
                except:
                    st.error("ID ALREADY EXISTS")

# --- TRADING TERMINAL ---
else:
    user_name = st.session_state.user
    # Get balance
    bal_res = supabase.table("users").select("balance").eq("username", user_name).execute()
    current_balance = bal_res.data[0]['balance']

    st.markdown(f"<h1>OPERATOR: {user_name.upper()}</h1>", unsafe_allow_html=True)
    
    # Sidebar for controls
    ticker = st.sidebar.selectbox("TARGET", ["BTC-USD", "NVDA", "AAPL", "TSLA", "ETH-USD"])
    qty = st.sidebar.number_input("QTY", min_value=1, value=1)
    
    # FIX: Fetching data and forcing 'live_price' to be a float
    data = yf.download(ticker, period="1d", interval="1m")
    if data.empty:
        st.error("LINK SEVERED.")
        st.stop()
        
    live_price = float(data['Close'].iloc[-1]) # FIX: Ensures it's a number
    
    # Signal Logic
    y = data['Close'].values
    x = range(len(y))
    slope = (len(x) * (x * y).sum() - sum(x) * sum(y)) / (len(x) * (sum([i**2 for i in x])) - (sum(x)**2))
    
    m1, m2, m3 = st.columns(3)
    m1.metric("LIVE PRICE", f"${live_price:,.2f}", delta=f"{slope:.4f}")
    m2.metric("CASH", f"${current_balance:,.2f}")
    
    total_pl = current_balance - 100000.0
    m3.metric("TOTAL P/L", f"${total_pl:,.2f}", delta=f"{total_pl:,.2f}", delta_color="normal")

    st.line_chart(data['Close'])

    if st.sidebar.button("EXECUTE BUY"):
        cost = live_price * qty
        if current_balance >= cost:
            new_bal = current_balance - cost
            supabase.table("users").update({"balance": new_bal}).eq("username", user_name).execute()
            supabase.table("trades").insert({
                "username": user_name, "symbol": ticker, "type": "BUY", 
                "qty": qty, "price": live_price, "total": cost,
                "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S")
            }).execute()
            st.rerun()

    if st.sidebar.button("EXECUTE SELL"):
        revenue = live_price * qty
        new_bal = current_balance + revenue
        supabase.table("users").update({"balance": new_bal}).eq("username", user_name).execute()
        supabase.table("trades").insert({
            "username": user_name, "symbol": ticker, "type": "SELL", 
            "qty": qty, "price": live_price, "total": revenue,
            "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S")
        }).execute()
        st.rerun()

    st.markdown("---")
    history = supabase.table("trades").select("*").order("created_at", desc=True).limit(50).execute()
    if history.data:
        st.dataframe(pd.DataFrame(history.data)[['username', 'symbol', 'type', 'qty', 'price', 'total']], use_container_width=True)
