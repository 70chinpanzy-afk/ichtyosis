"""Discord Webhook notification module.

Sends trade signals, position updates, and daily summaries to Discord.

Required .env var:
    DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxx/xxxx
"""

import json
import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")


def _send_discord(content: str = "", embeds=None) -> bool:
    """Send a message via Discord Webhook.

    Returns True on success, False on failure.
    """
    if not DISCORD_WEBHOOK_URL:
        print("[Discord] ⚠️ DISCORD_WEBHOOK_URL not set. Skipping notification.")
        return False

    payload = {}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds

    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            return True
        else:
            print(f"[Discord] ❌ Error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[Discord] ❌ Request failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Notification templates
# ---------------------------------------------------------------------------

def notify_signal(symbol: str, direction: str, entry_price: float,
                  stop_loss: float, take_profit: float,
                  pattern: str, confidence: float, reasoning: str = "") -> bool:
    """Notify when a new position is opened."""
    color = 0xEF5350 if direction == "short" else 0x26A69A  # red / green

    fields = [
        {"name": "📍 エントリー", "value": f"${entry_price:,.2f}", "inline": True},
        {"name": "🛑 損切り(SL)", "value": f"${stop_loss:,.2f}", "inline": True},
        {"name": "🎯 利確(TP)", "value": f"${take_profit:,.2f}", "inline": True},
        {"name": "📊 パターン", "value": f"{pattern} ({confidence:.0%})", "inline": True},
    ]
    if reasoning:
        short_reason = reasoning[:300] + "..." if len(reasoning) > 300 else reasoning
        fields.append({"name": "💡 根拠", "value": short_reason, "inline": False})

    embed = {
        "title": f"{'🔴' if direction == 'short' else '🟢'} {direction.upper()} {symbol}",
        "color": color,
        "fields": fields,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return _send_discord(embeds=[embed])


def notify_close(symbol: str, direction: str, entry_price: float,
                 exit_price: float, pnl: float, pnl_pct: float,
                 exit_reason: str, capital_after: float) -> bool:
    """Notify when a position is closed."""
    color = 0x26A69A if pnl > 0 else 0xEF5350
    emoji = "✅" if pnl > 0 else "❌"

    reason_jp = {
        "take_profit": "利確 🎯",
        "stop_loss": "損切り 🛑",
        "trailing_stop": "トレーリングストップ 📈",
        "reversal": "ドテン 🔄",
    }.get(exit_reason, exit_reason)

    embed = {
        "title": f"{emoji} 決済 {direction.upper()} {symbol}",
        "color": color,
        "fields": [
            {"name": "📍 エントリー", "value": f"${entry_price:,.2f}", "inline": True},
            {"name": "🏁 決済価格", "value": f"${exit_price:,.2f}", "inline": True},
            {"name": "💰 損益", "value": f"${pnl:+,.2f} ({pnl_pct:+.2f}%)", "inline": True},
            {"name": "📝 理由", "value": reason_jp, "inline": True},
            {"name": "💼 残高", "value": f"${capital_after:,.2f}", "inline": True},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return _send_discord(embeds=[embed])


def notify_daily_summary(capital: float, initial_capital: float,
                         positions: dict, journal: list) -> bool:
    """Send daily portfolio summary."""
    pnl = capital - initial_capital
    pnl_pct = pnl / initial_capital * 100
    color = 0x26A69A if pnl >= 0 else 0xEF5350

    fields = [
        {"name": "💼 資金", "value": f"${capital:,.2f}", "inline": True},
        {"name": "📈 損益", "value": f"${pnl:+,.2f} ({pnl_pct:+.2f}%)", "inline": True},
        {"name": "📌 ポジション", "value": f"{len(positions)}件", "inline": True},
    ]

    if positions:
        pos_text = "\n".join(
            f"{pos['direction'].upper()} {sym} @ ${pos['entry_price']:,.2f}"
            for sym, pos in positions.items()
        )
        fields.append({"name": "【保有中】", "value": pos_text, "inline": False})

    if journal:
        wins = sum(1 for t in journal if t["pnl"] > 0)
        total = len(journal)
        total_pnl = sum(t["pnl"] for t in journal)
        fields.append({"name": "【累計成績】", "value": (
            f"トレード: {total}回\n"
            f"勝率: {wins/total*100:.0f}% ({wins}W/{total-wins}L)\n"
            f"累計損益: ${total_pnl:+,.2f}"
        ), "inline": False})

    embed = {
        "title": "📊 日次レポート",
        "color": color,
        "fields": fields,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return _send_discord(embeds=[embed])


def notify_scan_start(symbols: list[str], capital: float, positions: int) -> bool:
    """Notify when a scan cycle starts."""
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    return _send_discord(
        content=f"🔍 スキャン開始 ({now}) | 通貨: {', '.join(symbols)} | "
                f"資金: ${capital:,.2f} | ポジション: {positions}件"
    )


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing Discord notification...")
    embed = {
        "title": "🤖 Trading Bot 通知テスト",
        "description": "Discord通知が正常に動作しています！",
        "color": 0x00D4FF,
        "fields": [
            {"name": "ステータス", "value": "✅ 接続成功", "inline": True},
            {"name": "時刻", "value": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), "inline": True},
        ],
    }
    success = _send_discord(embeds=[embed])
    if success:
        print("✅ Discord notification sent successfully!")
    else:
        print("❌ Failed. Check DISCORD_WEBHOOK_URL in .env")
