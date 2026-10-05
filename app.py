import streamlit as st
import pandas as pd
import yfinance as yf
import time

st.set_page_config(
    page_title="Pocket Option High-Accuracy Signal Bot",
    page_icon="🎯",
    layout="centered"
)

st.title("🎯 Pocket Option Signal Bot")
st.caption("Regular Markets • Strict Multi-Indicator Confirmation")

ASSETS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "USD/CHF": "CHF=X",
    "XAU/USD": "GC=F"
}

asset = st.selectbox("Select Asset", list(ASSETS.keys()))
duration = st.selectbox("Trade Duration", ["1 minute", "5 minutes"])

symbol = ASSETS[asset]


@st.cache_data(ttl=15)
def get_market_data(symbol):
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

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        cols = ["Open", "High", "Low", "Close"]

        for col in cols:
            if col not in df.columns:
                return pd.DataFrame()
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=cols)

        return df

    except Exception:
        return pd.DataFrame()


def calculate_indicators(df):

    d = df.copy()

    # EMA trend
    d["EMA9"] = d["Close"].ewm(span=9, adjust=False).mean()
    d["EMA20"] = d["Close"].ewm(span=20, adjust=False).mean()
    d["EMA50"] = d["Close"].ewm(span=50, adjust=False).mean()

    # Stochastic
    lowest = d["Low"].rolling(14).min()
    highest = d["High"].rolling(14).max()

    denominator = (highest - lowest).replace(0, pd.NA)

    d["K"] = (
        100 *
        (d["Close"] - lowest) /
        denominator
    )

    d["D"] = d["K"].rolling(3).mean()

    # ATR
    previous_close = d["Close"].shift(1)

    tr = pd.concat(
        [
            d["High"] - d["Low"],
            (d["High"] - previous_close).abs(),
            (d["Low"] - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    d["ATR"] = tr.rolling(14).mean()

    # Average volume when available
    if "Volume" in d.columns:
        d["Volume"] = pd.to_numeric(
            d["Volume"],
            errors="coerce"
        )

        d["VolumeMA"] = d["Volume"].rolling(20).mean()

    # Candle body
    d["Body"] = (d["Close"] - d["Open"]).abs()

    # Recent price momentum
    d["Momentum"] = d["Close"].pct_change(5) * 100

    return d.dropna()


def analyze(d):

    if len(d) < 60:
        return "WAIT", 0, 0, 0, "Not enough candles"

    c = d.iloc[-1]
    p = d.iloc[-2]

    call = 0
    put = 0

    call_reasons = []
    put_reasons = []

    # =====================================
    # 1. MAJOR TREND — 25 POINTS
    # =====================================

    if c["EMA9"] > c["EMA20"] > c["EMA50"]:
        call += 25
        call_reasons.append("Strong bullish EMA alignment")

    elif c["EMA9"] < c["EMA20"] < c["EMA50"]:
        put += 25
        put_reasons.append("Strong bearish EMA alignment")

    # =====================================
    # 2. PRICE LOCATION — 15 POINTS
    # =====================================

    if c["Close"] > c["EMA20"]:
        call += 15
        call_reasons.append("Price above EMA20")

    elif c["Close"] < c["EMA20"]:
        put += 15
        put_reasons.append("Price below EMA20")

    # =====================================
    # 3. STOCHASTIC CROSS — 20 POINTS
    # =====================================

    bullish_cross = (
        p["K"] <= p["D"] and
        c["K"] > c["D"]
    )

    bearish_cross = (
        p["K"] >= p["D"] and
        c["K"] < c["D"]
    )

    if bullish_cross:
        call += 20
        call_reasons.append("Bullish stochastic cross")

    elif bearish_cross:
        put += 20
        put_reasons.append("Bearish stochastic cross")

    # =====================================
    # 4. STOCHASTIC ZONE — 10 POINTS
    # =====================================

    if c["K"] < 25 and c["K"] > p["K"]:
        call += 10
        call_reasons.append("Oversold recovery")

    elif c["K"] > 75 and c["K"] < p["K"]:
        put += 10
        put_reasons.append("Overbought rejection")

    # =====================================
    # 5. MOMENTUM — 15 POINTS
    # =====================================

    if c["Momentum"] > 0:
        call += 15
        call_reasons.append("Positive momentum")

    elif c["Momentum"] < 0:
        put += 15
        put_reasons.append("Negative momentum")

    # =====================================
    # 6. CURRENT CANDLE — 10 POINTS
    # =====================================

    candle_range = c["High"] - c["Low"]

    if candle_range > 0:

        body_ratio = c["Body"] / candle_range

        if body_ratio >= 0.55:

            if c["Close"] > c["Open"]:
                call += 10
                call_reasons.append("Strong bullish candle")

            elif c["Close"] < c["Open"]:
                put += 10
                put_reasons.append("Strong bearish candle")

    # =====================================
    # 7. VOLATILITY FILTER
    # =====================================

    atr_average = d["ATR"].rolling(20).mean().iloc[-1]

    volatility_ok = (
        pd.notna(c["ATR"]) and
        pd.notna(atr_average) and
        c["ATR"] >= atr_average * 0.70
    )

    if not volatility_ok:
        # Low-volatility market = don't force trades
        return "WAIT", 0, call, put, "Low volatility — waiting"

    # =====================================
    # FINAL SCORE
    # =====================================

    call = min(call, 100)
    put = min(put, 100)

    difference = abs(call - put)
    strength = max(call, put)

    # =====================================
    # STRICT CONFIRMATION
    # =====================================

    if call >= 75 and call > put and difference >= 25:
        signal = "CALL"
        reason = " • ".join(call_reasons)

    elif put >= 75 and put > call and difference >= 25:
        signal = "PUT"
        reason = " • ".join(put_reasons)

    else:
        signal = "WAIT"
        reason = "Indicators are not sufficiently aligned"

    return signal, strength, call, put, reason


df = get_market_data(symbol)

if df.empty:

    st.error("🔴 Market data unavailable.")
    st.info("Try another regular-market asset.")

else:

    data = calculate_indicators(df)

    signal, strength, call_score, put_score, reason = analyze(data)

    st.success("🟢 Regular market data connected")

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

    st.write(f"**Asset:** {asset}")
    st.write(f"**Duration:** {duration}")
    st.write(
        f"**Latest Price:** {float(df['Close'].iloc[-1]):.5f}"
    )
    st.write(f"**Candles received:** {len(df)}")

    st.info(f"🔎 {reason}")

    st.caption(
        "Strict confirmation is used to reduce weak signals. "
        "Signal strength is indicator confluence, not a guaranteed win percentage."
    )


time.sleep(30)
st.rerun()

Replace only "app.py", commit to "main", and let Streamlit redeploy. This version is deliberately stricter: when the indicators disagree, it gives WAIT instead of forcing a trade.
