import streamlit as st
import trading
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Marcus.AI", layout="wide")

# auto refresh every 10 seconds
st_autorefresh(interval=10000, key="refresh")

if "balance" not in st.session_state:
    st.session_state.balance = 10000

if "trades" not in st.session_state:
    st.session_state.trades = []

st.title("🤖 Marcus.AI")

tab1, tab2, tab3 = st.tabs(["Trading", "Paper Trading", "Journal"])

# ================= TRADING TAB =================
with tab1:
    symbol = st.selectbox("Choose Asset", trading.STOCKS)
    data = trading.get_data(symbol)

    if data is not None and not data.empty:

        fig = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close']
        )])

        fig.add_trace(go.Scatter(x=data.index, y=data["MA20"], name="MA20"))
        fig.add_trace(go.Scatter(x=data.index, y=data["MA50"], name="MA50"))

        st.plotly_chart(fig, use_container_width=True)

        signal, confidence, risk, win_rate = trading.get_ai_signal(data)

        st.subheader(f"Signal: {signal}")
        st.write(f"Confidence: {confidence}%")
        st.write(f"Risk: {risk}%")
        st.write(f"Win Rate: {win_rate}%")

# ================= PAPER TRADING =================
with tab2:
    st.header("Paper Trading")

    amount = st.number_input("Amount ($)", min_value=10)

    col1, col2 = st.columns(2)

    if col1.button("BUY"):
        st.session_state.balance -= amount
        st.session_state.trades.append({
            "symbol": symbol,
            "amount": amount,
            "type": "BUY"
        })

    if col2.button("SELL"):
        st.session_state.balance += amount
        st.session_state.trades.append({
            "symbol": symbol,
            "amount": amount,
            "type": "SELL"
        })

    st.write(f"Balance: ${st.session_state.balance}")

# ================= JOURNAL =================
with tab3:
    st.header("Journal")

    if len(st.session_state.trades) == 0:
        st.write("No trades yet")
    else:
        df = pd.DataFrame(st.session_state.trades)
        st.dataframe(df)