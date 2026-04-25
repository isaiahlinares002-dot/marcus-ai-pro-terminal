import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client, Client
import hashlib
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION & DATABASE ---
st.set_page_config(page_title="Marcus.Ai Elite V4", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM "ELITE" STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 2rem; color: #00FF00; font-family: 'Courier New', monospace; }
    div[data-testid="stSidebar"] { background-image: linear-gradient(#1e1e2f, #0e1117); }
    h1 { text-shadow: 2px 2px #ff0000; font-family: 'Impact', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# 12-Second Heartbeat
st_autorefresh(interval=12000, key="datarefresh")

def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Missing Supabase Secrets!")
        st.stop()

supabase: Client = init_supabase()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- AUTHENTICATION UI ---
st.sidebar.title("🛡️ MARCUS.AI SECURE GATEWAY")
auth_mode = st.sidebar.selectbox("Mode", ["Login", "Sign Up"])
u = st.sidebar.text_input("Username")
p = st.sidebar.text_input("Password", type="password")

user_authenticated = False
user_name = ""
current_balance = 0.0

if auth_mode == "Sign Up":
    if st.sidebar.button("INITIALIZE ACCESS"):
        try:
            h_p = make_hashes(p)
            supabase.table("users").insert({"username": u, "password": h_p, "balance": 100000.0}).execute()
            st.sidebar.success("GATEWAY CREATED. LOG IN.")
        except:
            st.sidebar.error("ID ALREADY EXISTS.")

if auth_mode == "Login":
    if u and p:
        res = supabase.table("users").select("*").eq("username", u).execute()
        if res.data and res.data[0]['password'] == make_hashes(p):
            user_authenticated = True
            user_name = u
            current_balance = res.data[0]['balance']
        else:
            if st.sidebar.button("VERIFY"):
                st.sidebar.error("ACCESS DENIED.")

# --- MAIN TERMINAL INTERFACE ---
if user_authenticated:
    st.title(f"📈 MARCUS ELITE V4 // OPERATOR: {user_name.upper()}")
    
    ticker = st.sidebar.selectbox("TARGET ASSET", ["BTC-USD", "NVDA", "AAPL", "TSLA", "ETH-USD", "MSFT"])
    qty = st.sidebar.number_input("QUANTITY", min_value=1, value=1)
    
    data = yf.download(ticker, period="1d", interval="1m")
    if data.empty:
        st.error("DATA LINK SEVERED.")
        st.stop()
        
    live_price = data['Close'].iloc[-1]
    
    y = data['Close'].values
    x = range(len(y))
    slope = (len(x) * (x * y).sum() - sum(x) * sum(y)) / (len(x) * (sum([i**2 for i in x])) - (sum(x)**2))
    
    if slope > 0.01:
        signal, color = "📈 STRONG BUY", "#00FF00"
    elif slope < -0.01:
        signal, color = "📉 STRONG SELL", "#FF0000"
    else:
        signal, color = "⚖️ HOLD", "#808080"

    # Top Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("LIVE PRICE", f"${live_price:,.2f}", delta=f"{slope:.4f}")
    m2.metric("PORTFOLIO CASH", f"${current_balance:,.2f}")
    
    total_pl = current_balance - 100000.0
    # P/L FIX: Correct Color logic preserved
    m3.metric("TOTAL P/L", f"${total_pl:,.2f}", delta=f"{total_pl:,.2f}", delta_color="normal")

    st.subheader(f"{ticker} REAL-TIME FEED")
    st.line_chart(data['Close'])

    st.sidebar.markdown(f"### AI SIGNAL: <span style='color:{color}'>{signal}</span>", unsafe_allow_html=True)
    
    col_buy, col_sell = st.sidebar.columns(2)
    
    if col_buy.button("EXECUTE BUY"):
        cost = live_price * qty
        if current_balance >= cost:
            new_bal = current_balance - cost
            supabase.table("users").update({"balance": new_bal}).eq("username", user_name).execute()
            supabase.table("trades").insert({
                "username": user_name, "symbol": ticker, "type": "BUY", 
                "qty": qty, "price": float(live_price), "total": float(cost),
                "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S")
            }).execute()
            st.rerun()

    if col_sell.button("EXECUTE SELL"):
        revenue = live_price * qty
        new_bal = current_balance + revenue
        supabase.table("users").update({"balance": new_bal}).eq("username", user_name).execute()
        supabase.table("trades").insert({
            "username": user_name, "symbol": ticker, "type": "SELL", 
            "qty": qty, "price": float(live_price), "total": float(revenue),
            "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S")
        }).execute()
        st.rerun()

    st.markdown("---")
    st.subheader("📊 GLOBAL TRADING LEDGER")
    history = supabase.table("trades").select("*").order("created_at", desc=True).limit(50).execute()
    if history.data:
        df_ledger = pd.DataFrame(history.data)[['username', 'date', 'time', 'symbol', 'type', 'qty', 'price', 'total']]
        st.dataframe(df_ledger, use_container_width=True)

else:
    # THE "TOUGH" LOGIN UI
    st.markdown("<h1 style='text-align: center; color: red;'>SYSTEM LOCKED</h1>", unsafe_allow_html=True)
    st.image("https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&q=80&w=1000", caption="MARCUS.AI SECURE GATEWAY V4.0")
    st.info("Enter encrypted credentials in the sidebar to bypass security.")
