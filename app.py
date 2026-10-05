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
st.caption("Regular Market • Multi-Indicator Signal Analysis")

# -----------------------------
# ASSETS
# -----------------------------
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

symbol = assets[asset]

# -----------------------------
# GET MARKET DATA
# -----------------------------
@st.cache_data(ttl=20)
def get_data(symbol):
    try:
        df = yf.download(
            symbol,
            period="1d",
            interval="1m",
            progress=False,
            auto_adjust=False
        )

        if df is None or df.empty:
            return pd.DataFrame()

        # Handle Yahoo multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required = ["Open", "High", "Low", "Close"]

        for col in required:
            if col not in df.columns:
                return pd.DataFrame()

            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=required)

        return df

    except Exception:
        return pd.DataFrame()


df = get_data(symbol)

# -----------------------------
# SIGNAL ENGINE
# -----------------------------
def analyze_market(df):

    if len(df) < 30:
        return "WAIT", 0, 0, 0, "Not enough candles"

    data = df.copy()

    # EMA
    data["EMA20"] = data["Close"].ewm(
        span=20,
        adjust=False
    ).mean()

    data["EMA50"] = data["Close"].ewm(
        span=50,
        adjust=False
    ).mean()

    # Stochastic
    low14 = data["Low"].rolling(14).min()
    high14 = data["High"].rolling(14).max()

    data["%K"] = (
        100 *
        (data["Close"] - low14) /
        (high14 - low14)
    )

    data["%D"] = data["%K"].rolling(3).mean()

    # ATR
    previous_close = data["Close"].shift(1)

    tr1 = data["High"] - data["Low"]
    tr2 = abs(data["High"] - previous_close)
    tr3 = abs(data["Low"] - previous_close)

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    data["ATR"] = true_range.rolling(14).mean()

    data = data.dropna()

    if len(data) < 5:
        return "WAIT", 0, 0, 0, "Indicator data unavailable"

    current = data.iloc[-1]
    previous = data.iloc[-2]

    call_score = 0
    put_score = 0

    # -----------------------------
    # 1. EMA TREND — 25 POINTS
    # -----------------------------
    if current["EMA20"] > current["EMA50"]:
        call_score += 25
    elif current["EMA20"] < current["EMA50"]:
        put_score += 25

    # -----------------------------
    # 2. PRICE VS EMA — 20 POINTS
    # -----------------------------
    if current["Close"] > current["EMA20"]:
        call_score += 20
    elif current["Close"] < current["EMA20"]:
        put_score += 20

    # -----------------------------
    # 3. STOCHASTIC — 20 POINTS
    # -----------------------------
    if current["%K"] > current["%D"]:
        call_score += 20
    elif current["%K"] < current["%D"]:
        put_score += 20

    # Oversold / overbought reversal
    if current["%K"] < 20 and current["%K"] > previous["%K"]:
        call_score += 10

    elif current["%K"] > 80 and current["%K"] < previous["%K"]:
        put_score += 10

    # -----------------------------
    # 4. MOMENTUM — 15 POINTS
    # -----------------------------
    if current["Close"] > previous["Close"]:
        call_score += 15
    elif current["Close"] < previous["Close"]:
        put_score += 15

    # -----------------------------
    # 5. CANDLE DIRECTION — 10 POINTS
    # -----------------------------
    if current["Close"] > current["Open"]:
        call_score += 10
    elif current["Close"] < current["Open"]:
        put_score += 10

    # -----------------------------
    # CAP SCORES
    # -----------------------------
    call_score = min(call_score, 100)
    put_score = min(put_score, 100)

    strength = max(call_score, put_score)

    # -----------------------------
    # SIGNAL FILTER
    # -----------------------------
    if call_score >= 70 and call_score > put_score:
        signal = "CALL"

    elif put_score >= 70 and put_score > call_score:
        signal = "PUT"

    else:
        signal = "WAIT"

    return (
        signal,
        strength,
        call_score,
        put_score,
        "Analysis complete"
    )


# -----------------------------
# RUN ANALYSIS
# -----------------------------
if df.empty:

    st.error("🔴 Market data unavailable.")
    st.info("Try another regular-market asset.")

else:

    signal, strength, call_score, put_score, status = analyze_market(df)

    st.success("🟢 Regular market data connected")

    # -----------------------------
    # SIGNAL DISPLAY
    # -----------------------------
    st.subheader("Current Signal")

    if signal == "CALL":
        st.success("🟢 CALL")

    elif signal == "PUT":
        st.error("🔴 PUT")

    else:
        st.warning("⚪ WAIT")

    st.metric(
        "Signal Strength",
        f"{strength}%"
    )

    # -----------------------------
    # SCORES
    # -----------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "CALL Score",
            f"{call_score}/100"
        )

    with col2:
        st.metric(
            "PUT Score",
            f"{put_score}/100"
        )

    # -----------------------------
    # MARKET INFORMATION
    # -----------------------------
    latest_price = float(df["Close"].iloc[-1])

    st.write(f"**Asset:** {asset}")
    st.write(f"**Duration:** {duration}")
    st.write(f"**Latest Price:** {latest_price:.5f}")
    st.write(f"**Candles received:** {len(df)}")

    st.caption(
        "Signal strength measures indicator agreement, "
        "not guaranteed winning probability."
    )

# -----------------------------
# AUTO REFRESH
# -----------------------------
time.sleep(30)
st.rerun()

Do this now

1. Open GitHub.
2. Open your repository.
3. Open "app.py".
4. Tap Edit ✏️.
5. Delete the old code.
6. Paste the code above.
7. Commit changes to "main".
8. Go back to Streamlit and wait for it to redeploy.
9. Open the app

Don't change "bot.py" or "requirements.txt". This version does the signal calculation directly in "app.py".
