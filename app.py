import streamlit as st
import pandas as pd
import yfinance as yf
import time

st.set_page_config(
    page_title="Pocket Option Signal Bot",
    page_icon="🎯",
    layout="centered"
)

st.title("🎯 Pocket Option Signal Bot")
st.caption("Regular Market • Strict Multi-Indicator Analysis")

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
duration = st.selectbox(
    "Trade Duration",
    ["1 minute", "5 minutes"]
)

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

        required = ["Open", "High", "Low", "Close"]

        for col in required:
            if col not in df.columns:
                return pd.DataFrame()

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.dropna(subset=required)

        return df

    except Exception:
        return pd.DataFrame()


def calculate_indicators(df):

    data = df.copy()

    # EMA trend
    data["EMA9"] = data["Close"].ewm(
        span=9,
        adjust=False
    ).mean()

    data["EMA20"] = data["Close"].ewm(
        span=20,
        adjust=False
    ).mean()

    data["EMA50"] = data["Close"].ewm(
        span=50,
        adjust=False
    ).mean()

    # Stochastic
    lowest = data["Low"].rolling(14).min()
    highest = data["High"].rolling(14).max()

    denominator = (highest - lowest).replace(0, pd.NA)

    data["K"] = (
        100 *
        (data["Close"] - lowest) /
        denominator
    )

    data["D"] = data["K"].rolling(3).mean()

    # ATR
    previous_close = data["Close"].shift(1)

    tr1 = data["High"] - data["Low"]
    tr2 = (data["High"] - previous_close).abs()
    tr3 = (data["Low"] - previous_close).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    data["ATR"] = true_range.rolling(14).mean()

    # Momentum
    data["Momentum"] = (
        data["Close"].pct_change(5) * 100
    )

    # Candle body
    data["Body"] = (
        data["Close"] - data["Open"]
    ).abs()

    return data.dropna()


def analyze_market(data):

    if len(data) < 60:
        return (
            "WAIT",
            0,
            0,
            0,
            "Not enough candles"
        )

    current = data.iloc[-1]
    previous = data.iloc[-2]

    call = 0
    put = 0

    call_reasons = []
    put_reasons = []

    # --------------------------------
    # 1. EMA TREND - 25 POINTS
    # --------------------------------

    if (
        current["EMA9"] >
        current["EMA20"] >
        current["EMA50"]
    ):
        call += 25
        call_reasons.append(
            "Bullish EMA trend"
        )

    elif (
        current["EMA9"] <
        current["EMA20"] <
        current["EMA50"]
    ):
        put += 25
        put_reasons.append(
            "Bearish EMA trend"
        )

    # --------------------------------
    # 2. PRICE VS EMA20 - 15 POINTS
    # --------------------------------

    if current["Close"] > current["EMA20"]:
        call += 15
        call_reasons.append(
            "Price above EMA20"
        )

    elif current["Close"] < current["EMA20"]:
        put += 15
        put_reasons.append(
            "Price below EMA20"
        )

    # --------------------------------
    # 3. STOCHASTIC CROSS - 20 POINTS
    # --------------------------------

    bullish_cross = (
        previous["K"] <= previous["D"]
        and current["K"] > current["D"]
    )

    bearish_cross = (
        previous["K"] >= previous["D"]
        and current["K"] < current["D"]
    )

    if bullish_cross:
        call += 20
        call_reasons.append(
            "Bullish stochastic cross"
        )

    elif bearish_cross:
        put += 20
        put_reasons.append(
            "Bearish stochastic cross"
        )

    # --------------------------------
    # 4. STOCHASTIC REVERSAL - 10 POINTS
    # --------------------------------

    if (
        current["K"] < 25
        and current["K"] > previous["K"]
    ):
        call += 10
        call_reasons.append(
            "Oversold recovery"
        )

    elif (
        current["K"] > 75
        and current["K"] < previous["K"]
    ):
        put += 10
        put_reasons.append(
            "Overbought rejection"
        )

    # --------------------------------
    # 5. MOMENTUM - 15 POINTS
    # --------------------------------

    if current["Momentum"] > 0:
        call += 15
        call_reasons.append(
            "Positive momentum"
        )

    elif current["Momentum"] < 0:
        put += 15
        put_reasons.append(
            "Negative momentum"
        )

    # --------------------------------
    # 6. CANDLE CONFIRMATION - 10 POINTS
    # --------------------------------

    candle_range = (
        current["High"] -
        current["Low"]
    )

    if candle_range > 0:

        body_ratio = (
            current["Body"] /
            candle_range
        )

        if body_ratio >= 0.55:

            if current["Close"] > current["Open"]:
                call += 10
                call_reasons.append(
                    "Strong bullish candle"
                )

            elif current["Close"] < current["Open"]:
                put += 10
                put_reasons.append(
                    "Strong bearish candle"
                )

    # --------------------------------
    # 7. VOLATILITY FILTER
    # --------------------------------

    atr_average = (
        data["ATR"]
        .rolling(20)
        .mean()
        .iloc[-1]
    )

    volatility_ok = (
        pd.notna(current["ATR"])
        and pd.notna(atr_average)
        and current["ATR"] >= atr_average * 0.70
    )

    if not volatility_ok:
        return (
            "WAIT",
            0,
            call,
            put,
            "Low volatility"
        )

    call = min(call, 100)
    put = min(put, 100)

    strength = max(call, put)
    difference = abs(call - put)

    # --------------------------------
    # STRICT SIGNAL FILTER
    # --------------------------------

    if (
        call >= 75
        and call > put
        and difference >= 25
    ):
        signal = "CALL"
        reason = " | ".join(call_reasons)

    elif (
        put >= 75
        and put > call
        and difference >= 25
    ):
        signal = "PUT"
        reason = " | ".join(put_reasons)

    else:
        signal = "WAIT"
        reason = (
            "Indicators are not sufficiently aligned"
        )

    return (
        signal,
        strength,
        call,
        put,
        reason
    )


# ==================================
# GET DATA
# ==================================

df = get_market_data(symbol)


if df.empty:

    st.error(
        "🔴 Market data unavailable."
    )

    st.info(
        "Try another regular-market asset."
    )

else:

    data = calculate_indicators(df)

    (
        signal,
        strength,
        call_score,
        put_score,
        reason
    ) = analyze_market(data)

    st.success(
        "🟢 Regular market data connected"
    )

    st.subheader(
        "Current Signal"
    )

    if signal == "CALL":

        st.success(
            "🟢 CALL"
        )

    elif signal == "PUT":

        st.error(
            "🔴 PUT"
        )

    else:

        st.warning(
            "⚪ WAIT"
        )

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

    latest_price = float(
        df["Close"].iloc[-1]
    )

    st.write(
        f"**Asset:** {asset}"
    )

    st.write(
        f"**Duration:** {duration}"
    )

    st.write(
        f"**Latest Price:** {latest_price:.5f}"
    )

    st.write(
        f"**Candles received:** {len(df)}"
    )

    st.info(
        f"🔎 {reason}"
    )

    st.caption(
        "The score measures indicator agreement. "
        "It is not a guaranteed win percentage."
    )


# ==================================
# AUTO REFRESH
# ==================================

time.sleep(30)
st.rerun()
After pasting, commit the file to "main" and wait for Streamlit to redeploy. Do not paste anything else into "app.py".
