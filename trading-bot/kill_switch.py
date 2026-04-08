"""Kill Switch — emergency safety system for live trading.

Monitors portfolio health and automatically stops trading when:
1. Daily loss exceeds threshold
2. Total drawdown exceeds threshold
3. Too many consecutive losses
4. Manual kill signal detected (file-based)

Can also be used to manually halt trading from Discord or terminal.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from config import RESULT_DIR
from notifier import _send_discord

KILL_FILE = RESULT_DIR / "KILL_SWITCH"
STATE_FILE = RESULT_DIR / "kill_switch_state.json"


class KillSwitch:
    """Safety system that halts trading when risk limits are breached."""

    def __init__(self,
                 max_daily_loss_pct: float = 5.0,
                 max_total_drawdown_pct: float = 15.0,
                 max_consecutive_losses: int = 5,
                 max_open_positions: int = 5):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_total_drawdown_pct = max_total_drawdown_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.max_open_positions = max_open_positions

        # Load state
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {
            "peak_capital": 0,
            "daily_start_capital": 0,
            "daily_start_date": "",
            "consecutive_losses": 0,
            "total_trades_today": 0,
            "killed": False,
            "kill_reason": "",
        }

    def _save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2, default=str)

    # ------------------------------------------------------------------
    # Core checks
    # ------------------------------------------------------------------

    def is_killed(self) -> tuple[bool, str]:
        """Check if trading should be halted.

        Returns (is_killed, reason) tuple.
        """
        # 1. Manual kill file
        if KILL_FILE.exists():
            return True, "Manual kill switch activated (KILL_SWITCH file exists)"

        # 2. State-based kill
        if self.state.get("killed", False):
            return True, self.state.get("kill_reason", "Previously killed")

        return False, ""

    def check(self, capital: float, initial_capital: float,
              journal: list, positions: dict) -> tuple[bool, str]:
        """Run all safety checks. Returns (should_halt, reason).

        Call this BEFORE every scan cycle.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Initialize daily tracking
        if self.state.get("daily_start_date") != today:
            self.state["daily_start_date"] = today
            self.state["daily_start_capital"] = capital
            self.state["total_trades_today"] = 0

        # Update peak
        if capital > self.state.get("peak_capital", 0):
            self.state["peak_capital"] = capital

        # Check 1: Manual kill
        killed, reason = self.is_killed()
        if killed:
            return True, reason

        # Check 2: Daily loss
        daily_start = self.state.get("daily_start_capital", initial_capital)
        if daily_start > 0:
            daily_loss_pct = (daily_start - capital) / daily_start * 100
            if daily_loss_pct >= self.max_daily_loss_pct:
                self._kill(f"Daily loss limit hit: -{daily_loss_pct:.1f}% "
                          f"(limit: {self.max_daily_loss_pct}%)")
                return True, self.state["kill_reason"]

        # Check 3: Total drawdown from peak
        peak = self.state.get("peak_capital", initial_capital)
        if peak > 0:
            drawdown_pct = (peak - capital) / peak * 100
            if drawdown_pct >= self.max_total_drawdown_pct:
                self._kill(f"Max drawdown hit: -{drawdown_pct:.1f}% from peak "
                          f"(limit: {self.max_total_drawdown_pct}%)")
                return True, self.state["kill_reason"]

        # Check 4: Consecutive losses
        if journal:
            consecutive = 0
            for trade in reversed(journal):
                if trade.get("pnl_jpy", trade.get("pnl", 0)) < 0:
                    consecutive += 1
                else:
                    break
            self.state["consecutive_losses"] = consecutive
            if consecutive >= self.max_consecutive_losses:
                self._kill(f"Too many consecutive losses: {consecutive} "
                          f"(limit: {self.max_consecutive_losses})")
                return True, self.state["kill_reason"]

        # Check 5: Too many open positions
        if len(positions) > self.max_open_positions:
            self._kill(f"Too many open positions: {len(positions)} "
                      f"(limit: {self.max_open_positions})")
            return True, self.state["kill_reason"]

        self._save_state()
        return False, ""

    def _kill(self, reason: str):
        """Activate kill switch."""
        self.state["killed"] = True
        self.state["kill_reason"] = reason
        self.state["kill_time"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

        print(f"🚨 KILL SWITCH ACTIVATED: {reason}")

        # Send Discord alert
        _send_discord(embeds=[{
            "title": "🚨 KILL SWITCH ACTIVATED",
            "description": reason,
            "color": 0xFF0000,
            "fields": [
                {"name": "Time", "value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")},
                {"name": "Action", "value": "All trading has been halted. Manual intervention required."},
                {"name": "To Resume", "value": "`python kill_switch.py --reset`"},
            ],
        }])

    # ------------------------------------------------------------------
    # Control methods
    # ------------------------------------------------------------------

    def reset(self):
        """Reset kill switch (manual intervention)."""
        self.state["killed"] = False
        self.state["kill_reason"] = ""
        if KILL_FILE.exists():
            KILL_FILE.unlink()
        self._save_state()
        print("✅ Kill switch reset. Trading can resume.")

        _send_discord(embeds=[{
            "title": "✅ Kill Switch Reset",
            "description": "Trading has been resumed by manual intervention.",
            "color": 0x26A69A,
        }])

    def manual_kill(self, reason: str = "Manual halt requested"):
        """Manually activate kill switch."""
        KILL_FILE.write_text(reason)
        self._kill(reason)

    def status(self) -> dict:
        """Get current kill switch status."""
        killed, reason = self.is_killed()
        return {
            "active": killed,
            "reason": reason,
            "peak_capital": self.state.get("peak_capital", 0),
            "daily_start_capital": self.state.get("daily_start_capital", 0),
            "consecutive_losses": self.state.get("consecutive_losses", 0),
            "limits": {
                "max_daily_loss_pct": self.max_daily_loss_pct,
                "max_total_drawdown_pct": self.max_total_drawdown_pct,
                "max_consecutive_losses": self.max_consecutive_losses,
                "max_open_positions": self.max_open_positions,
            },
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Kill Switch Control")
    parser.add_argument("--reset", action="store_true", help="Reset kill switch")
    parser.add_argument("--kill", type=str, default="", help="Manually kill with reason")
    parser.add_argument("--status", action="store_true", help="Show status")
    args = parser.parse_args()

    ks = KillSwitch()

    if args.reset:
        ks.reset()
    elif args.kill:
        ks.manual_kill(args.kill)
    else:
        status = ks.status()
        print(f"Kill Switch: {'🔴 ACTIVE' if status['active'] else '🟢 OK'}")
        if status["active"]:
            print(f"  Reason: {status['reason']}")
        print(f"  Peak capital: ${status['peak_capital']:,.2f}")
        print(f"  Consecutive losses: {status['consecutive_losses']}")
        print(f"  Limits: {json.dumps(status['limits'], indent=4)}")
