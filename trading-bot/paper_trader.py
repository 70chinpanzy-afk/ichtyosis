"""Paper Trading Engine — real-time signal tracking with virtual capital.

Monitors all configured symbols on a fixed interval, detects patterns via
Gemini Vision, opens/closes virtual positions with ATR-based SL/TP, and
persists the full trade journal to a JSON file.

Usage:
    python paper_trader.py                  # Run with defaults
    python paper_trader.py --interval 300   # Scan every 5 min
    python paper_trader.py --capital 50000  # Start with $50k
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from data_fetcher import fetch_ohlcv
from chart_generator import generate_chart_image
from numerical_filter import prefilter_window
from gemini_analyzer import analyze_chart
from multi_agent_analyzer import multi_agent_analyze
from backtester import calculate_atr
from market_regime import detect_regime
from notifier import notify_signal, notify_close, notify_daily_summary, notify_scan_start
from config import (
    SYMBOLS, TIMEFRAME, CHART_WINDOW_SIZE, INITIAL_CAPITAL,
    ATR_SL_MULTIPLIER, ATR_TP_MULTIPLIER, RESULT_DIR,
)

JOURNAL_PATH = RESULT_DIR / "paper_journal.json"
STATE_PATH = RESULT_DIR / "paper_state.json"

# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def _save_json(path: Path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Paper Trading State
# ---------------------------------------------------------------------------

class PaperTrader:
    """Manages virtual positions and trade journal."""

    def __init__(self, initial_capital: float = INITIAL_CAPITAL,
                 sl_mult: float = ATR_SL_MULTIPLIER,
                 tp_mult: float = ATR_TP_MULTIPLIER,
                 min_confidence: float = 0.60,
                 commission: float = 0.001,
                 use_multi_agent: bool = True):
        self.initial_capital = initial_capital
        self.sl_mult = sl_mult
        self.tp_mult = tp_mult
        self.min_confidence = min_confidence
        self.commission = commission
        self.use_multi_agent = use_multi_agent

        # Load persisted state
        state = _load_json(STATE_PATH, {})
        self.capital = state.get("capital", initial_capital)
        self.positions = state.get("positions", {})  # symbol -> position dict
        self.journal = _load_json(JOURNAL_PATH, [])

    def save(self):
        """Persist state and journal to disk."""
        _save_json(STATE_PATH, {
            "capital": self.capital,
            "positions": self.positions,
            "initial_capital": self.initial_capital,
            "last_update": datetime.now(timezone.utc).isoformat(),
        })
        _save_json(JOURNAL_PATH, self.journal)

    def _log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[{ts}] {msg}")

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def check_sl_tp(self, symbol: str, current_high: float, current_low: float,
                    current_atr: float = 0):
        """Check stop-loss, take-profit, and trailing stop for an open position."""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        direction = pos["direction"]
        entry_price = pos["entry_price"]
        stop_loss = pos["stop_loss"]
        take_profit = pos["take_profit"]

        closed = False
        exit_price = 0.0
        exit_reason = ""

        if direction == "long":
            # Trailing stop: move SL up when price makes new highs
            if current_high > pos.get("highest_since_entry", entry_price):
                pos["highest_since_entry"] = current_high
                # Trail SL at 1.5 × ATR below highest point
                if current_atr > 0:
                    new_sl = current_high - current_atr * self.sl_mult
                    if new_sl > stop_loss:
                        pos["stop_loss"] = new_sl
                        stop_loss = new_sl
                        self.save()

            if current_low <= stop_loss:
                exit_price = stop_loss
                exit_reason = "trailing_stop" if stop_loss > entry_price - current_atr * self.sl_mult else "stop_loss"
                closed = True
            elif current_high >= take_profit:
                exit_price = take_profit
                exit_reason = "take_profit"
                closed = True

        elif direction == "short":
            # Trailing stop: move SL down when price makes new lows
            if current_low < pos.get("lowest_since_entry", entry_price):
                pos["lowest_since_entry"] = current_low
                if current_atr > 0:
                    new_sl = current_low + current_atr * self.sl_mult
                    if new_sl < stop_loss:
                        pos["stop_loss"] = new_sl
                        stop_loss = new_sl
                        self.save()

            if current_high >= stop_loss:
                exit_price = stop_loss
                exit_reason = "trailing_stop" if stop_loss < entry_price + current_atr * self.sl_mult else "stop_loss"
                closed = True
            elif current_low <= take_profit:
                exit_price = take_profit
                exit_reason = "take_profit"
                closed = True

        if closed:
            self._close_position(symbol, exit_price, exit_reason)

    def open_position(self, symbol: str, direction: str, entry_price: float,
                      atr: float, pattern: str, confidence: float, reasoning: str):
        """Open a new virtual position."""
        if symbol in self.positions:
            existing = self.positions[symbol]
            if existing["direction"] == direction:
                self._log(f"  {symbol}: Already {direction}, skipping")
                return
            # Close opposite position first (reversal)
            self._close_position(symbol, entry_price, "reversal")

        # Calculate position size (equal allocation across symbols)
        size = self.capital / len(SYMBOLS)

        if direction == "long":
            sl = entry_price - atr * self.sl_mult
            tp = entry_price + atr * self.tp_mult
        else:
            sl = entry_price + atr * self.sl_mult
            tp = entry_price - atr * self.tp_mult

        self.positions[symbol] = {
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": sl,
            "take_profit": tp,
            "size": size,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "pattern": pattern,
            "confidence": confidence,
        }

        self._log(f"  📈 OPEN {direction.upper()} {symbol} @ ${entry_price:,.2f} "
                  f"| SL=${sl:,.2f} TP=${tp:,.2f} | Pattern: {pattern} ({confidence:.0%})")
        self._log(f"     Reasoning: {reasoning}")
        self.save()

        # LINE notification
        notify_signal(symbol, direction, entry_price, sl, tp,
                      pattern, confidence, reasoning)

    def _close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a virtual position and record in journal."""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        direction = pos["direction"]
        entry_price = pos["entry_price"]
        size = pos["size"]

        if direction == "long":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        pnl = size * pnl_pct
        pnl -= abs(pnl) * self.commission
        self.capital += pnl

        trade_record = {
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
            "pattern": pos.get("pattern", ""),
            "confidence": pos.get("confidence", 0),
        }
        self.journal.append(trade_record)

        emoji = "✅" if pnl > 0 else "❌"
        self._log(f"  {emoji} CLOSE {direction.upper()} {symbol} @ ${exit_price:,.2f} "
                  f"| PnL: ${pnl:+,.2f} ({pnl_pct:+.2f}%) | Reason: {reason}")

        del self.positions[symbol]
        self.save()

        # LINE notification
        notify_close(symbol, direction, entry_price, exit_price,
                     pnl, pnl_pct * 100, reason, self.capital)

    # ------------------------------------------------------------------
    # Scan loop
    # ------------------------------------------------------------------

    def scan_symbol(self, symbol: str, timeframe: str = TIMEFRAME):
        """Scan one symbol for patterns and manage positions."""
        try:
            df = fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=100)
        except Exception as e:
            self._log(f"  {symbol}: Failed to fetch data: {e}")
            return

        # Calculate ATR for trailing stop
        atr = calculate_atr(df)
        current_atr = atr.iloc[-1]
        current_atr = current_atr if not (current_atr <= 0 or str(current_atr) == "nan") else 0

        # Check SL/TP with latest candle (including trailing stop)
        latest = df.iloc[-1]
        self.check_sl_tp(symbol, latest["high"], latest["low"], current_atr)

        # Market regime check
        regime = detect_regime(df)
        self._log(f"    📊 Regime: {regime['regime']} (ADX={regime['adx']}, "
                  f"trend={regime['trend_direction']})")
        if regime["regime"] == "ranging":
            self._log(f"    ⏸️  Ranging market detected — skipping pattern detection")
            return

        # Generate chart for last 60 candles
        window_start = max(0, len(df) - CHART_WINDOW_SIZE)
        window_df = df.iloc[window_start:].copy()

        # Numerical pre-filter
        candidates = prefilter_window(window_df)
        if not candidates:
            return

        # Generate chart image
        key = symbol.replace("/", "_")
        chart_path = generate_chart_image(df, window_start, symbol_prefix=f"paper_{key}")
        if not chart_path or not chart_path.exists():
            return

        # Analysis: Multi-agent consensus OR single-agent
        if self.use_multi_agent:
            self._log(f"    🤖 Running 4-agent consensus analysis...")
            result = multi_agent_analyze(chart_path, candidates, symbol=symbol)
            # Log vote details
            vote = result.get("consensus", {}).get("vote_detail", {})
            if vote:
                for agent_name, v in vote.items():
                    if "dir" in v:
                        self._log(f"      {agent_name}: {v['dir']} ({v['conf']:.0%})"
                                  if isinstance(v.get('conf'), (int, float))
                                  else f"      {agent_name}: {v}")
                    elif "should_trade" in v:
                        self._log(f"      {agent_name}: trade={'✅' if v['should_trade'] else '🚫'} "
                                  f"objection={v.get('objection', 0):.0%}")
        else:
            result = analyze_chart(chart_path, candidates)

        pattern = result.get("pattern", "none")
        confidence = result.get("confidence", 0.0)
        direction = result.get("direction", "none")
        reasoning = result.get("reasoning", "")

        # Apply regime confidence modifier
        confidence *= regime["confidence_modifier"]
        self._log(f"    Adjusted confidence: {confidence:.0%} "
                  f"(modifier: {regime['confidence_modifier']})")

        if pattern == "none" or confidence < self.min_confidence:
            return

        if current_atr <= 0:
            return

        current_price = latest["close"]
        self.open_position(symbol, direction, current_price, current_atr,
                           pattern, confidence, reasoning)

    def scan_all(self, symbols: list[str] | None = None, timeframe: str = TIMEFRAME):
        """Scan all symbols once."""
        if symbols is None:
            symbols = SYMBOLS

        mode = "🤖 Multi-Agent (4-agent consensus)" if self.use_multi_agent else "Single-Agent"
        self._log(f"{'=' * 50}")
        self._log(f"Scanning {len(symbols)} symbols... [{mode}]")
        self._log(f"Capital: ${self.capital:,.2f} | "
                  f"Open positions: {len(self.positions)} | "
                  f"Total trades: {len(self.journal)}")

        for symbol in symbols:
            self._log(f"  Scanning {symbol}...")
            self.scan_symbol(symbol, timeframe)

        self._print_status()
        self.save()

    def _print_status(self):
        """Print current portfolio status."""
        self._log(f"{'─' * 50}")
        self._log(f"💼 Portfolio Status")
        self._log(f"   Capital: ${self.capital:,.2f} "
                  f"(P&L: ${self.capital - self.initial_capital:+,.2f} / "
                  f"{(self.capital - self.initial_capital) / self.initial_capital * 100:+.2f}%)")

        if self.positions:
            self._log(f"   Open positions:")
            for sym, pos in self.positions.items():
                self._log(f"     {pos['direction'].upper()} {sym} "
                          f"@ ${pos['entry_price']:,.2f} "
                          f"| SL=${pos['stop_loss']:,.2f} TP=${pos['take_profit']:,.2f}")

        if self.journal:
            wins = sum(1 for t in self.journal if t["pnl"] > 0)
            total = len(self.journal)
            total_pnl = sum(t["pnl"] for t in self.journal)
            self._log(f"   Closed trades: {total} ({wins}W/{total - wins}L) "
                      f"| Total PnL: ${total_pnl:+,.2f}")
        self._log(f"{'─' * 50}")

    def run_loop(self, interval_sec: int = 300, symbols: list[str] | None = None):
        """Run continuous scanning loop."""
        self._log("🚀 Paper Trading Bot started!")
        self._log(f"   Interval: {interval_sec}s | Symbols: {symbols or SYMBOLS}")
        self._log(f"   SL: {self.sl_mult}×ATR | TP: {self.tp_mult}×ATR "
                  f"| Min confidence: {self.min_confidence}")
        self._log(f"   Capital: ${self.capital:,.2f}")
        self._log("")

        scan_count = 0
        try:
            while True:
                self.scan_all(symbols)
                scan_count += 1

                # Send daily summary every 6 scans (= 24h at 4h intervals)
                if scan_count % 6 == 0:
                    notify_daily_summary(
                        self.capital, self.initial_capital,
                        self.positions, self.journal)

                self._log(f"⏳ Next scan in {interval_sec}s...\n")
                time.sleep(interval_sec)
        except KeyboardInterrupt:
            self._log("\n🛑 Paper Trading Bot stopped by user")
            self._print_status()
            self.save()

    def reset(self):
        """Reset paper trading state (keep journal as archive)."""
        self.capital = self.initial_capital
        self.positions = {}
        # Archive old journal
        if self.journal:
            archive_path = RESULT_DIR / f"paper_journal_archive_{int(time.time())}.json"
            _save_json(archive_path, self.journal)
            self._log(f"Archived {len(self.journal)} trades to {archive_path}")
        self.journal = []
        self.save()
        self._log(f"Reset complete. Capital: ${self.capital:,.2f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paper Trading Bot")
    parser.add_argument("--interval", type=int, default=14400,
                        help="Scan interval in seconds (default: 14400 = 4h)")
    parser.add_argument("--capital", type=float, default=INITIAL_CAPITAL,
                        help=f"Initial capital (default: {INITIAL_CAPITAL})")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="Symbols to trade (default: all)")
    parser.add_argument("--sl", type=float, default=ATR_SL_MULTIPLIER,
                        help=f"SL ATR multiplier (default: {ATR_SL_MULTIPLIER})")
    parser.add_argument("--tp", type=float, default=ATR_TP_MULTIPLIER,
                        help=f"TP ATR multiplier (default: {ATR_TP_MULTIPLIER})")
    parser.add_argument("--confidence", type=float, default=0.60,
                        help="Min confidence threshold (default: 0.60)")
    parser.add_argument("--reset", action="store_true",
                        help="Reset paper trading state")
    parser.add_argument("--once", action="store_true",
                        help="Run one scan and exit (no loop)")
    parser.add_argument("--single-agent", action="store_true",
                        help="Use single-agent mode (faster, less accurate)")
    args = parser.parse_args()

    symbols = args.symbols
    if symbols:
        symbols = [s if "/" in s else f"{s[:3]}/{s[3:]}" for s in symbols]

    trader = PaperTrader(
        initial_capital=args.capital,
        sl_mult=args.sl,
        tp_mult=args.tp,
        min_confidence=args.confidence,
        use_multi_agent=not args.single_agent,
    )

    if args.reset:
        trader.reset()
    elif args.once:
        trader.scan_all(symbols)
    else:
        trader.run_loop(interval_sec=args.interval, symbols=symbols)
