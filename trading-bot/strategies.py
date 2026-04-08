"""Numerical Trading Strategies — no API calls, pure price action.

Three strategies that complement each other:
  1. TrendFollowing: EMA crossover + ADX + RSI (works in trending markets)
  2. MeanReversion: Bollinger Bands + RSI extremes (works in ranging markets)
  3. Breakout: Donchian channel breakout + volume (catches new trends early)

Usage:
    from strategies import run_all_strategies, TrendFollowingStrategy
    signals = run_all_strategies(df)
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backtester import calculate_atr, calculate_ema
from market_regime import calculate_adx


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    direction: str        # "long" | "short"
    strength: float       # 0.0 - 1.0
    entry_price: float
    stop_loss: float
    take_profit: float
    strategy_name: str
    reasoning: str


# ---------------------------------------------------------------------------
# Indicator helpers
# ---------------------------------------------------------------------------

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _bollinger_bands(series: pd.Series, period: int = 20,
                     num_std: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper, middle, lower) Bollinger Bands."""
    middle = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def _donchian(df: pd.DataFrame, period: int = 20) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper, middle, lower) Donchian channels."""
    upper = df["high"].rolling(period).max()
    lower = df["low"].rolling(period).min()
    middle = (upper + lower) / 2
    return upper, middle, lower


def _macd(series: pd.Series, fast: int = 12, slow: int = 26,
          signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# ---------------------------------------------------------------------------
# Strategy 1: Trend Following
# ---------------------------------------------------------------------------

class TrendFollowingStrategy:
    """EMA crossover confirmed by ADX and RSI.

    - Long:  EMA fast > EMA slow, ADX > threshold, 40 < RSI < 70
    - Short: EMA fast < EMA slow, ADX > threshold, 30 < RSI < 60
    - SL/TP: ATR-based with 1.5:3.0 risk/reward
    """

    name = "trend_following"

    def __init__(self, ema_fast: int = 20, ema_slow: int = 50,
                 adx_threshold: int = 30, rsi_period: int = 14,
                 atr_sl_mult: float = 2.0, atr_tp_mult: float = 4.0):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.adx_threshold = adx_threshold
        self.rsi_period = rsi_period
        self.atr_sl_mult = atr_sl_mult
        self.atr_tp_mult = atr_tp_mult

    def generate_signal(self, df: pd.DataFrame) -> "Signal | None":
        if len(df) < self.ema_slow + 20:
            return None

        close = df["close"]
        ema_f = calculate_ema(close, self.ema_fast)
        ema_s = calculate_ema(close, self.ema_slow)
        adx = calculate_adx(df)
        rsi = _rsi(close, self.rsi_period)
        atr = calculate_atr(df)
        macd_line, macd_signal, macd_hist = _macd(close)

        current_adx = adx.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]
        current_price = close.iloc[-1]

        if np.isnan(current_adx) or np.isnan(current_atr) or current_atr <= 0:
            return None

        # ADX must confirm trend
        if current_adx < self.adx_threshold:
            return None

        # EMA crossover detection (within last 3 bars for freshness)
        ema_diff = ema_f - ema_s
        cross_long = (ema_diff.iloc[-1] > 0 and ema_diff.iloc[-4:-1].min() <= 0)
        cross_short = (ema_diff.iloc[-1] < 0 and ema_diff.iloc[-4:-1].max() >= 0)

        # Also allow existing trend if MACD confirms
        trending_long = (ema_diff.iloc[-1] > 0 and macd_hist.iloc[-1] > 0
                         and macd_hist.iloc[-2] <= 0)
        trending_short = (ema_diff.iloc[-1] < 0 and macd_hist.iloc[-1] < 0
                          and macd_hist.iloc[-2] >= 0)

        direction = None
        if (cross_long or trending_long) and 40 < current_rsi < 70:
            direction = "long"
        elif (cross_short or trending_short) and 30 < current_rsi < 60:
            direction = "short"

        if direction is None:
            return None

        # Calculate strength based on ADX and RSI alignment
        adx_score = min((current_adx - self.adx_threshold) / 25, 1.0)
        rsi_score = 1.0 - abs(current_rsi - 50) / 50  # Best near 50
        macd_score = min(abs(macd_hist.iloc[-1]) / (current_atr * 0.1), 1.0)
        strength = 0.4 * adx_score + 0.3 * rsi_score + 0.3 * macd_score
        strength = max(0.1, min(strength, 1.0))

        if direction == "long":
            sl = current_price - current_atr * self.atr_sl_mult
            tp = current_price + current_atr * self.atr_tp_mult
        else:
            sl = current_price + current_atr * self.atr_sl_mult
            tp = current_price - current_atr * self.atr_tp_mult

        return Signal(
            direction=direction,
            strength=round(strength, 2),
            entry_price=current_price,
            stop_loss=round(sl, 2),
            take_profit=round(tp, 2),
            strategy_name=self.name,
            reasoning=(f"EMA{self.ema_fast}/{self.ema_slow} {'cross' if (cross_long or cross_short) else 'trend'}"
                       f" | ADX={current_adx:.0f} RSI={current_rsi:.0f}"
                       f" | MACD hist={'+'if macd_hist.iloc[-1]>0 else ''}{macd_hist.iloc[-1]:.2f}"),
        )


# ---------------------------------------------------------------------------
# Strategy 2: Mean Reversion
# ---------------------------------------------------------------------------

class MeanReversionStrategy:
    """Bollinger Band bounce with RSI confirmation.

    - Long:  Price at/below lower BB + RSI < oversold
    - Short: Price at/above upper BB + RSI > overbought
    - Only active when ADX < 25 (ranging market)
    - TP at middle BB (mean), SL beyond opposite band
    """

    name = "mean_reversion"

    def __init__(self, bb_period: int = 20, bb_std: float = 2.5,
                 rsi_period: int = 14, rsi_oversold: int = 25,
                 rsi_overbought: int = 75, adx_max: int = 22,
                 atr_sl_mult: float = 2.5):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.adx_max = adx_max
        self.atr_sl_mult = atr_sl_mult

    def generate_signal(self, df: pd.DataFrame) -> "Signal | None":
        if len(df) < self.bb_period + 20:
            return None

        close = df["close"]
        upper, middle, lower = _bollinger_bands(close, self.bb_period, self.bb_std)
        rsi = _rsi(close, self.rsi_period)
        adx = calculate_adx(df)
        atr = calculate_atr(df)

        current_price = close.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_adx = adx.iloc[-1]
        current_atr = atr.iloc[-1]
        current_upper = upper.iloc[-1]
        current_middle = middle.iloc[-1]
        current_lower = lower.iloc[-1]

        if np.isnan(current_adx) or np.isnan(current_atr) or current_atr <= 0:
            return None

        # Only trade in ranging markets
        if current_adx >= self.adx_max:
            return None

        direction = None
        # Long: price touches or pierces lower BB + RSI oversold
        if current_price <= current_lower and current_rsi < self.rsi_oversold:
            direction = "long"
        # Short: price touches or pierces upper BB + RSI overbought
        elif current_price >= current_upper and current_rsi > self.rsi_overbought:
            direction = "short"

        if direction is None:
            return None

        # Strength based on how extreme the position is
        if direction == "long":
            bb_penetration = (current_lower - current_price) / current_atr
            rsi_extreme = (self.rsi_oversold - current_rsi) / self.rsi_oversold
        else:
            bb_penetration = (current_price - current_upper) / current_atr
            rsi_extreme = (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)

        strength = 0.5 + 0.25 * min(bb_penetration, 1.0) + 0.25 * min(rsi_extreme, 1.0)
        strength = max(0.1, min(strength, 1.0))

        if direction == "long":
            sl = current_price - current_atr * self.atr_sl_mult
            tp = current_middle  # Revert to mean
        else:
            sl = current_price + current_atr * self.atr_sl_mult
            tp = current_middle

        return Signal(
            direction=direction,
            strength=round(strength, 2),
            entry_price=current_price,
            stop_loss=round(sl, 2),
            take_profit=round(tp, 2),
            strategy_name=self.name,
            reasoning=(f"BB {'lower' if direction == 'long' else 'upper'} touch"
                       f" | RSI={current_rsi:.0f} | ADX={current_adx:.0f} (ranging)"
                       f" | TP=middle BB ¥{current_middle:,.0f}"),
        )


# ---------------------------------------------------------------------------
# Strategy 3: Breakout
# ---------------------------------------------------------------------------

class BreakoutStrategy:
    """Donchian channel breakout with volume confirmation.

    - Long:  Close above upper Donchian + volume spike
    - Short: Close below lower Donchian + volume spike
    - Catches the beginning of new trends
    """

    name = "breakout"

    def __init__(self, donchian_period: int = 30, volume_mult: float = 2.0,
                 atr_sl_mult: float = 2.0, atr_tp_mult: float = 4.0):
        self.donchian_period = donchian_period
        self.volume_mult = volume_mult
        self.atr_sl_mult = atr_sl_mult
        self.atr_tp_mult = atr_tp_mult

    def generate_signal(self, df: pd.DataFrame) -> "Signal | None":
        if len(df) < self.donchian_period + 10:
            return None

        close = df["close"]
        volume = df["volume"]
        atr = calculate_atr(df)

        # Donchian channels (use [:-1] to avoid lookahead - channel based on previous bars)
        prev_df = df.iloc[:-1]
        upper = prev_df["high"].rolling(self.donchian_period).max().iloc[-1]
        lower = prev_df["low"].rolling(self.donchian_period).min().iloc[-1]
        mid = (upper + lower) / 2

        current_price = close.iloc[-1]
        current_atr = atr.iloc[-1]
        avg_volume = volume.iloc[-self.donchian_period - 1:-1].mean()
        current_volume = volume.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0 or np.isnan(upper):
            return None

        # Volume confirmation
        volume_confirmed = current_volume > avg_volume * self.volume_mult

        direction = None
        if current_price > upper and volume_confirmed:
            direction = "long"
        elif current_price < lower and volume_confirmed:
            direction = "short"

        if direction is None:
            return None

        # Strength based on breakout magnitude and volume
        if direction == "long":
            breakout_size = (current_price - upper) / current_atr
        else:
            breakout_size = (lower - current_price) / current_atr

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        strength = 0.3 + 0.35 * min(breakout_size, 1.0) + 0.35 * min((volume_ratio - 1) / 2, 1.0)
        strength = max(0.1, min(strength, 1.0))

        if direction == "long":
            sl = mid  # SL at channel midpoint
            tp = current_price + current_atr * self.atr_tp_mult
        else:
            sl = mid
            tp = current_price - current_atr * self.atr_tp_mult

        return Signal(
            direction=direction,
            strength=round(strength, 2),
            entry_price=current_price,
            stop_loss=round(sl, 2),
            take_profit=round(tp, 2),
            strategy_name=self.name,
            reasoning=(f"Donchian {self.donchian_period} {'upper' if direction == 'long' else 'lower'} breakout"
                       f" | Volume {volume_ratio:.1f}x avg"
                       f" | Breakout size {breakout_size:.1f}x ATR"),
        )


# ---------------------------------------------------------------------------
# Composite runner
# ---------------------------------------------------------------------------

ALL_STRATEGIES = [
    TrendFollowingStrategy(),
    MeanReversionStrategy(),
    BreakoutStrategy(),
]


def run_all_strategies(df: pd.DataFrame,
                       strategies: list = None) -> list[Signal]:
    """Evaluate all strategies and return list of signals."""
    if strategies is None:
        strategies = ALL_STRATEGIES

    signals = []
    for strat in strategies:
        sig = strat.generate_signal(df)
        if sig is not None:
            signals.append(sig)
    return signals


def select_best_signal(signals: list[Signal]) -> "Signal | None":
    """Select the best signal when multiple strategies fire.

    Rules:
    - If multiple strategies agree on direction: average strength, tightest SL
    - If strategies disagree: only trade if one is strong (>0.7) with no strong opposition
    - If all agree: boost strength by 10%
    """
    if not signals:
        return None

    if len(signals) == 1:
        return signals[0]

    # Group by direction
    longs = [s for s in signals if s.direction == "long"]
    shorts = [s for s in signals if s.direction == "short"]

    # All agree
    if len(longs) == len(signals):
        best = max(longs, key=lambda s: s.strength)
        tightest_sl = max(s.stop_loss for s in longs)  # Highest SL = tightest for long
        avg_strength = min(sum(s.strength for s in longs) / len(longs) * 1.1, 1.0)
        return Signal(
            direction="long",
            strength=round(avg_strength, 2),
            entry_price=best.entry_price,
            stop_loss=tightest_sl,
            take_profit=best.take_profit,
            strategy_name="+".join(s.strategy_name for s in longs),
            reasoning=" | ".join(s.reasoning for s in longs),
        )

    if len(shorts) == len(signals):
        best = max(shorts, key=lambda s: s.strength)
        tightest_sl = min(s.stop_loss for s in shorts)  # Lowest SL = tightest for short
        avg_strength = min(sum(s.strength for s in shorts) / len(shorts) * 1.1, 1.0)
        return Signal(
            direction="short",
            strength=round(avg_strength, 2),
            entry_price=best.entry_price,
            stop_loss=tightest_sl,
            take_profit=best.take_profit,
            strategy_name="+".join(s.strategy_name for s in shorts),
            reasoning=" | ".join(s.reasoning for s in shorts),
        )

    # Disagreement: only trade if one side is clearly stronger
    long_strength = max((s.strength for s in longs), default=0)
    short_strength = max((s.strength for s in shorts), default=0)

    if long_strength > 0.7 and short_strength < 0.5:
        return max(longs, key=lambda s: s.strength)
    if short_strength > 0.7 and long_strength < 0.5:
        return max(shorts, key=lambda s: s.strength)

    # No clear winner — skip
    return None


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from data_fetcher import fetch_ohlcv
    from config import SYMBOLS

    for symbol in SYMBOLS:
        df = fetch_ohlcv(symbol=symbol, timeframe="4h", limit=200)
        signals = run_all_strategies(df)
        if signals:
            best = select_best_signal(signals)
            if best:
                print(f"\n{symbol}: {best.direction.upper()} (strength={best.strength})")
                print(f"  Strategy: {best.strategy_name}")
                print(f"  Entry: ${best.entry_price:,.2f} | SL: ${best.stop_loss:,.2f} | TP: ${best.take_profit:,.2f}")
                print(f"  {best.reasoning}")
            else:
                print(f"\n{symbol}: Conflicting signals — skip")
                for s in signals:
                    print(f"  {s.strategy_name}: {s.direction} ({s.strength})")
        else:
            print(f"\n{symbol}: No signal")
