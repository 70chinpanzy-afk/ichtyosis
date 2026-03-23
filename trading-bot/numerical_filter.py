"""Numerical pre-filter to detect potential chart pattern candidates.

This reduces Gemini API calls by ~90% by filtering out windows
that clearly don't contain any recognizable pattern.
"""

import numpy as np
import pandas as pd
from config import PREFILTER_MIN_SWING_PCT, PREFILTER_LOOKBACK


def find_swing_points(df: pd.DataFrame, order: int = 5) -> tuple[list, list]:
    """Find local swing highs and lows."""
    highs = []
    lows = []
    high_vals = df["high"].values
    low_vals = df["low"].values

    for i in range(order, len(df) - order):
        # Swing high: higher than `order` bars on each side
        if all(high_vals[i] >= high_vals[i - j] for j in range(1, order + 1)) and \
           all(high_vals[i] >= high_vals[i + j] for j in range(1, order + 1)):
            highs.append((i, high_vals[i]))

        # Swing low: lower than `order` bars on each side
        if all(low_vals[i] <= low_vals[i - j] for j in range(1, order + 1)) and \
           all(low_vals[i] <= low_vals[i + j] for j in range(1, order + 1)):
            lows.append((i, low_vals[i]))

    return highs, lows


def has_double_bottom_candidate(lows: list, price: float, min_swing_pct: float) -> bool:
    """Check if there are two similar swing lows (potential double bottom)."""
    if len(lows) < 2:
        return False
    min_diff = price * min_swing_pct / 100
    for i in range(len(lows) - 1):
        for j in range(i + 1, len(lows)):
            if abs(lows[i][1] - lows[j][1]) < min_diff:
                # Check separation (at least 10 bars apart)
                if abs(lows[i][0] - lows[j][0]) >= 10:
                    return True
    return False


def has_double_top_candidate(highs: list, price: float, min_swing_pct: float) -> bool:
    """Check if there are two similar swing highs (potential double top)."""
    if len(highs) < 2:
        return False
    min_diff = price * min_swing_pct / 100
    for i in range(len(highs) - 1):
        for j in range(i + 1, len(highs)):
            if abs(highs[i][1] - highs[j][1]) < min_diff:
                if abs(highs[i][0] - highs[j][0]) >= 10:
                    return True
    return False


def has_head_and_shoulders_candidate(highs: list) -> bool:
    """Check for three swing highs where middle is highest."""
    if len(highs) < 3:
        return False
    for i in range(len(highs) - 2):
        h1, h2, h3 = highs[i][1], highs[i + 1][1], highs[i + 2][1]
        if h2 > h1 and h2 > h3:
            # Middle peak should be notably higher
            if h2 > h1 * 1.005 and h2 > h3 * 1.005:
                return True
    return False


def has_inv_head_and_shoulders_candidate(lows: list) -> bool:
    """Check for three swing lows where middle is lowest."""
    if len(lows) < 3:
        return False
    for i in range(len(lows) - 2):
        l1, l2, l3 = lows[i][1], lows[i + 1][1], lows[i + 2][1]
        if l2 < l1 and l2 < l3:
            if l2 < l1 * 0.995 and l2 < l3 * 0.995:
                return True
    return False


def has_triangle_candidate(highs: list, lows: list) -> str | None:
    """Check for ascending/descending triangle patterns."""
    if len(highs) < 2 or len(lows) < 2:
        return None

    # Ascending: flat highs + rising lows
    high_vals = [h[1] for h in highs[-3:]]
    low_vals = [l[1] for l in lows[-3:]]

    high_range = (max(high_vals) - min(high_vals)) / max(high_vals)
    low_range = (max(low_vals) - min(low_vals)) / max(low_vals) if low_vals else 0

    if high_range < 0.01 and len(low_vals) >= 2 and low_vals[-1] > low_vals[0]:
        return "ascending_triangle"
    if low_range < 0.01 and len(high_vals) >= 2 and high_vals[-1] < high_vals[0]:
        return "descending_triangle"

    return None


def prefilter_window(df_window: pd.DataFrame) -> list[str]:
    """Run all numerical filters on a window and return candidate pattern names."""
    candidates = []
    price = df_window["close"].iloc[-1]
    highs, lows = find_swing_points(df_window, order=5)

    if has_double_bottom_candidate(lows, price, PREFILTER_MIN_SWING_PCT):
        candidates.append("double_bottom")
    if has_double_top_candidate(highs, price, PREFILTER_MIN_SWING_PCT):
        candidates.append("double_top")
    if has_head_and_shoulders_candidate(highs):
        candidates.append("head_and_shoulders")
    if has_inv_head_and_shoulders_candidate(lows):
        candidates.append("inverse_head_and_shoulders")

    triangle = has_triangle_candidate(highs, lows)
    if triangle:
        candidates.append(triangle)

    return candidates
