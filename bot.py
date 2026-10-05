import pandas as pd
import numpy as np


# ==========================================
# Pocket Option Signal Engine
# ZigZag + Keltner Channel + Stochastic
# ==========================================

def calculate_indicators(df):
    df = df.copy()

    # Keltner Channel
    df["ema"] = df["close"].ewm(span=20, adjust=False).mean()

    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift(1))
    low_close = abs(df["low"] - df["close"].shift(1))

    tr = pd.concat(
        [high_low, high_close, low_close],
        axis=1
    ).max(axis=1)

    df["atr"] = tr.rolling(10).mean()

    df["upper"] = df["ema"] + (2 * df["atr"])
    df["lower"] = df["ema"] - (2 * df["atr"])

    # Stochastic Oscillator
    lowest_low = df["low"].rolling(14).min()
    highest_high = df["high"].rolling(14).max()

    denominator = highest_high - lowest_low

    df["%K"] = np.where(
        denominator != 0,
        100 * (df["close"] - lowest_low) / denominator,
        50
    )

    df["%D"] = pd.Series(df["%K"], index=df.index).rolling(3).mean()

    # ZigZag-style swing detection
    df["swing_high"] = (
        (df["high"] > df["high"].shift(1)) &
        (df["high"] > df["high"].shift(-1))
    )

    df["swing_low"] = (
        (df["low"] < df["low"].shift(1)) &
        (df["low"] < df["low"].shift(-1))
    )

    return df


def analyze_signal(df):
    df = calculate_indicators(df)

    if len(df) < 20:
        return {
            "signal": "WAIT",
            "confidence": 0,
            "call_score": 0,
            "put_score": 0
        }

    last = df.iloc[-1]

    call_score = 0
    put_score = 0

    # --------------------------
    # Keltner Channel
    # --------------------------

    if last["close"] <= last["lower"]:
        call_score += 1

    if last["close"] >= last["upper"]:
        put_score += 1

    # --------------------------
    # Stochastic
    # --------------------------

    if last["%K"] < 20 and last["%K"] > last["%D"]:
        call_score += 1

    if last["%K"] > 80 and last["%K"] < last["%D"]:
        put_score += 1

    # --------------------------
    # ZigZag
    # --------------------------

    if bool(last["swing_low"]):
        call_score += 1

    if bool(last["swing_high"]):
        put_score += 1

    # --------------------------
    # Signal decision
    # --------------------------

    total = call_score + put_score

    if total == 0:
        return {
            "signal": "WAIT",
            "confidence": 0,
            "call_score": call_score,
            "put_score": put_score
        }

    if call_score >= 2 and call_score > put_score:
        confidence = round((call_score / 3) * 100)

        return {
            "signal": "CALL",
            "confidence": confidence,
            "call_score": call_score,
            "put_score": put_score
        }

    if put_score >= 2 and put_score > call_score:
        confidence = round((put_score / 3) * 100)

        return {
            "signal": "PUT",
            "confidence": confidence,
            "call_score": call_score,
            "put_score": put_score
        }

    return {
        "signal": "WAIT",
        "confidence": 0,
        "call_score": call_score,
        "put_score": put_score
    }


def generate_signal(df):
    result = analyze_signal(df)
    return result["signal"]


if __name__ == "__main__":
    print("Pocket Option Signal Engine")
    print("ZigZag + Keltner Channel + Stochastic")
    print("Waiting for market candle data...")
