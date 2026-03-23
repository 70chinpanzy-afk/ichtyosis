"""Main orchestrator: Multi-symbol pipeline.

Fetch → Chart → Filter → Gemini → Backtest → Visualize
for each symbol, then produce a combined report.
"""

import argparse
import json
from pathlib import Path

from data_fetcher import fetch_ohlcv
from chart_generator import generate_all_charts
from numerical_filter import prefilter_window
from gemini_analyzer import analyze_charts_batch
from backtester import run_backtest, compute_stats
from visualizer import generate_equity_chart_html, generate_pattern_review_html
from config import (
    CHART_WINDOW_SIZE, CHART_SLIDE_STEP, RESULT_DIR, SYMBOLS, TIMEFRAME,
)


def _symbol_key(symbol: str) -> str:
    """Convert 'BTC/USDT' → 'BTC_USDT' for filenames."""
    return symbol.replace("/", "_")


def run_single_symbol(symbol: str, num_candles: int = 1000,
                      skip_gemini: bool = False, timeframe: str = TIMEFRAME) -> dict | None:
    """Run full pipeline for one symbol. Returns stats dict or None."""
    key = _symbol_key(symbol)
    print(f"\n{'#' * 60}")
    print(f"  SYMBOL: {symbol}")
    print(f"{'#' * 60}")

    # Phase 1: Fetch data
    print(f"\n[{symbol}] Phase 1: Fetching OHLCV data...")
    try:
        df = fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=num_candles)
    except Exception as e:
        print(f"[{symbol}] ❌ Failed to fetch data: {e}")
        return None

    # Phase 2: Generate chart images
    print(f"[{symbol}] Phase 2: Generating chart images...")
    charts = generate_all_charts(df, CHART_WINDOW_SIZE, CHART_SLIDE_STEP,
                                 symbol_prefix=key)

    # Phase 3: Numerical pre-filtering
    print(f"[{symbol}] Phase 3: Numerical pre-filtering...")
    candidates = []
    for start_idx, filepath in charts:
        window = df.iloc[start_idx:start_idx + CHART_WINDOW_SIZE]
        patterns = prefilter_window(window)
        if patterns:
            candidates.append((start_idx, filepath, patterns))

    total_charts = len(charts)
    filtered = len(candidates)
    reduction = (1 - filtered / total_charts) * 100 if total_charts > 0 else 0
    print(f"[{symbol}] Pre-filter: {filtered}/{total_charts} charts passed "
          f"({reduction:.0f}% reduction)")

    if not candidates:
        print(f"[{symbol}] No pattern candidates found.")
        return None

    # Phase 4: Gemini Vision analysis
    cache_path = RESULT_DIR / f"gemini_results_{key}.json"

    if skip_gemini:
        print(f"[{symbol}] Phase 4: Loading cached Gemini results...")
        if cache_path.exists():
            with open(cache_path) as f:
                signals = json.load(f)
            print(f"[{symbol}] Loaded {len(signals)} cached results")
        else:
            print(f"[{symbol}] ❌ No cached results found. Run without --skip-gemini.")
            return None
    else:
        print(f"[{symbol}] Phase 4: Running Gemini Vision API ({len(candidates)} images)...")
        signals = analyze_charts_batch(candidates)
        with open(cache_path, "w") as f:
            json.dump(signals, f, indent=2, default=str)
        print(f"[{symbol}] Cached {len(signals)} results")

    # Tag each signal with symbol
    for sig in signals:
        sig["symbol"] = symbol

    detected = [s for s in signals if s.get("pattern", "none") != "none"]
    print(f"[{symbol}] Detected patterns: {len(detected)}/{len(signals)}")
    for s in detected:
        print(f"  idx={s['start_index']:4d}  {s['pattern']:30s}  "
              f"conf={s['confidence']:.0%}  dir={s['direction']}")

    # Phase 5: Backtesting
    print(f"[{symbol}] Phase 5: Backtesting...")
    trade_df, equity_df = run_backtest(
        df, signals, min_confidence=0.60,
        sl_mult=1.0, tp_mult=2.0, commission=0.001,
        use_ema_filter=False, dedup_signals=False,
    )
    stats = compute_stats(trade_df, equity_df)

    print(f"[{symbol}] Results: {stats.get('total_trades', 0)} trades, "
          f"WR={stats.get('win_rate', 0)}%, "
          f"Return={stats.get('total_return_pct', 0):+.2f}%, "
          f"PF={stats.get('profit_factor', 0)}")

    # Phase 6: Per-symbol visualizations
    print(f"[{symbol}] Phase 6: Generating visualizations...")
    generate_equity_chart_html(
        equity_df, trade_df, stats,
        output_path=RESULT_DIR / f"backtest_{key}.html",
    )
    generate_pattern_review_html(
        signals,
        output_path=RESULT_DIR / f"review_{key}.html",
    )

    stats["symbol"] = symbol
    stats["signals"] = signals
    stats["trade_df"] = trade_df
    stats["equity_df"] = equity_df

    return stats


def run_multi_symbol(symbols: list[str] | None = None, num_candles: int = 1000,
                     skip_gemini: bool = False, timeframe: str = TIMEFRAME):
    """Run pipeline for multiple symbols and generate combined report."""
    if symbols is None:
        symbols = SYMBOLS

    print("=" * 60)
    print(f"  MULTI-SYMBOL PIPELINE: {', '.join(symbols)}")
    print(f"  Candles: {num_candles} | Timeframe: {timeframe}")
    print("=" * 60)

    all_stats = []
    for symbol in symbols:
        stats = run_single_symbol(symbol, num_candles, skip_gemini, timeframe)
        if stats:
            all_stats.append(stats)

    if not all_stats:
        print("\n❌ No results for any symbol.")
        return

    # Combined summary
    print("\n" + "=" * 60)
    print("  COMBINED RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'Symbol':<12} {'Trades':>6} {'WR%':>6} {'Return%':>9} {'PF':>6} "
          f"{'MaxDD%':>8} {'Sharpe':>7} {'Final$':>10}")
    print("-" * 70)

    total_trades = 0
    total_pnl = 0.0

    for s in all_stats:
        sym = s["symbol"]
        print(f"{sym:<12} {s['total_trades']:>6} {s['win_rate']:>6.1f} "
              f"{s['total_return_pct']:>+9.2f} {s['profit_factor']:>6.2f} "
              f"{s['max_drawdown_pct']:>8.2f} {s['sharpe_ratio']:>7.2f} "
              f"${s['final_capital']:>9,.2f}")
        total_trades += s["total_trades"]
        total_pnl += s["final_capital"] - s["initial_capital"]

    print("-" * 70)
    capital_per_symbol = all_stats[0]["initial_capital"]
    total_capital = capital_per_symbol * len(all_stats)
    combined_return = total_pnl / total_capital * 100
    print(f"{'COMBINED':<12} {total_trades:>6} {'':>6} {combined_return:>+9.2f} "
          f"{'':>6} {'':>8} {'':>7} "
          f"${total_capital + total_pnl:>9,.2f}")

    # Generate combined HTML report
    _generate_combined_html(all_stats)

    print(f"\nCombined report: {RESULT_DIR}/combined_results.html")
    for s in all_stats:
        key = _symbol_key(s["symbol"])
        print(f"  {s['symbol']}: results/{f'backtest_{key}.html'}")

    return all_stats


def _generate_combined_html(all_stats: list[dict]):
    """Generate a combined HTML dashboard for all symbols."""
    rows_html = ""
    for s in all_stats:
        ret_class = "positive" if s["total_return_pct"] > 0 else "negative"
        rows_html += f"""<tr>
            <td><strong>{s['symbol']}</strong></td>
            <td>{s['total_trades']}</td>
            <td>{s['win_rate']:.1f}%</td>
            <td class="{ret_class}">{s['total_return_pct']:+.2f}%</td>
            <td>{s['profit_factor']:.2f}</td>
            <td>{s['max_drawdown_pct']:.2f}%</td>
            <td>{s['sharpe_ratio']:.2f}</td>
            <td>${s['final_capital']:,.2f}</td>
        </tr>\n"""

    # Per-symbol cards with iframe links
    cards_html = ""
    for s in all_stats:
        key = _symbol_key(s["symbol"])
        ret_class = "positive" if s["total_return_pct"] > 0 else "negative"
        cards_html += f"""
        <div class="card">
            <h3>{s['symbol']}</h3>
            <div class="stats-row">
                <div class="stat"><span class="value">{s['total_trades']}</span><span class="label">Trades</span></div>
                <div class="stat"><span class="value">{s['win_rate']:.1f}%</span><span class="label">Win Rate</span></div>
                <div class="stat"><span class="value {ret_class}">{s['total_return_pct']:+.2f}%</span><span class="label">Return</span></div>
                <div class="stat"><span class="value">{s['profit_factor']:.2f}</span><span class="label">PF</span></div>
                <div class="stat"><span class="value">{s['sharpe_ratio']:.2f}</span><span class="label">Sharpe</span></div>
            </div>
            <div class="links">
                <a href="backtest_{key}.html" target="_blank">📊 Backtest</a>
                <a href="review_{key}.html" target="_blank">🔍 Pattern Review</a>
            </div>
        </div>
        """

    total_capital = sum(s["initial_capital"] for s in all_stats)
    total_final = sum(s["final_capital"] for s in all_stats)
    total_pnl = total_final - total_capital
    combined_return = total_pnl / total_capital * 100
    total_trades = sum(s["total_trades"] for s in all_stats)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Multi-Symbol Trading Bot Results</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 20px; background: #1a1a2e; color: #e0e0e0; }}
    h1, h2, h3 {{ color: #00d4ff; }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 20px 0; }}
    .summary-card {{ background: #16213e; border-radius: 8px; padding: 18px; text-align: center; }}
    .summary-card .value {{ font-size: 28px; color: #00d4ff; font-weight: bold; }}
    .summary-card .label {{ font-size: 12px; color: #888; margin-top: 5px; }}
    .positive {{ color: #26a69a !important; }}
    .negative {{ color: #ef5350 !important; }}
    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
    th, td {{ border: 1px solid #333; padding: 10px 14px; text-align: left; }}
    th {{ background: #16213e; color: #00d4ff; }}
    tr:nth-child(even) {{ background: #16213e; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 15px; margin: 20px 0; }}
    .card {{ background: #16213e; border-radius: 10px; padding: 20px; border: 1px solid #333; }}
    .card h3 {{ margin-top: 0; }}
    .stats-row {{ display: flex; justify-content: space-between; margin: 15px 0; }}
    .stat {{ text-align: center; }}
    .stat .value {{ display: block; font-size: 18px; font-weight: bold; color: #00d4ff; }}
    .stat .label {{ display: block; font-size: 11px; color: #888; }}
    .links {{ display: flex; gap: 10px; }}
    .links a {{ color: #00d4ff; text-decoration: none; background: #0a3d62; padding: 6px 14px; border-radius: 6px; font-size: 13px; }}
    .links a:hover {{ background: #1e5f8a; }}
</style>
</head>
<body>
<div class="container">
<h1>🤖 Multi-Symbol Trading Bot Results</h1>

<div class="summary-grid">
    <div class="summary-card"><div class="value">{len(all_stats)}</div><div class="label">Symbols</div></div>
    <div class="summary-card"><div class="value">{total_trades}</div><div class="label">Total Trades</div></div>
    <div class="summary-card"><div class="value {'positive' if combined_return > 0 else 'negative'}">{combined_return:+.2f}%</div><div class="label">Combined Return</div></div>
    <div class="summary-card"><div class="value">${total_capital:,.0f}</div><div class="label">Total Capital</div></div>
    <div class="summary-card"><div class="value {'positive' if total_pnl > 0 else 'negative'}">${total_pnl:+,.2f}</div><div class="label">Total PnL</div></div>
    <div class="summary-card"><div class="value">${total_final:,.2f}</div><div class="label">Final Capital</div></div>
</div>

<h2>Per-Symbol Summary</h2>
<table>
<thead><tr><th>Symbol</th><th>Trades</th><th>Win Rate</th><th>Return</th><th>PF</th><th>Max DD</th><th>Sharpe</th><th>Final Capital</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>

<h2>Per-Symbol Details</h2>
<div class="cards">{cards_html}</div>

</div>
</body>
</html>"""

    output_path = RESULT_DIR / "combined_results.html"
    output_path.write_text(html)
    print(f"Combined report saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Symbol Trading Bot Pipeline")
    parser.add_argument("--candles", type=int, default=1000,
                        help="Number of candles to fetch per symbol (default: 1000)")
    parser.add_argument("--skip-gemini", action="store_true",
                        help="Use cached Gemini results")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="Symbols to analyze (default: all in config)")
    parser.add_argument("--timeframe", default=TIMEFRAME,
                        help="Timeframe (default: 4h)")
    args = parser.parse_args()

    symbols = args.symbols
    if symbols:
        # Normalize: "BTCUSDT" → "BTC/USDT"
        symbols = [s if "/" in s else f"{s[:3]}/{s[3:]}" for s in symbols]

    run_multi_symbol(
        symbols=symbols,
        num_candles=args.candles,
        skip_gemini=args.skip_gemini,
        timeframe=args.timeframe,
    )
