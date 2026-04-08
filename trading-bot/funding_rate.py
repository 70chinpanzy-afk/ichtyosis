"""Funding Rate Monitor — detects arbitrage opportunities.

Monitors perpetual futures funding rates across exchanges.
When funding rate is extremely positive (longs pay shorts),
the bot can short futures + long spot for risk-free yield.

This module only monitors and signals — actual execution requires
futures-capable exchange accounts.

Usage:
    from funding_rate import get_funding_rates, find_arb_opportunities
    rates = get_funding_rates()
    opps = find_arb_opportunities(rates)
"""

import time
from datetime import datetime, timezone

import requests


# Binance public API (no auth needed for funding rates)
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"

# Symbols to monitor
MONITORED_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT",
]

# Thresholds
HIGH_FUNDING_THRESHOLD = 0.03   # 0.03% per 8h = ~0.09%/day = ~33%/year
EXTREME_FUNDING_THRESHOLD = 0.05  # Very high — strong arb signal


def get_funding_rates() -> list:
    """Fetch current funding rates from Binance Futures.

    Returns list of dicts: [{symbol, funding_rate, next_funding_time, mark_price}]
    """
    try:
        resp = requests.get(BINANCE_FUNDING_URL, timeout=10)
        if resp.status_code != 200:
            print(f"  Funding rate API error: {resp.status_code}")
            return []

        data = resp.json()
        results = []
        for item in data:
            symbol = item.get("symbol", "")
            if symbol in MONITORED_SYMBOLS:
                rate = float(item.get("lastFundingRate", 0))
                results.append({
                    "symbol": symbol,
                    "funding_rate": round(rate * 100, 4),  # Convert to %
                    "funding_rate_raw": rate,
                    "mark_price": float(item.get("markPrice", 0)),
                    "next_funding_time": int(item.get("nextFundingTime", 0)),
                    "annualized_pct": round(rate * 100 * 3 * 365, 2),  # 3 fundings/day
                })
        return results
    except Exception as e:
        print(f"  Funding rate fetch error: {e}")
        return []


def find_arb_opportunities(rates: list, threshold_pct: float = HIGH_FUNDING_THRESHOLD) -> list:
    """Find funding rate arbitrage opportunities.

    When funding rate is very positive:
      - Longs pay shorts → short futures, long spot = earn funding
    When funding rate is very negative:
      - Shorts pay longs → long futures, short spot (if possible)

    Returns list of opportunities with action details.
    """
    opportunities = []
    for r in rates:
        rate = r["funding_rate"]
        abs_rate = abs(rate)

        if abs_rate < threshold_pct:
            continue

        is_extreme = abs_rate >= EXTREME_FUNDING_THRESHOLD
        daily_yield = abs_rate * 3  # 3 funding periods per day
        annual_yield = daily_yield * 365

        if rate > 0:
            # Positive funding: longs pay shorts
            action = "short_futures_long_spot"
            description = f"Short futures + Long spot (earn {daily_yield:.3f}%/day)"
        else:
            # Negative funding: shorts pay longs
            action = "long_futures_short_spot"
            description = f"Long futures + Short spot (earn {daily_yield:.3f}%/day)"

        opportunities.append({
            "symbol": r["symbol"],
            "funding_rate_pct": rate,
            "daily_yield_pct": round(daily_yield, 4),
            "annual_yield_pct": round(annual_yield, 2),
            "action": action,
            "description": description,
            "mark_price": r["mark_price"],
            "strength": "EXTREME" if is_extreme else "HIGH",
            "next_funding_time": r["next_funding_time"],
        })

    # Sort by absolute yield (best first)
    opportunities.sort(key=lambda x: abs(x["daily_yield_pct"]), reverse=True)
    return opportunities


def format_funding_report(rates: list, opportunities: list) -> str:
    """Format funding rate data for Discord notification."""
    lines = ["**📊 Funding Rate Report**\n"]

    for r in sorted(rates, key=lambda x: abs(x["funding_rate"]), reverse=True):
        emoji = "🔴" if abs(r["funding_rate"]) >= HIGH_FUNDING_THRESHOLD else "⚪"
        lines.append(
            f"{emoji} {r['symbol']}: {r['funding_rate']:+.4f}% "
            f"(年率 {r['annualized_pct']:+.1f}%)"
        )

    if opportunities:
        lines.append("\n**💰 Arbitrage Opportunities:**")
        for opp in opportunities:
            lines.append(
                f"{'🚨' if opp['strength'] == 'EXTREME' else '⚡'} "
                f"{opp['symbol']}: {opp['description']} "
                f"(年率 {opp['annual_yield_pct']:.1f}%)"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Fetching funding rates from Binance...")
    rates = get_funding_rates()

    if not rates:
        print("No data fetched.")
    else:
        print(f"\n{'Symbol':<12} {'Rate%':>10} {'Annual%':>10}")
        print("-" * 35)
        for r in sorted(rates, key=lambda x: abs(x["funding_rate"]), reverse=True):
            print(f"{r['symbol']:<12} {r['funding_rate']:>+10.4f} {r['annualized_pct']:>+10.1f}")

        opps = find_arb_opportunities(rates)
        if opps:
            print(f"\n💰 Arbitrage opportunities:")
            for o in opps:
                print(f"  {o['strength']}: {o['symbol']} — {o['description']}")
        else:
            print("\nNo arbitrage opportunities above threshold.")
