"""Generate candlestick chart images with technical indicators overlay.

Indicators drawn on chart (visible to Gemini):
  - EMA 20 (yellow), EMA 50 (cyan), EMA 200 (magenta)
  - RSI (14) in lower panel
  - Volume bars with color-coding
"""

from pathlib import Path
import numpy as np
import mplfinance as mpf
import pandas as pd
from config import CHART_DIR, CHART_WINDOW_SIZE, CHART_SLIDE_STEP


def _calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI indicator."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_chart_image(df: pd.DataFrame, start_idx: int,
                         window_size: int = CHART_WINDOW_SIZE,
                         output_dir: Path = CHART_DIR,
                         symbol_prefix: str = "",
                         with_indicators: bool = True) -> Path | None:
    """Generate a candlestick chart image with optional indicators overlay.

    Indicators (when with_indicators=True):
      - EMA 20/50/200 on price panel
      - RSI 14 in separate panel
      - Volume with color coding

    Returns path to saved image, or None if not enough data.
    """
    end_idx = start_idx + window_size
    if end_idx > len(df):
        return None

    window = df.iloc[start_idx:end_idx].copy()

    if symbol_prefix:
        sub_dir = output_dir / symbol_prefix
        sub_dir.mkdir(exist_ok=True)
        filename = f"chart_{start_idx:05d}.png"
        filepath = sub_dir / filename
    else:
        filename = f"chart_{start_idx:05d}.png"
        filepath = output_dir / filename

    # Style: clean chart optimized for pattern recognition
    mc = mpf.make_marketcolors(
        up="#26a69a", down="#ef5350",
        edge="inherit", wick="inherit",
        volume="in",
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle="",
        y_on_right=True,
        rc={"figure.facecolor": "white", "axes.facecolor": "white"},
    )

    addplots = []

    if with_indicators:
        # EMA overlays on price panel
        # Calculate from the full slice to avoid NaN at edges
        lookback_start = max(0, start_idx - 200)
        extended = df.iloc[lookback_start:end_idx].copy()

        ema20_full = extended["close"].ewm(span=20, adjust=False).mean()
        ema50_full = extended["close"].ewm(span=50, adjust=False).mean()
        ema200_full = extended["close"].ewm(span=200, adjust=False).mean()

        # Trim to window
        offset = start_idx - lookback_start
        ema20 = ema20_full.iloc[offset:].values
        ema50 = ema50_full.iloc[offset:].values
        ema200 = ema200_full.iloc[offset:].values

        addplots.append(mpf.make_addplot(
            ema20, color="#FFD700", width=1.2, linestyle="-",
            panel=0, secondary_y=False))
        addplots.append(mpf.make_addplot(
            ema50, color="#00BFFF", width=1.5, linestyle="-",
            panel=0, secondary_y=False))
        addplots.append(mpf.make_addplot(
            ema200, color="#FF00FF", width=1.8, linestyle="--",
            panel=0, secondary_y=False))

        # RSI in separate panel
        rsi_full = _calculate_rsi(extended["close"], 14)
        rsi = rsi_full.iloc[offset:].values

        # RSI overbought/oversold reference lines
        rsi_70 = np.full(len(window), 70.0)
        rsi_30 = np.full(len(window), 30.0)

        addplots.append(mpf.make_addplot(
            rsi, color="#E040FB", width=1.2,
            panel=2, ylabel="RSI(14)", secondary_y=False))
        addplots.append(mpf.make_addplot(
            rsi_70, color="#888888", width=0.5, linestyle="--",
            panel=2, secondary_y=False))
        addplots.append(mpf.make_addplot(
            rsi_30, color="#888888", width=0.5, linestyle="--",
            panel=2, secondary_y=False))

    plot_kwargs = dict(
        type="candle",
        style=style,
        volume=True,
        savefig=dict(fname=str(filepath), dpi=100, bbox_inches="tight"),
        figscale=1.2,
        warn_too_much_data=9999,
    )
    if addplots:
        plot_kwargs["addplot"] = addplots
        plot_kwargs["panel_ratios"] = (4, 1, 1.5)  # price, volume, RSI

    mpf.plot(window, **plot_kwargs)

    return filepath


def generate_all_charts(df: pd.DataFrame, window_size: int = CHART_WINDOW_SIZE,
                        step: int = CHART_SLIDE_STEP,
                        symbol_prefix: str = "",
                        with_indicators: bool = True) -> list[tuple[int, Path]]:
    """Generate chart images by sliding window across the data.

    Returns list of (start_index, filepath) tuples.
    """
    charts = []
    total = (len(df) - window_size) // step + 1
    label = f" [{symbol_prefix}]" if symbol_prefix else ""

    for i, start_idx in enumerate(range(0, len(df) - window_size + 1, step)):
        filepath = generate_chart_image(df, start_idx, window_size,
                                        symbol_prefix=symbol_prefix,
                                        with_indicators=with_indicators)
        if filepath:
            charts.append((start_idx, filepath))
            if (i + 1) % 10 == 0:
                print(f"  {label} Generated {i + 1}/{total} charts")

    print(f"  {label} Generated {len(charts)} chart images total")
    return charts


if __name__ == "__main__":
    from data_fetcher import fetch_ohlcv
    df = fetch_ohlcv(limit=200)
    charts = generate_all_charts(df, with_indicators=True)
    print(f"Created {len(charts)} charts")
