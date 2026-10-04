import pandas as pd
import numpy as np


# ==============================
# Pocket Option Signal Engine
# Indicators:
# - ZigZag
# - Keltner Channel
# - Stochastic Oscillator
# ==============================

def calculate_indicators(df):
    df = df.copy()

    # EMA for Keltner Channel
    df["ema"] = df["close"].ewm(span=20, adjust=False).mean()

    # ATR
    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift(1))
    low_close = abs(df["low"] - df["close"].shift(1))

    tr = pd.concat(
        [high_low, high_close, low_close],
        axis=1
    ).max(axis=1)

    df["atr"] = tr.rolling(10).mean()

    # Keltner Channel
    df["upper"] = df["ema"] + (2 * df["atr"])
    df["lower"] = df["ema"] - (2 * df["atr"])

    # Stochastic Oscillator
    lowest_low = df["low"].rolling(14).min()
    highest_high = df["high"].rolling(14).max()

    df["%K"] = (
        100 * (df["close"] - lowest_low) /
        (highest_high - lowest_low)
    )

    df["%D"] = df["%K"].rolling(3).mean()

    # Simple ZigZag-style swing detection
    df["swing_high"] = (
        (df["high"] > df["high"].shift(1)) &
        (df["high"] > df["high"].shift(-1))
    )

    df["swing_low"] = (
        (df["low"] < df["low"].shift(1)) &
        (df["low"] < df["low"].shift(-1))
    )

    return df


def generate_signal(df):
    df = calculate_indicators(df)

    last = df.iloc[-1]

    call_score = 0
    put_score = 0

    # Keltner Channel
    if last["close"] <= last["lower"]:
        call_score += 1

    if last["close"] >= last["upper"]:
        put_score += 1

    # Stochastic
    if last["%K"] < 20 and last["%K"] > last["%D"]:
        call_score += 1

    if last["%K"] > 80 and last["%K"] < last["%D"]:
        put_score += 1

    # ZigZag-style reversal
    if last["swing_low"]:
        call_score += 1

    if last["swing_high"]:
        put_score += 1

    # Require confirmation from multiple conditions
    if call_score >= 2 and call_score > put_score:
        return "CALL"

    if put_score >= 2 and put_score > call_score:
        return "PUT"

    return "WAIT"


if __name__ == "__main__":
    print("Pocket Option Signal Engine")
    print("ZigZag + Keltner Channel + Stochastic")
    print("Waiting for market candle data...")
