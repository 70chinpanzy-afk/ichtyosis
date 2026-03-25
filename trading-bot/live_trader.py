"""Live Trading Engine for GMO Coin.

Extends the paper trader logic with real order execution via GMO Coin API.
Includes kill switch integration and strict risk management.

Required .env vars:
    GMO_API_KEY=xxx
    GMO_API_SECRET=xxx
    GEMINI_API_KEY=xxx
    DISCORD_WEBHOOK_URL=xxx

Usage:
    python live_trader.py --once               # Single scan (dry run)
    python live_trader.py --once --execute      # Single scan (real orders)
    python live_trader.py --execute             # Continuous (real orders)
    python live_trader.py --capital 100000      # Set capital in JPY
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from gmo_client import GMOClient
from data_fetcher import fetch_ohlcv
from chart_generator import generate_chart_image
from numerical_filter import prefilter_window
from multi_agent_analyzer import multi_agent_analyze
from backtester import calculate_atr
from market_regime import detect_regime
from kill_switch import KillSwitch
from notifier import (
    notify_signal, notify_close, notify_daily_summary, _send_discord,
)
from config import (
    SYMBOLS, TIMEFRAME, CHART_WINDOW_SIZE, RESULT_DIR,
    ATR_SL_MULTIPLIER, ATR_TP_MULTIPLIER,
)

LIVE_STATE_PATH = RESULT_DIR / "live_state.json"
LIVE_JOURNAL_PATH = RESULT_DIR / "live_journal.json"

# GMO Coin symbol mapping: "BTC/USDT" -> "BTC_JPY"
SYMBOL_MAP = {
    "BTC/USDT": "BTC_JPY",
    "ETH/USDT": "ETH_JPY",
    "XRP/USDT": "XRP_JPY",
    "SOL/USDT": "SOL_JPY",
    "BNB/USDT": "BNB_JPY",  # Check if GMO supports BNB
}

# Minimum order sizes for GMO Coin
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


class LiveTrader:
    """Live trading engine with GMO Coin integration."""

    def __init__(self,
                 capital_jpy: float = 100000,
                 sl_mult: float = ATR_SL_MULTIPLIER,
                 tp_mult: float = ATR_TP_MULTIPLIER,
                 min_confidence: float = 0.60,
                 max_position_pct: float = 0.20,  # Max 20% per position
                 execute: bool = False):
        self.sl_mult = sl_mult
        self.tp_mult = tp_mult
        self.min_confidence = min_confidence
        self.max_position_pct = max_position_pct
        self.execute = execute  # False = dry run mode

        # GMO Coin client
        self.gmo = GMOClient()

        # Kill switch
        self.kill_switch = KillSwitch(
            max_daily_loss_pct=5.0,
            max_total_drawdown_pct=15.0,
            max_consecutive_losses=5,
            max_open_positions=5,
        )

        # Load state
        state = _load_json(LIVE_STATE_PATH, {})
        self.capital = state.get("capital", capital_jpy)
        self.initial_capital = state.get("initial_capital", capital_jpy)
        self.positions = state.get("positions", {})
        self.journal = _load_json(LIVE_JOURNAL_PATH, [])

    def save(self):
        _save_json(LIVE_STATE_PATH, {
            "capital": self.capital,
            "initial_capital": self.initial_capital,
            "positions": self.positions,
            "last_update": datetime.now(timezone.utc).isoformat(),
        })
        _save_json(LIVE_JOURNAL_PATH, self.journal)

    def _log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        mode = "🔴 LIVE" if self.execute else "🟡 DRY RUN"
        print(f"[{ts}] [{mode}] {msg}")

    # ------------------------------------------------------------------
    # Order execution
    # ------------------------------------------------------------------

    def _place_order(self, symbol: str, side: str, size: float) -> dict | None:
        """Place an order on GMO Coin.

        Returns order result or None if dry run / error.
        """
        gmo_symbol = SYMBOL_MAP.get(symbol)
        if not gmo_symbol:
            self._log(f"  ⚠️ {symbol} not mapped to GMO symbol")
            return None

        min_size = MIN_ORDER_SIZE.get(gmo_symbol, 0.0001)
        if size < min_size:
            self._log(f"  ⚠️ Order size {size} below minimum {min_size}")
            return None

        if not self.execute:
            self._log(f"  🟡 DRY RUN: Would {side} {size} {gmo_symbol}")
            return {"dry_run": True, "side": side, "size": size}

        try:
            self._log(f"  📤 Placing {side} order: {size} {gmo_symbol}")
            result = self.gmo.place_order(
                symbol=gmo_symbol,
                side=side,
                size=str(size),
                execution_type="MARKET",
            )
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

    def _calculate_position_size(self, symbol: str, price_jpy: float) -> float:
        """Calculate position size based on risk management rules."""
        # Max position = capital * max_position_pct
        max_jpy = self.capital * self.max_position_pct
        size = max_jpy / price_jpy

        # Round to appropriate precision
        gmo_symbol = SYMBOL_MAP.get(symbol, "")
        min_size = MIN_ORDER_SIZE.get(gmo_symbol, 0.0001)
        precision = len(str(min_size).split(".")[-1]) if "." in str(min_size) else 0
        size = round(size, precision)

        return max(size, min_size)

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def open_position(self, symbol: str, direction: str, price: float,
                      atr: float, pattern: str, confidence: float,
                      reasoning: str):
        """Open a new position."""
        if symbol in self.positions:
            existing = self.positions[symbol]
            if existing["direction"] == direction:
                self._log(f"  Already {direction} {symbol}, skipping")
                return
            # Close opposite position (reversal)
            self.close_position(symbol, price, "reversal")

        # Calculate position size
        # Get JPY price from GMO
        gmo_symbol = SYMBOL_MAP.get(symbol)
        if gmo_symbol:
            try:
                price_jpy = self.gmo.get_price(gmo_symbol)
            except Exception:
                price_jpy = price * 150  # Rough USD->JPY fallback
        else:
            price_jpy = price * 150

        size = self._calculate_position_size(symbol, price_jpy)

        # Calculate SL/TP
        if direction == "long":
            sl = price - atr * self.sl_mult
            tp = price + atr * self.tp_mult
            side = "BUY"
        else:
            sl = price + atr * self.sl_mult
            tp = price - atr * self.tp_mult
            side = "SELL"

        # Place order
        order_result = self._place_order(symbol, side, size)

        # Record position
        self.positions[symbol] = {
            "direction": direction,
            "entry_price": price,
            "entry_price_jpy": price_jpy,
            "stop_loss": sl,
            "take_profit": tp,
            "size": size,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "pattern": pattern,
            "confidence": confidence,
            "order_result": order_result,
        }

        self._log(f"  📈 OPEN {direction.upper()} {symbol} @ ¥{price_jpy:,.0f} "
                  f"(${price:,.2f}) | Size: {size} | SL={sl:,.2f} TP={tp:,.2f}")
        self.save()

        notify_signal(symbol, direction, price, sl, tp,
                      pattern, confidence, reasoning)

    def close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position."""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        direction = pos["direction"]
        entry_price = pos["entry_price"]
        size = pos["size"]

        # Place closing order
        close_side = "SELL" if direction == "long" else "BUY"
        self._place_order(symbol, close_side, size)

        # Calculate PnL
        if direction == "long":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        pnl_jpy = pos.get("entry_price_jpy", 0) * size * pnl_pct

        trade_record = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "entry_time": pos["entry_time"],
            "exit_time": datetime.now(timezone.utc).isoformat(),
            "pnl_jpy": round(pnl_jpy, 0),
            "pnl_pct": round(pnl_pct * 100, 2),
            "exit_reason": reason,
            "size": size,
            "pattern": pos.get("pattern", ""),
        }
        self.journal.append(trade_record)
        self.capital += pnl_jpy

        emoji = "✅" if pnl_jpy > 0 else "❌"
        self._log(f"  {emoji} CLOSE {direction.upper()} {symbol} "
                  f"| PnL: ¥{pnl_jpy:+,.0f} ({pnl_pct * 100:+.2f}%) | {reason}")

        del self.positions[symbol]
        self.save()

        notify_close(symbol, direction, entry_price, exit_price,
                     pnl_jpy, pnl_pct * 100, reason, self.capital)

    def check_sl_tp(self, symbol: str, current_high: float,
                    current_low: float, current_atr: float = 0):
        """Check SL/TP with trailing stop."""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        direction = pos["direction"]
        entry_price = pos["entry_price"]
        sl = pos["stop_loss"]
        tp = pos["take_profit"]

        if direction == "long":
            # Trailing stop
            highest = pos.get("highest_since_entry", entry_price)
            if current_high > highest:
                pos["highest_since_entry"] = current_high
                if current_atr > 0:
                    new_sl = current_high - current_atr * self.sl_mult
                    if new_sl > sl:
                        pos["stop_loss"] = new_sl
                        sl = new_sl
                        self.save()

            if current_low <= sl:
                self.close_position(symbol, sl, "stop_loss")
            elif current_high >= tp:
                self.close_position(symbol, tp, "take_profit")

        elif direction == "short":
            lowest = pos.get("lowest_since_entry", entry_price)
            if current_low < lowest:
                pos["lowest_since_entry"] = current_low
                if current_atr > 0:
                    new_sl = current_low + current_atr * self.sl_mult
                    if new_sl < sl:
                        pos["stop_loss"] = new_sl
                        sl = new_sl
                        self.save()

            if current_high >= sl:
                self.close_position(symbol, sl, "stop_loss")
            elif current_low <= tp:
                self.close_position(symbol, tp, "take_profit")

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan_symbol(self, symbol: str):
        """Scan one symbol."""
        try:
            df = fetch_ohlcv(symbol=symbol, timeframe=TIMEFRAME, limit=100)
        except Exception as e:
            self._log(f"  {symbol}: Failed to fetch data: {e}")
            return

        atr = calculate_atr(df)
        current_atr = atr.iloc[-1]
        if str(current_atr) == "nan":
            current_atr = 0

        latest = df.iloc[-1]
        self.check_sl_tp(symbol, latest["high"], latest["low"], current_atr)

        # Market regime
        regime = detect_regime(df)
        self._log(f"    📊 Regime: {regime['regime']} (ADX={regime['adx']})")
        if regime["regime"] == "ranging":
            self._log(f"    ⏸️ Ranging — skipping")
            return

        # Pre-filter
        window_start = max(0, len(df) - CHART_WINDOW_SIZE)
        window_df = df.iloc[window_start:].copy()
        candidates = prefilter_window(window_df)
        if not candidates:
            return

        # Chart + analysis
        key = symbol.replace("/", "_")
        chart_path = generate_chart_image(df, window_start, symbol_prefix=f"live_{key}")
        if not chart_path:
            return

        self._log(f"    🤖 Multi-agent analysis...")
        result = multi_agent_analyze(chart_path, candidates, symbol=symbol)

        pattern = result.get("pattern", "none")
        confidence = result.get("confidence", 0.0) * regime["confidence_modifier"]
        direction = result.get("direction", "none")
        reasoning = result.get("reasoning", "")

        if pattern == "none" or confidence < self.min_confidence or current_atr <= 0:
            return

        self.open_position(symbol, direction, latest["close"], current_atr,
                           pattern, confidence, reasoning)

    def scan_all(self, symbols: list[str] | None = None):
        """Scan all symbols with kill switch check."""
        if symbols is None:
            symbols = SYMBOLS

        # Kill switch check
        killed, reason = self.kill_switch.check(
            self.capital, self.initial_capital, self.journal, self.positions)
        if killed:
            self._log(f"🚨 KILL SWITCH: {reason}")
            return

        mode = "🔴 LIVE" if self.execute else "🟡 DRY RUN"
        self._log(f"{'=' * 50}")
        self._log(f"Scanning {len(symbols)} symbols [{mode}]")
        self._log(f"Capital: ¥{self.capital:,.0f} | Positions: {len(self.positions)}")

        for symbol in symbols:
            self._log(f"  Scanning {symbol}...")
            self.scan_symbol(symbol)

        self._print_status()
        self.save()

    def _print_status(self):
        self._log(f"{'─' * 50}")
        self._log(f"💼 Portfolio: ¥{self.capital:,.0f} "
                  f"(P&L: ¥{self.capital - self.initial_capital:+,.0f})")
        for sym, pos in self.positions.items():
            self._log(f"   {pos['direction'].upper()} {sym} @ ${pos['entry_price']:,.2f}")
        self._log(f"{'─' * 50}")

    def run_loop(self, interval_sec: int = 14400, symbols: list[str] | None = None):
        """Run continuous loop."""
        mode = "🔴 LIVE" if self.execute else "🟡 DRY RUN"
        self._log(f"🚀 Live Trader started! [{mode}]")
        self._log(f"   Capital: ¥{self.capital:,.0f}")

        if self.execute:
            _send_discord(embeds=[{
                "title": "🚀 Live Trading Bot Started",
                "description": f"Capital: ¥{self.capital:,.0f}\nSymbols: {', '.join(symbols or SYMBOLS)}",
                "color": 0xFF6600,
            }])

        scan_count = 0
        try:
            while True:
                self.scan_all(symbols)
                scan_count += 1
                if scan_count % 6 == 0:
                    notify_daily_summary(
                        self.capital, self.initial_capital,
                        self.positions, self.journal)
                self._log(f"⏳ Next scan in {interval_sec}s...")
                time.sleep(interval_sec)
        except KeyboardInterrupt:
            self._log("🛑 Stopped by user")
            self.save()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Trading Bot (GMO Coin)")
    parser.add_argument("--execute", action="store_true",
                        help="Actually place orders (without this flag = dry run)")
    parser.add_argument("--once", action="store_true",
                        help="Run one scan and exit")
    parser.add_argument("--capital", type=float, default=100000,
                        help="Initial capital in JPY (default: 100000)")
    parser.add_argument("--interval", type=int, default=14400,
                        help="Scan interval in seconds (default: 14400 = 4h)")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="Symbols to trade")
    parser.add_argument("--max-position-pct", type=float, default=0.20,
                        help="Max position size as %% of capital (default: 0.20)")
    args = parser.parse_args()

    if args.execute:
        print("⚠️  LIVE TRADING MODE — Real orders will be placed!")
        print("    Press Ctrl+C within 5 seconds to cancel...")
        time.sleep(5)
        print("    Starting live trading...")

    trader = LiveTrader(
        capital_jpy=args.capital,
        execute=args.execute,
        max_position_pct=args.max_position_pct,
    )

    if args.once:
        trader.scan_all(args.symbols)
    else:
        trader.run_loop(interval_sec=args.interval, symbols=args.symbols)
