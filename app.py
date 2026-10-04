import streamlit as st
import pandas as pd
from bot import generate_signal

st.set_page_config(
    page_title="Pocket Option Signal Bot",
    page_icon="📊",
    layout="centered"
)

st.title("📊 Pocket Option Signal Bot")
st.write("ZigZag + Keltner Channel + Stochastic Oscillator")

st.divider()

asset = st.selectbox(
    "Select Asset",
    ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD"]
)

duration = st.selectbox(
    "Trade Duration",
    ["1 minute", "2 minutes", "5 minutes"]
)

st.subheader("Indicators")

zigzag = st.checkbox("ZigZag", value=True)
keltner = st.checkbox("Keltner Channel", value=True)
stochastic = st.checkbox("Stochastic Oscillator", value=True)

st.divider()

st.info(
    "Waiting for market candle data. "
    "Connect a supported market-data source to generate live signals."
)

st.subheader("Signal")

st.metric("Current Signal", "WAIT")

st.caption(
    f"Asset: {asset} • Duration: {duration}"
)

st.warning(
    "This app is a signal-analysis prototype. "
    "It does not directly place Pocket Option trades."
)
