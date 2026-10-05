import pandas as pd


def calculate_indicators(df):
    df = df.copy()

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "high", "low", "close"])

    # EMA / Keltner
    df["ema"] = df["close"].ewm(span=20, adjust=False).mean()

    tr1 = df["high"] - df["low"]
    tr2 = abs(df["high"] - df["close"].shift(1))
    tr3 = abs(df["low"] - df["close"].shift(1))

    df["atr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = df["atr"].rolling(10, min_periods=1).mean()

    df["upper"] = df["ema"] + 2 * df["atr"]
    df["lower"] = df["ema"] - 2 * df["atr"]

    # Stochastic
    lowest = df["low"].rolling(14, min_periods=1).min()
    highest = df["high"].rolling(14, min_periods=1).max()

    spread = highest - lowest

    df["k"] = 50.0
    valid = spread > 0
    df.loc[valid, "k"] = (
        100 * (df.loc[valid, "close"] - lowest[valid])
        / spread[valid]
    )

    df["d"] = df["k"].rolling(3, min_periods=1).mean()

    return df


def analyze_signal(df):

    df = calculate_indicators(df)

    if len(df) < 2:
        return {
            "signal": "WAIT",
            "confidence": 0,
            "call_score": 0,
            "put_score": 0
        }

    last = df.iloc[-1]
    previous = df.iloc[-2]

    call = 0
    put = 0

    # Keltner / EMA
    if last["close"] > last["ema"]:
        call += 1
    else:
        put += 1

    # Stochastic
    if last["k"] > last["d"]:
        call += 1
    else:
        put += 1

    # Price momentum
    if last["close"] > previous["close"]:
        call += 1
    elif last["close"] < previous["close"]:
        put += 1

    # Keep score 0-3
    call = min(call, 3)
    put = min(put, 3)

    strength = max(call, put)
    confidence = round((strength / 3) * 100)

    if call >= 2 and call > put:
        signal = "CALL"
    elif put >= 2 and put > call:
        signal = "PUT"
    else:
        signal = "WAIT"

    return {
        "signal": signal,
        "confidence": confidence,
        "call_score": call,
        "put_score": put
    }


def generate_signal(df):
    return analyze_signal(df)["signal"]
