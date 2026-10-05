import streamlit as st
import pandas as pd
import yfinance as yf
from bot import analyze_signal

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

duration = st.selectbox(
    "Trade Duration",
    ["1 minute", "5 minutes"]
)

st.subheader("Indicators")
st.write("✅ ZigZag")
st.write("✅ Keltner Channel")
st.write("✅ Stochastic Oscillator")


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

    if not all(column in data.columns for column in required):
        return pd.DataFrame()

    return data[required].dropna()


df = get_market_data(assets[asset])

if df.empty:
    st.error("❌ No market candle data received.")
    st.stop()

result = analyze_signal(df)

signal = result["signal"]
confidence = result["confidence"]
call_score = result["call_score"]
put_score = result["put_score"]


st.success("🟢 Regular market data connected")

st.subheader("Signal")

if signal == "CALL":
    st.success("📈 CALL")
    st.metric("Confidence", f"{confidence}%")

elif signal == "PUT":
    st.error("📉 PUT")
    st.metric("Confidence", f"{confidence}%")

else:
    st.warning("⏳ WAIT")
    st.metric("Confidence", f"{confidence}%")

st.write(f"**CALL score:** {call_score}/3")
st.write(f"**PUT score:** {put_score}/3")

st.write(
    f"**Asset:** {asset}  •  **Duration:** {duration}"
)

st.write(
    f"**Latest price:** {df['close'].iloc[-1]:.5f}"
)

st.caption(
    "Regular market analysis using market data. "
    "The app does not directly place Pocket Option trades."
)

st.caption(
    "🔄 Market data refreshes every 30 seconds."
)

st.divider()

st.write(
    "⚠️ A CALL or PUT is shown only when at least two "
    "indicators agree. Otherwise the system remains on WAIT."
  )
