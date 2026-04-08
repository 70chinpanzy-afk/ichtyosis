"""Backtester V2 — tests numerical strategies without any API calls.

Features:
  - Bar-by-bar simulation with trailing stops
  - Tests each strategy individually and combined
  - Walk-forward optimization
  - Multi-symbol portfolio testing
  - Outputs: win rate, profit factor, max drawdown, Sharpe ratio

Usage:
    python backtest_v2.py                           # All strategies, all symbols
    python backtest_v2.py --strategy trend          # Single strategy
    python backtest_v2.py --symbol BTC/USDT         # Single symbol
    python backtest_v2.py --walk-forward            # Walk-forward optimization
    python backtest_v2.py --timeframe 1h            # Different timeframe
"""

import argparse
import json
from itertools import product as iter_product
from pathlib import Path

import numpy as np
import pandas as pd

from data_fetcher import fetch_ohlcv
from strategies import (
    Signal, TrendFollowingStrategy, MeanReversionStrategy,
    BreakoutStrategy, run_all_strategies, select_best_signal,
)
from risk_manager import RiskManager
from backtester import calculate_atr, compute_stats
from config import SYMBOLS, RESULT_DIR


# ---------------------------------------------------------------------------
# Core backtester
# ---------------------------------------------------------------------------

class BacktesterV2:
    """Bar-by-bar backtester for numerical strategies."""

    def __init__(self,
                 strategies: list = None,
                 risk_manager=None,
                 initial_capital: float = 10000.0,
                 commission: float = 0.001,
                 trailing_stop: bool = True):
        self.strategies = strategies or [
            TrendFollowingStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
        ]
        self.rm = risk_manager or RiskManager()
        self.initial_capital = initial_capital
        self.commission = commission
        self.trailing_stop = trailing_stop

    def run(self, df: pd.DataFrame, symbol: str = "BTC/USDT") -> tuple[pd.DataFrame, pd.DataFrame]:
        """Run bar-by-bar backtest.

        Returns (trade_df, equity_df).
        """
        capital = self.initial_capital
        self.rm.update_peak(capital)
        position = None  # {direction, entry_price, sl, tp, size, highest, lowest, entry_time}
        trades = []
        equity = []

        # Need enough bars for indicator warmup
        warmup = 60

        for i in range(warmup, len(df)):
            current = df.iloc[i]
            current_price = current["close"]
            current_high = current["high"]
            current_low = current["low"]

            # --- Check SL/TP on open position ---
            if position is not None:
                closed, exit_price, reason = self._check_exit(
                    position, current_high, current_low, df.iloc[:i + 1])

                if closed:
                    pnl = self._calc_pnl(position, exit_price)
                    pnl -= abs(pnl) * self.commission
                    capital += pnl
                    self.rm.update_peak(capital)

                    trades.append({
                        "symbol": symbol,
                        "direction": position["direction"],
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "entry_time": position["entry_time"],
                        "exit_time": df.index[i],
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl / position["size"] * 100, 2) if position["size"] > 0 else 0,
                        "exit_reason": reason,
                        "capital_after": round(capital, 2),
                        "strategy": position.get("strategy", ""),
                    })
                    position = None

            # --- Generate signals ---
            if position is None:
                # Check risk limits
                can_trade, _ = self.rm.can_trade(capital, {})
                if not can_trade:
                    equity.append({"timestamp": df.index[i], "equity": capital})
                    continue

                window = df.iloc[:i + 1]
                signals = run_all_strategies(window, self.strategies)
                best = select_best_signal(signals)

                if best and best.strength >= 0.3:
                    size = self.rm.calculate_position_size(
                        capital, best.entry_price, best.stop_loss, symbol, {})
                    size = min(size, capital * 0.95)  # Keep some reserve

                    if size > 0:
                        position = {
                            "direction": best.direction,
                            "entry_price": best.entry_price,
                            "stop_loss": best.stop_loss,
                            "take_profit": best.take_profit,
                            "size": size,
                            "highest": best.entry_price,
                            "lowest": best.entry_price,
                            "entry_time": df.index[i],
                            "strategy": best.strategy_name,
                        }

            equity.append({"timestamp": df.index[i], "equity": capital})

        # Close remaining position at end
        if position is not None:
            exit_price = df["close"].iloc[-1]
            pnl = self._calc_pnl(position, exit_price)
            pnl -= abs(pnl) * self.commission
            capital += pnl
            trades.append({
                "symbol": symbol,
                "direction": position["direction"],
                "entry_price": position["entry_price"],
                "exit_price": exit_price,
                "entry_time": position["entry_time"],
                "exit_time": df.index[-1],
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl / position["size"] * 100, 2) if position["size"] > 0 else 0,
                "exit_reason": "end_of_data",
                "capital_after": round(capital, 2),
                "strategy": position.get("strategy", ""),
            })
            equity.append({"timestamp": df.index[-1], "equity": capital})

        trade_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        equity_df = pd.DataFrame(equity)
        return trade_df, equity_df

    def _check_exit(self, pos: dict, high: float, low: float,
                    df: pd.DataFrame) -> tuple[bool, float, str]:
        """Check SL/TP with optional trailing stop."""
        sl = pos["stop_loss"]
        tp = pos["take_profit"]

        if self.trailing_stop:
            atr = calculate_atr(df)
            current_atr = atr.iloc[-1] if not np.isnan(atr.iloc[-1]) else 0

            if pos["direction"] == "long":
                if high > pos["highest"]:
                    pos["highest"] = high
                    if current_atr > 0:
                        new_sl = high - current_atr * 1.5
                        if new_sl > sl:
                            pos["stop_loss"] = new_sl
                            sl = new_sl
            else:
                if low < pos["lowest"]:
                    pos["lowest"] = low
                    if current_atr > 0:
                        new_sl = low + current_atr * 1.5
                        if new_sl < sl:
                            pos["stop_loss"] = new_sl
                            sl = new_sl

        if pos["direction"] == "long":
            if low <= sl:
                return True, sl, "stop_loss"
            if high >= tp:
                return True, tp, "take_profit"
        else:
            if high >= sl:
                return True, sl, "stop_loss"
            if low <= tp:
                return True, tp, "take_profit"

        return False, 0, ""

    def _calc_pnl(self, pos: dict, exit_price: float) -> float:
        """Calculate PnL for a position."""
        if pos["direction"] == "long":
            return (exit_price - pos["entry_price"]) / pos["entry_price"] * pos["size"]
        else:
            return (pos["entry_price"] - exit_price) / pos["entry_price"] * pos["size"]


# ---------------------------------------------------------------------------
# Multi-symbol testing
# ---------------------------------------------------------------------------

def run_multi_symbol(symbols: list[str], timeframe: str = "4h",
                     limit: int = 1000, strategies: list = None,
                     initial_capital: float = 10000.0) -> dict:
    """Run backtests across multiple symbols."""
    results = {}
    total_trades = []

    for symbol in symbols:
        print(f"\n{'=' * 50}")
        print(f"Backtesting {symbol} ({timeframe})")
        print(f"{'=' * 50}")

        try:
            df = fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
        except Exception as e:
            print(f"  Failed to fetch data: {e}")
            continue

        bt = BacktesterV2(strategies=strategies, initial_capital=initial_capital)
        trade_df, equity_df = bt.run(df, symbol)

        if trade_df.empty:
            print(f"  No trades generated")
            results[symbol] = {"total_trades": 0}
            continue

        stats = compute_stats(trade_df, equity_df, initial_capital)
        results[symbol] = stats

        # Print summary
        print(f"  Trades: {stats['total_trades']} "
              f"({stats['winning_trades']}W/{stats['losing_trades']}L)")
        print(f"  Win Rate: {stats['win_rate']}%")
        print(f"  Profit Factor: {stats['profit_factor']}")
        print(f"  Return: {stats['total_return_pct']}%")
        print(f"  Max DD: {stats['max_drawdown_pct']}%")
        print(f"  Sharpe: {stats['sharpe_ratio']}")

        # Strategy breakdown
        if "strategy" in trade_df.columns:
            print(f"\n  Strategy breakdown:")
            for strat, group in trade_df.groupby("strategy"):
                wins = (group["pnl"] > 0).sum()
                total = len(group)
                pnl = group["pnl"].sum()
                print(f"    {strat}: {total} trades ({wins}W/{total-wins}L) PnL=${pnl:+,.2f}")

        total_trades.append(trade_df)

    # Portfolio summary
    if total_trades:
        all_trades = pd.concat(total_trades, ignore_index=True)
        total_pnl = all_trades["pnl"].sum()
        total_count = len(all_trades)
        total_wins = (all_trades["pnl"] > 0).sum()

        print(f"\n{'=' * 50}")
        print(f"PORTFOLIO SUMMARY")
        print(f"{'=' * 50}")
        print(f"Total trades: {total_count} ({total_wins}W/{total_count - total_wins}L)")
        print(f"Win rate: {total_wins / total_count * 100:.1f}%")
        print(f"Total PnL: ${total_pnl:+,.2f}")
        print(f"Avg PnL/trade: ${total_pnl / total_count:+,.2f}")

        results["_portfolio"] = {
            "total_trades": total_count,
            "winning_trades": int(total_wins),
            "win_rate": round(total_wins / total_count * 100, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / total_count, 2),
        }

    return results


# ---------------------------------------------------------------------------
# Walk-forward optimization
# ---------------------------------------------------------------------------

def walk_forward(symbol: str = "BTC/USDT", timeframe: str = "4h",
                 limit: int = 1000, n_splits: int = 3,
                 train_ratio: float = 0.7) -> dict:
    """Walk-forward optimization: train on past, test on future.

    Tests parameter combinations on training data, picks the best,
    then evaluates on unseen test data.
    """
    print(f"\n{'=' * 50}")
    print(f"Walk-Forward Optimization: {symbol} ({timeframe})")
    print(f"{'=' * 50}")

    df = fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
    total_bars = len(df)
    split_size = total_bars // n_splits

    # Parameter grid (kept small for speed)
    param_grid = {
        "ema_fast": [8, 12, 20],
        "ema_slow": [21, 26, 50],
        "adx_threshold": [20, 25, 30],
    }

    oos_results = []  # Out-of-sample results

    for split_idx in range(n_splits):
        start = split_idx * split_size
        end = min(start + split_size, total_bars)
        split_df = df.iloc[start:end]

        train_end = int(len(split_df) * train_ratio)
        train_df = split_df.iloc[:train_end]
        test_df = split_df.iloc[train_end:]

        if len(train_df) < 100 or len(test_df) < 30:
            continue

        print(f"\n  Split {split_idx + 1}/{n_splits}: "
              f"Train {len(train_df)} bars, Test {len(test_df)} bars")

        # Find best params on training data
        best_pf = -999
        best_params = {}

        for ema_f, ema_s, adx_t in iter_product(
            param_grid["ema_fast"], param_grid["ema_slow"], param_grid["adx_threshold"]
        ):
            if ema_f >= ema_s:
                continue

            strategies = [TrendFollowingStrategy(ema_fast=ema_f, ema_slow=ema_s, adx_threshold=adx_t)]
            bt = BacktesterV2(strategies=strategies, initial_capital=10000)
            trade_df, equity_df = bt.run(train_df, symbol)

            if trade_df.empty or len(trade_df) < 3:
                continue

            stats = compute_stats(trade_df, equity_df, 10000)
            pf = stats.get("profit_factor", 0)

            if pf > best_pf:
                best_pf = pf
                best_params = {"ema_fast": ema_f, "ema_slow": ema_s, "adx_threshold": adx_t}

        if not best_params:
            print(f"    No profitable parameters found on training data")
            continue

        print(f"    Best train params: {best_params} (PF={best_pf:.2f})")

        # Test on out-of-sample data
        strategies = [TrendFollowingStrategy(**best_params)]
        bt = BacktesterV2(strategies=strategies, initial_capital=10000)
        trade_df, equity_df = bt.run(test_df, symbol)

        if trade_df.empty:
            print(f"    No trades on test data")
            continue

        stats = compute_stats(trade_df, equity_df, 10000)
        stats["params"] = best_params
        oos_results.append(stats)

        print(f"    OOS: {stats['total_trades']} trades, "
              f"WR={stats['win_rate']}%, PF={stats['profit_factor']}, "
              f"Return={stats['total_return_pct']}%")

    # Aggregate OOS results
    if oos_results:
        avg_wr = np.mean([r["win_rate"] for r in oos_results])
        avg_pf = np.mean([r["profit_factor"] for r in oos_results])
        avg_ret = np.mean([r["total_return_pct"] for r in oos_results])
        total_trades = sum(r["total_trades"] for r in oos_results)

        print(f"\n  Walk-Forward Summary:")
        print(f"    Avg Win Rate: {avg_wr:.1f}%")
        print(f"    Avg Profit Factor: {avg_pf:.2f}")
        print(f"    Avg Return: {avg_ret:.2f}%")
        print(f"    Total OOS Trades: {total_trades}")

        return {
            "avg_win_rate": round(avg_wr, 1),
            "avg_profit_factor": round(avg_pf, 2),
            "avg_return_pct": round(avg_ret, 2),
            "total_oos_trades": total_trades,
            "splits": oos_results,
        }

    return {"error": "No valid walk-forward results"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest V2 — Numerical Strategies")
    parser.add_argument("--symbol", type=str, default=None, help="Single symbol")
    parser.add_argument("--symbols", nargs="+", default=None, help="Multiple symbols")
    parser.add_argument("--timeframe", type=str, default="4h", help="Timeframe (default: 4h)")
    parser.add_argument("--limit", type=int, default=1000, help="Number of candles (default: 1000)")
    parser.add_argument("--strategy", type=str, default=None,
                        choices=["trend", "reversion", "breakout"],
                        help="Test single strategy")
    parser.add_argument("--walk-forward", action="store_true", help="Walk-forward optimization")
    parser.add_argument("--capital", type=float, default=10000.0, help="Initial capital")
    args = parser.parse_args()

    # Select strategies
    strategy_map = {
        "trend": [TrendFollowingStrategy()],
        "reversion": [MeanReversionStrategy()],
        "breakout": [BreakoutStrategy()],
    }
    strategies = strategy_map.get(args.strategy) if args.strategy else None

    symbols = args.symbols or ([args.symbol] if args.symbol else SYMBOLS)

    if args.walk_forward:
        for sym in symbols:
            result = walk_forward(sym, args.timeframe, args.limit)
            print(json.dumps(result, indent=2, default=str))
    else:
        results = run_multi_symbol(
            symbols, args.timeframe, args.limit,
            strategies=strategies, initial_capital=args.capital)

        # Save results
        output_path = RESULT_DIR / "backtest_v2_results.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {output_path}")
