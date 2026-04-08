"""Trading Bot V2 — Numerical strategies, no API calls for signals.

Replaces the Gemini Vision image-based approach with pure numerical
strategies (EMA crossover, Bollinger Bands, Donchian breakout).

Supports: paper trading, dry-run (GMO), and live trading (GMO).

Usage:
    python bot_v2.py                          # Paper mode (default)
    python bot_v2.py --once                   # Single scan
    python bot_v2.py --mode dry_run           # GMO dry run
    python bot_v2.py --mode live --execute    # GMO live trading
    python bot_v2.py --strategy trend         # Only trend following
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from data_fetcher import fetch_ohlcv
from strategies import (
    TrendFollowingStrategy, MeanReversionStrategy, BreakoutStrategy,
    run_all_strategies, select_best_signal, Signal,
)
from risk_manager import RiskManager
from backtester import calculate_atr
from kill_switch import KillSwitch
from notifier import notify_signal, notify_close, notify_daily_summary, _send_discord
from config import SYMBOLS, RESULT_DIR

STATE_PATH = RESULT_DIR / "bot_v2_state.json"
JOURNAL_PATH = RESULT_DIR / "bot_v2_journal.json"

# GMO Coin symbol mapping
SYMBOL_MAP = {
    "BTC/USDT": "BTC_JPY",
    "ETH/USDT": "ETH_JPY",
    "XRP/USDT": "XRP_JPY",
    "SOL/USDT": "SOL_JPY",
    "BNB/USDT": "BNB_JPY",
}

# Optimized strategies per symbol (from grid search backtest)
SYMBOL_STRATEGIES = {
    "BTC/USDT": [TrendFollowingStrategy(ema_fast=8, ema_slow=100, adx_threshold=35,
                                         atr_sl_mult=2.0, atr_tp_mult=3.0)],
    "XRP/USDT": [TrendFollowingStrategy(ema_fast=12, ema_slow=50, adx_threshold=30,
                                         atr_sl_mult=2.0, atr_tp_mult=3.0)],
}
# Only trade symbols with backtested profitable strategies
DEFAULT_SYMBOLS = ["BTC/USDT", "XRP/USDT"]
MIN_ORDER_SIZE = {
    "BTC_JPY": 0.0001,
    "ETH_JPY": 0.01,
    "XRP_JPY": 1.0,
    "SOL_JPY": 0.01,
}


def _load_json(path: Path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def _save_json(path: Path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


class TradingBotV2:
    """Numerical strategy trading bot."""

    def __init__(self,
                 mode: str = "paper",
                 capital: float = 10000.0,
                 strategies: list = None,
                 risk_manager=None,
                 symbols=None,
                 timeframe: str = "4h",
                 min_strength: float = 0.3,
                 execute: bool = False):
        self.mode = mode
        self.timeframe = timeframe
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.min_strength = min_strength
        self.execute = execute

        self.strategies = strategies or [
            TrendFollowingStrategy(),
        ]
        self.rm = risk_manager or RiskManager()

        # Kill switch
        self.kill_switch = KillSwitch(
            max_daily_loss_pct=5.0,
            max_total_drawdown_pct=15.0,
            max_consecutive_losses=5,
            max_open_positions=5,
        )

        # GMO client (only for live/dry_run)
        self.gmo = None
        if mode in ("live", "dry_run"):
            from gmo_client import GMOClient
            self.gmo = GMOClient()

        # Load state
        state = _load_json(STATE_PATH, {})
        self.capital = state.get("capital", capital)
        self.initial_capital = state.get("initial_capital", capital)
        self.positions = state.get("positions", {})
        self.journal = _load_json(JOURNAL_PATH, [])

        self.rm.update_peak(max(self.capital, self.initial_capital))

    def save(self):
        _save_json(STATE_PATH, {
            "capital": self.capital,
            "initial_capital": self.initial_capital,
            "positions": self.positions,
            "last_update": datetime.now(timezone.utc).isoformat(),
        })
        _save_json(JOURNAL_PATH, self.journal)

    def _log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        mode_emoji = {"paper": "📝", "dry_run": "🟡", "live": "🔴"}.get(self.mode, "")
        print(f"[{ts}] [{mode_emoji} {self.mode.upper()}] {msg}")

    # ------------------------------------------------------------------
    # Order execution
    # ------------------------------------------------------------------

    def _place_order(self, symbol: str, side: str, size: float) -> "dict | None":
        if self.mode == "paper":
            return {"paper": True}

        gmo_symbol = SYMBOL_MAP.get(symbol)
        if not gmo_symbol:
            self._log(f"  {symbol} not mapped to GMO")
            return None

        min_size = MIN_ORDER_SIZE.get(gmo_symbol, 0.0001)
        if size < min_size:
            self._log(f"  Size {size} below min {min_size}")
            return None

        if not self.execute:
            self._log(f"  🟡 DRY RUN: Would {side} {size} {gmo_symbol}")
            return {"dry_run": True}

        try:
            self._log(f"  📤 {side} {size} {gmo_symbol}")
            result = self.gmo.place_order(
                symbol=gmo_symbol, side=side,
                size=str(size), execution_type="MARKET")
            self._log(f"  ✅ Order placed: {result}")
            return result
        except Exception as e:
            self._log(f"  ❌ Order failed: {e}")
            _send_discord(embeds=[{
                "title": "❌ Order Failed",
                "description": f"{side} {size} {gmo_symbol}: {e}",
                "color": 0xFF0000,
            }])
            return None

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def open_position(self, symbol: str, signal: Signal, size_usd: float):
        if symbol in self.positions:
            existing = self.positions[symbol]
            if existing["direction"] == signal.direction:
                return
            self.close_position(symbol, signal.entry_price, "reversal")

        side = "BUY" if signal.direction == "long" else "SELL"

        # For GMO: convert to coin quantity
        if self.gmo:
            gmo_symbol = SYMBOL_MAP.get(symbol)
            try:
                price_jpy = self.gmo.get_price(gmo_symbol) if gmo_symbol else signal.entry_price * 150
            except Exception:
                price_jpy = signal.entry_price * 150
            size_coin = size_usd / signal.entry_price
        else:
            price_jpy = signal.entry_price * 150
            size_coin = size_usd / signal.entry_price

        order = self._place_order(symbol, side, round(size_coin, 6))

        self.positions[symbol] = {
            "direction": signal.direction,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "size": size_usd,
            "size_coin": round(size_coin, 6),
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "strategy": signal.strategy_name,
            "strength": signal.strength,
            "highest": signal.entry_price,
            "lowest": signal.entry_price,
        }

        self._log(f"  📈 OPEN {signal.direction.upper()} {symbol} "
                  f"@ ${signal.entry_price:,.2f} | Size: ${size_usd:,.0f} "
                  f"| SL=${signal.stop_loss:,.2f} TP=${signal.take_profit:,.2f}")
        self._log(f"     Strategy: {signal.strategy_name} ({signal.strength:.0%})")
        self._log(f"     {signal.reasoning}")
        self.save()

        notify_signal(symbol, signal.direction, signal.entry_price,
                      signal.stop_loss, signal.take_profit,
                      signal.strategy_name, signal.strength, signal.reasoning)

    def close_position(self, symbol: str, exit_price: float, reason: str):
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        direction = pos["direction"]
        entry_price = pos["entry_price"]
        size = pos["size"]

        # Place closing order
        close_side = "SELL" if direction == "long" else "BUY"
        self._place_order(symbol, close_side, pos.get("size_coin", 0))

        if direction == "long":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        pnl = size * pnl_pct
        pnl -= abs(pnl) * 0.001  # Commission
        self.capital += pnl
        self.rm.update_peak(self.capital)

        trade = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "entry_time": pos["entry_time"],
            "exit_time": datetime.now(timezone.utc).isoformat(),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct * 100, 2),
            "exit_reason": reason,
            "capital_after": round(self.capital, 2),
            "strategy": pos.get("strategy", ""),
        }
        self.journal.append(trade)

        emoji = "✅" if pnl > 0 else "❌"
        self._log(f"  {emoji} CLOSE {direction.upper()} {symbol} "
                  f"@ ${exit_price:,.2f} | PnL: ${pnl:+,.2f} ({pnl_pct * 100:+.2f}%) | {reason}")

        del self.positions[symbol]
        self.save()

        notify_close(symbol, direction, entry_price, exit_price,
                     pnl, pnl_pct * 100, reason, self.capital)

    def check_sl_tp(self, symbol: str, high: float, low: float, atr: float):
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        sl = pos["stop_loss"]
        tp = pos["take_profit"]

        # Trailing stop
        if pos["direction"] == "long":
            if high > pos.get("highest", pos["entry_price"]):
                pos["highest"] = high
                if atr > 0:
                    new_sl = high - atr * 1.5
                    if new_sl > sl:
                        pos["stop_loss"] = new_sl
                        sl = new_sl
                        self.save()

            if low <= sl:
                self.close_position(symbol, sl, "stop_loss")
            elif high >= tp:
                self.close_position(symbol, tp, "take_profit")

        elif pos["direction"] == "short":
            if low < pos.get("lowest", pos["entry_price"]):
                pos["lowest"] = low
                if atr > 0:
                    new_sl = low + atr * 1.5
                    if new_sl < sl:
                        pos["stop_loss"] = new_sl
                        sl = new_sl
                        self.save()

            if high >= sl:
                self.close_position(symbol, sl, "stop_loss")
            elif low <= tp:
                self.close_position(symbol, tp, "take_profit")

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan_symbol(self, symbol: str):
        try:
            df = fetch_ohlcv(symbol=symbol, timeframe=self.timeframe, limit=200)
        except Exception as e:
            self._log(f"  {symbol}: Fetch failed: {e}")
            return

        atr = calculate_atr(df)
        current_atr = atr.iloc[-1] if not (atr.iloc[-1] != atr.iloc[-1]) else 0
        latest = df.iloc[-1]

        # Check SL/TP
        self.check_sl_tp(symbol, latest["high"], latest["low"], current_atr)

        # Skip if already in position
        if symbol in self.positions:
            return

        # Generate signals (ZERO API calls!)
        # Use symbol-specific optimized strategy if available
        strats = SYMBOL_STRATEGIES.get(symbol, self.strategies)
        signals = run_all_strategies(df, strats)
        best = select_best_signal(signals)

        if best is None or best.strength < self.min_strength:
            if signals:
                self._log(f"    Signals below threshold: {[(s.strategy_name, s.direction, s.strength) for s in signals]}")
            return

        # Risk checks
        can_trade, reason = self.rm.can_trade(self.capital, self.positions)
        if not can_trade:
            self._log(f"    Risk blocked: {reason}")
            return

        killed, kill_reason = self.kill_switch.check(
            self.capital, self.initial_capital, self.journal, self.positions)
        if killed:
            self._log(f"    🚨 KILL SWITCH: {kill_reason}")
            return

        # Position sizing
        size = self.rm.calculate_position_size(
            self.capital, best.entry_price, best.stop_loss,
            symbol, self.positions)

        if size <= 0:
            return

        self.open_position(symbol, best, size)

    def scan_all(self):
        # Kill switch pre-check
        killed, reason = self.kill_switch.check(
            self.capital, self.initial_capital, self.journal, self.positions)
        if killed:
            self._log(f"🚨 KILL SWITCH: {reason}")
            return

        strat_names = [s.name for s in self.strategies]
        self._log(f"{'=' * 50}")
        self._log(f"Scanning {len(self.symbols)} symbols | Strategies: {', '.join(strat_names)}")
        self._log(f"Capital: ${self.capital:,.2f} | Positions: {len(self.positions)} "
                  f"| Trades: {len(self.journal)}")

        for symbol in self.symbols:
            self._log(f"  {symbol}...")
            self.scan_symbol(symbol)

        self._print_status()
        self.save()

    def _print_status(self):
        self._log(f"{'─' * 50}")
        self._log(f"💼 Portfolio: ${self.capital:,.2f} "
                  f"(P&L: ${self.capital - self.initial_capital:+,.2f} / "
                  f"{(self.capital - self.initial_capital) / self.initial_capital * 100:+.2f}%)")

        dd = self.rm.get_drawdown(self.capital)
        heat = self.rm.get_portfolio_heat(self.capital, self.positions)
        self._log(f"   Drawdown: {dd:.1%} | Heat: {heat:.1%}")

        for sym, pos in self.positions.items():
            self._log(f"   {pos['direction'].upper()} {sym} @ ${pos['entry_price']:,.2f} "
                      f"| {pos.get('strategy', '')} | SL=${pos['stop_loss']:,.2f}")

        if self.journal:
            wins = sum(1 for t in self.journal if t["pnl"] > 0)
            total = len(self.journal)
            total_pnl = sum(t["pnl"] for t in self.journal)
            self._log(f"   Trades: {total} ({wins}W/{total - wins}L) | PnL: ${total_pnl:+,.2f}")
        self._log(f"{'─' * 50}")

    def run_loop(self, interval_sec: int = 3600):
        self._log(f"🚀 Bot V2 started! [{self.mode.upper()}]")
        self._log(f"   Strategies: {[s.name for s in self.strategies]}")
        self._log(f"   Timeframe: {self.timeframe} | Interval: {interval_sec}s")
        self._log(f"   Capital: ${self.capital:,.2f}")

        if self.mode == "live" and self.execute:
            _send_discord(embeds=[{
                "title": "🚀 Bot V2 Live Trading Started",
                "description": (f"Strategies: {', '.join(s.name for s in self.strategies)}\n"
                                f"Capital: ${self.capital:,.2f}\n"
                                f"Symbols: {', '.join(self.symbols)}"),
                "color": 0xFF6600,
            }])

        scan_count = 0
        try:
            while True:
                self.scan_all()
                scan_count += 1
                if scan_count % 24 == 0:  # Daily summary
                    notify_daily_summary(
                        self.capital, self.initial_capital,
                        self.positions, self.journal)
                self._log(f"⏳ Next scan in {interval_sec}s...\n")
                time.sleep(interval_sec)
        except KeyboardInterrupt:
            self._log("🛑 Stopped")
            self.save()

    def reset(self):
        if self.journal:
            archive = RESULT_DIR / f"bot_v2_journal_archive_{int(time.time())}.json"
            _save_json(archive, self.journal)
            self._log(f"Archived {len(self.journal)} trades to {archive}")
        self.capital = self.initial_capital
        self.positions = {}
        self.journal = []
        self.rm.update_peak(self.initial_capital)
        self.save()
        self._log(f"Reset. Capital: ${self.capital:,.2f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trading Bot V2 — Numerical Strategies")
    parser.add_argument("--mode", type=str, default="paper",
                        choices=["paper", "dry_run", "live"],
                        help="Trading mode (default: paper)")
    parser.add_argument("--execute", action="store_true",
                        help="Actually place live orders (requires --mode live)")
    parser.add_argument("--once", action="store_true", help="Single scan")
    parser.add_argument("--reset", action="store_true", help="Reset state")
    parser.add_argument("--capital", type=float, default=10000.0, help="Initial capital")
    parser.add_argument("--interval", type=int, default=3600, help="Scan interval (default: 3600s = 1h)")
    parser.add_argument("--timeframe", type=str, default="4h", help="Analysis timeframe")
    parser.add_argument("--symbols", nargs="+", default=None, help="Symbols to trade")
    parser.add_argument("--strategy", type=str, default=None,
                        choices=["trend", "reversion", "breakout"],
                        help="Use single strategy")
    parser.add_argument("--min-strength", type=float, default=0.3,
                        help="Minimum signal strength (default: 0.3)")
    args = parser.parse_args()

    strategy_map = {
        "trend": [TrendFollowingStrategy()],
        "reversion": [MeanReversionStrategy()],
        "breakout": [BreakoutStrategy()],
    }
    strategies = strategy_map.get(args.strategy) if args.strategy else None
    symbols = args.symbols or DEFAULT_SYMBOLS

    if args.mode == "live" and args.execute:
        print("⚠️  LIVE TRADING — Real orders will be placed!")
        print("    Press Ctrl+C within 5 seconds to cancel...")
        time.sleep(5)

    bot = TradingBotV2(
        mode=args.mode,
        capital=args.capital,
        strategies=strategies,
        symbols=symbols,
        timeframe=args.timeframe,
        min_strength=args.min_strength,
        execute=args.execute,
    )

    if args.reset:
        bot.reset()
    elif args.once:
        bot.scan_all()
    else:
        bot.run_loop(interval_sec=args.interval)
