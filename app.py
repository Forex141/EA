import streamlit as st
import pandas as pd
import yfinance as yf
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

    data.columns = [
        str(column).lower()
        for column in data.columns
    ]

    needed = ["open", "high", "low", "close"]

    if not all(column in data.columns for column in needed):
        return pd.DataFrame()

    data = data[needed].copy()

    for column in needed:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    return data.dropna()


def calculate_signal(df):

    if len(df) < 20:
        return "WAIT", 0, 0, 0

    # ==========================
    # EMA / KELTNER
    # ==========================

    ema = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    # ==========================
    # STOCHASTIC
    # ==========================

    lowest = df["low"].rolling(14).min()
    highest = df["high"].rolling(14).max()

    spread = highest - lowest

    k = (
        100 * (df["close"] - lowest) / spread
    ).fillna(50)

    d = k.rolling(3).mean().fillna(50)

    # ==========================
    # SCORES
    # ==========================

    call_score = 0
    put_score = 0

    current_close = float(df["close"].iloc[-1])
    previous_close = float(df["close"].iloc[-2])
    current_ema = float(ema.iloc[-1])
    current_k = float(k.iloc[-1])
    current_d = float(d.iloc[-1])

    # Keltner / EMA direction
    if current_close > current_ema:
        call_score += 1
    elif current_close < current_ema:
        put_score += 1

    # Stochastic direction
    if current_k > current_d:
        call_score += 1
    elif current_k < current_d:
        put_score += 1

    # Price momentum
    if current_close > previous_close:
        call_score += 1
    elif current_close < previous_close:
        put_score += 1

    # Strong overbought/oversold confirmation
    if current_k < 20:
        call_score += 1

    elif current_k > 80:
        put_score += 1

    # Maximum displayed score = 3
    call_score = min(call_score, 3)
    put_score = min(put_score, 3)

    strongest = max(call_score, put_score)

    confidence = round(
        (strongest / 3) * 100
    )

    if call_score >= 2 and call_score > put_score:
        signal = "CALL"

    elif put_score >= 2 and put_score > call_score:
        signal = "PUT"

    else:
        signal = "WAIT"

    return (
        signal,
        confidence,
        call_score,
        put_score
    )


# ==========================
# GET MARKET DATA
# ==========================

df = get_market_data(assets[asset])

if df.empty:
    st.error("❌ No regular market data received.")
    st.stop()


# ==========================
# SIGNAL
# ==========================

signal, confidence, call_score, put_score = calculate_signal(df)


# ==========================
# DISPLAY
# ==========================

st.success("🟢 Regular market data connected")

st.subheader("Signal")

if signal == "CALL":
    st.success("📈 CALL")

elif signal == "PUT":
    st.error("📉 PUT")

else:
    st.warning("⏳ WAIT")


st.metric(
    "Signal Strength",
    f"{confidence}%"
)

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "CALL Score",
        f"{call_score}/3"
    )

with col2:
    st.metric(
        "PUT Score",
        f"{put_score}/3"
    )


st.write(f"**Asset:** {asset}")
st.write(f"**Duration:** {duration}")

latest_price = float(
    df["close"].iloc[-1]
)

st.write(
    f"**Latest Price:** {latest_price:.5f}"
)

st.write(
    f"**Candles received:** {len(df)}"
)

st.caption(
    "🔄 Regular market data refreshes every 30 seconds."
)

st.caption(
    "This is a signal-analysis tool. "
    "It does not automatically place Pocket Option trades."
)

time.sleep(30)
st.rerun()
