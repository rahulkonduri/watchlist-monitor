import numpy as np
import pandas as pd
from typing import Optional


def wilder_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI using Wilder's smoothing method (alpha = 1/period)."""
    if len(prices) < period + 1:
        return pd.Series(np.nan, index=prices.index)

    delta = prices.diff()
    gains = delta.clip(lower=0).values
    losses = (-delta).clip(lower=0).values

    n = len(prices)
    avg_g = np.full(n, np.nan)
    avg_l = np.full(n, np.nan)

    # Seed: simple mean of first `period` non-NaN changes (indices 1..period)
    avg_g[period] = gains[1 : period + 1].mean()
    avg_l[period] = losses[1 : period + 1].mean()

    # Wilder's smoothing for subsequent bars
    for i in range(period + 1, n):
        avg_g[i] = (avg_g[i - 1] * (period - 1) + gains[i]) / period
        avg_l[i] = (avg_l[i - 1] * (period - 1) + losses[i]) / period

    # Build RS; treat both-zero (flat prices) as undefined
    both_zero = (avg_g == 0) & (avg_l == 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(both_zero, np.nan, np.where(avg_l == 0, np.inf, avg_g / avg_l))

    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi[:period] = np.nan

    return pd.Series(rsi, index=prices.index)


def sma(prices: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return prices.rolling(window=period).mean()


def daily_pct_change(prices: pd.Series) -> pd.Series:
    """Percent change from previous close."""
    return prices.pct_change() * 100.0


def ma_crossover(prices: pd.Series, short_period: int, long_period: int) -> Optional[str]:
    """
    Detect a moving-average crossover on the latest bar.

    Returns 'golden' if the short SMA crossed above the long SMA on the most
    recent bar, 'death' if it crossed below, or None if no crossover occurred.
    """
    short_ma = sma(prices, short_period)
    long_ma = sma(prices, long_period)

    combined = pd.DataFrame({"short": short_ma, "long": long_ma}).dropna()
    if len(combined) < 2:
        return None

    prev = combined.iloc[-2]
    curr = combined.iloc[-1]

    if prev["short"] <= prev["long"] and curr["short"] > curr["long"]:
        return "golden"
    if prev["short"] >= prev["long"] and curr["short"] < curr["long"]:
        return "death"
    return None
