"""Backtesting engine with ATR-based risk management."""

import numpy as np
import pandas as pd
from config import (
    INITIAL_CAPITAL, POSITION_SIZE_PCT, ATR_PERIOD,
    ATR_SL_MULTIPLIER, ATR_TP_MULTIPLIER, COMMISSION_PCT,
    CHART_WINDOW_SIZE,
)


def calculate_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    """Calculate Average True Range."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return tr.rolling(window=period).mean()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def run_backtest(df: pd.DataFrame, signals: list[dict],
                 initial_capital: float = INITIAL_CAPITAL,
                 min_confidence: float = 0.80,
                 sl_mult: float = None,
                 tp_mult: float = None,
                 commission: float = None,
                 use_ema_filter: bool = True,
                 dedup_signals: bool = True) -> tuple:
    """Run backtest with optional EMA trend filter and fixed SL/TP.

    Strategy:
    - Optional EMA50 trend filter: only trade patterns aligned with trend
    - Fixed SL/TP based on ATR multiples
    - Opposite-direction signals close current position
    - Optional deduplication of consecutive same-direction signals
    """
    if sl_mult is None:
        sl_mult = ATR_SL_MULTIPLIER
    if tp_mult is None:
        tp_mult = ATR_TP_MULTIPLIER
    if commission is None:
        commission = COMMISSION_PCT

    atr = calculate_atr(df)
    ema50 = calculate_ema(df["close"], 50) if use_ema_filter else None
    trades = []
    capital = initial_capital
    position = None
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0

    # Build signal lookup
    signal_map = {}
    last_direction = None
    for sig in sorted(signals, key=lambda s: s.get("start_index", 0)):
        if sig.get("pattern", "none") != "none" and sig.get("confidence", 0) >= min_confidence:
            direction = sig.get("direction", "none")
            if dedup_signals and direction == last_direction:
                continue
            last_direction = direction
            bar_idx = sig["start_index"] + CHART_WINDOW_SIZE - 1
            if bar_idx < len(df):
                signal_map[bar_idx] = sig

    equity_curve = []

    for i in range(len(df)):
        current_price = df["close"].iloc[i]
        current_high = df["high"].iloc[i]
        current_low = df["low"].iloc[i]
        current_atr = atr.iloc[i] if not np.isnan(atr.iloc[i]) else 0

        # Check SL/TP for open positions
        if position == "long":
            if current_low <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * capital * POSITION_SIZE_PCT
                pnl -= abs(pnl) * commission
                capital += pnl
                trades.append({
                    "entry_time": entry_time, "exit_time": df.index[i],
                    "direction": "long", "entry_price": entry_price,
                    "exit_price": stop_loss, "pnl": pnl,
                    "exit_reason": "stop_loss", "capital_after": capital,
                })
                position = None
            elif current_high >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * capital * POSITION_SIZE_PCT
                pnl -= abs(pnl) * commission
                capital += pnl
                trades.append({
                    "entry_time": entry_time, "exit_time": df.index[i],
                    "direction": "long", "entry_price": entry_price,
                    "exit_price": take_profit, "pnl": pnl,
                    "exit_reason": "take_profit", "capital_after": capital,
                })
                position = None

        elif position == "short":
            if current_high >= stop_loss:
                pnl = (entry_price - stop_loss) / entry_price * capital * POSITION_SIZE_PCT
                pnl -= abs(pnl) * commission
                capital += pnl
                trades.append({
                    "entry_time": entry_time, "exit_time": df.index[i],
                    "direction": "short", "entry_price": entry_price,
                    "exit_price": stop_loss, "pnl": pnl,
                    "exit_reason": "stop_loss", "capital_after": capital,
                })
                position = None
            elif current_low <= take_profit:
                pnl = (entry_price - take_profit) / entry_price * capital * POSITION_SIZE_PCT
                pnl -= abs(pnl) * commission
                capital += pnl
                trades.append({
                    "entry_time": entry_time, "exit_time": df.index[i],
                    "direction": "short", "entry_price": entry_price,
                    "exit_price": take_profit, "pnl": pnl,
                    "exit_reason": "take_profit", "capital_after": capital,
                })
                position = None

        # Check for new signal
        if i in signal_map:
            sig = signal_map[i]
            direction = sig["direction"]
            # EMA trend filter (optional)
            if use_ema_filter and ema50 is not None:
                current_ema50 = ema50.iloc[i] if not np.isnan(ema50.iloc[i]) else 0
                trend_aligned = False
                if direction == "long" and current_price > current_ema50:
                    trend_aligned = True
                elif direction == "short" and current_price < current_ema50:
                    trend_aligned = True
            else:
                trend_aligned = True

            if trend_aligned and current_atr > 0:
                # Close opposite position (reversal)
                if position is not None and position != direction:
                    if position == "long":
                        pnl = (current_price - entry_price) / entry_price * capital * POSITION_SIZE_PCT
                    else:
                        pnl = (entry_price - current_price) / entry_price * capital * POSITION_SIZE_PCT
                    pnl -= abs(pnl) * commission
                    capital += pnl
                    trades.append({
                        "entry_time": entry_time, "exit_time": df.index[i],
                        "direction": position, "entry_price": entry_price,
                        "exit_price": current_price, "pnl": pnl,
                        "exit_reason": "reversal", "capital_after": capital,
                    })
                    position = None

                # Open new position
                if position is None:
                    position = direction
                    entry_price = current_price
                    entry_time = df.index[i]
                    if direction == "long":
                        stop_loss = entry_price - current_atr * sl_mult
                        take_profit = entry_price + current_atr * tp_mult
                    else:
                        stop_loss = entry_price + current_atr * sl_mult
                        take_profit = entry_price - current_atr * tp_mult

        equity_curve.append({"timestamp": df.index[i], "equity": capital})

    # Close remaining position
    if position is not None:
        last_price = df["close"].iloc[-1]
        if position == "long":
            pnl = (last_price - entry_price) / entry_price * capital * POSITION_SIZE_PCT
        else:
            pnl = (entry_price - last_price) / entry_price * capital * POSITION_SIZE_PCT
        pnl -= abs(pnl) * commission
        capital += pnl
        trades.append({
            "entry_time": entry_time, "exit_time": df.index[-1],
            "direction": position, "entry_price": entry_price,
            "exit_price": last_price, "pnl": pnl,
            "exit_reason": "end_of_data", "capital_after": capital,
        })

    trade_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    equity_df = pd.DataFrame(equity_curve)

    return trade_df, equity_df


def compute_stats(trade_df: pd.DataFrame, equity_df: pd.DataFrame,
                  initial_capital: float = INITIAL_CAPITAL) -> dict:
    """Compute backtest performance statistics."""
    if trade_df.empty:
        return {"total_trades": 0, "message": "No trades executed"}

    total_trades = len(trade_df)
    winning = trade_df[trade_df["pnl"] > 0]
    losing = trade_df[trade_df["pnl"] <= 0]

    win_rate = len(winning) / total_trades * 100
    avg_win = winning["pnl"].mean() if len(winning) > 0 else 0
    avg_loss = abs(losing["pnl"].mean()) if len(losing) > 0 else 0
    profit_factor = (winning["pnl"].sum() / abs(losing["pnl"].sum())) if len(losing) > 0 and losing["pnl"].sum() != 0 else float("inf")

    final_capital = equity_df["equity"].iloc[-1]
    total_return = (final_capital - initial_capital) / initial_capital * 100

    equity_series = equity_df["equity"]
    peak = equity_series.expanding().max()
    drawdown = (equity_series - peak) / peak * 100
    max_drawdown = drawdown.min()

    if len(equity_df) > 1:
        returns = equity_series.pct_change().dropna()
        periods_per_year = 365 * 24 / 4
        sharpe = returns.mean() / returns.std() * np.sqrt(periods_per_year) if returns.std() > 0 else 0
    else:
        sharpe = 0

    stats = {
        "total_trades": total_trades,
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": round(win_rate, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "total_return_pct": round(total_return, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 2),
        "initial_capital": initial_capital,
        "final_capital": round(final_capital, 2),
    }

    return stats
