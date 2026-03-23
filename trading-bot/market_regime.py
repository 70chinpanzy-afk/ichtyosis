"""Market Regime Detection — Trending vs Ranging filter.

Uses ADX (Average Directional Index) to determine if the market
is trending or ranging. Chart patterns are more reliable in trending markets.

ADX > 25: Trending → patterns are more likely to follow through
ADX < 20: Ranging → patterns frequently fail, skip trading
ADX 20-25: Transitional → trade with caution (lower confidence)
"""

import numpy as np
import pandas as pd


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ADX (Average Directional Index)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # +DM and -DM
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Smoothed (Wilder's method)
    atr = tr.rolling(window=period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

    # DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()

    return adx


def detect_regime(df: pd.DataFrame, period: int = 14) -> dict:
    """Detect current market regime.

    Returns:
        dict with:
            regime: "trending" | "ranging" | "transitional"
            adx: current ADX value
            trend_direction: "up" | "down" | "none"
            confidence_modifier: float to multiply signal confidence by
    """
    adx = calculate_adx(df, period)
    current_adx = adx.iloc[-1]

    if np.isnan(current_adx):
        return {
            "regime": "unknown",
            "adx": 0,
            "trend_direction": "none",
            "confidence_modifier": 0.8,
        }

    # Trend direction from EMA
    ema20 = df["close"].ewm(span=20, adjust=False).mean()
    ema50 = df["close"].ewm(span=50, adjust=False).mean()
    price = df["close"].iloc[-1]

    if price > ema20.iloc[-1] > ema50.iloc[-1]:
        trend_dir = "up"
    elif price < ema20.iloc[-1] < ema50.iloc[-1]:
        trend_dir = "down"
    else:
        trend_dir = "none"

    if current_adx >= 25:
        regime = "trending"
        modifier = 1.0  # Full confidence
    elif current_adx >= 20:
        regime = "transitional"
        modifier = 0.85  # Slight reduction
    else:
        regime = "ranging"
        modifier = 0.6  # Significant reduction (patterns less reliable)

    return {
        "regime": regime,
        "adx": round(float(current_adx), 1),
        "trend_direction": trend_dir,
        "confidence_modifier": modifier,
    }


if __name__ == "__main__":
    from data_fetcher import fetch_ohlcv

    for symbol in ["BTC/USDT", "ETH/USDT", "SOL/USDT"]:
        df = fetch_ohlcv(symbol=symbol, limit=100)
        regime = detect_regime(df)
        print(f"{symbol}: {regime['regime']} (ADX={regime['adx']}, "
              f"trend={regime['trend_direction']}, modifier={regime['confidence_modifier']})")
