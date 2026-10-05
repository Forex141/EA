import streamlit as st
import pandas as pd
import yfinance as yf
from bot import generate_signal
import time

st.set_page_config(
    page_title="Pocket Option Signal Bot",
    page_icon="📊",
    layout="centered"
)

st.title("📊 Pocket Option Signal Bot")
st.write("ZigZag + Keltner Channel + Stochastic Oscillator")

assets = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "USD/CHF": "CHF=X",
    "XAU/USD": "GC=F"
}

asset = st.selectbox("Select Asset", list(assets.keys()))
duration = st.selectbox("Trade Duration", ["1 minute", "5 minutes"])

st.subheader("Indicators")
st.write("ZigZag")
st.write("Keltner Channel")
st.write("Stochastic Oscillator")


@st.cache_data(ttl=30)
def get_market_data(symbol):
    data = yf.download(
        symbol,
        period="1d",
        interval="1m",
        progress=False,
        auto_adjust=False
    )

    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data.columns = [str(c).lower() for c in data.columns]

    required = ["open", "high", "low", "close"]

    if not all(c in data.columns for c in required):
        return pd.DataFrame()

    return data[required].dropna()


df = get_market_data(assets[asset])

if df.empty:
    st.error("No live market candle data received.")
    st.stop()

signal = generate_signal(df)

st.success("🟢 Live market data connected")

st.subheader("Signal")

if signal == "CALL":
    st.success("📈 CALL")
elif signal == "PUT":
    st.error("📉 PUT")
else:
    st.warning("⏳ WAIT")

st.metric("Current Signal", signal)

st.write(f"Asset: {asset} • Duration: {duration}")

st.caption(
    "Regular market analysis using live market data. "
    "The app does not directly place Pocket Option trades."
)

st.caption("🔄 Market data refreshes automatically every 30 seconds.")

time.sleep(30)
st.rerun()
