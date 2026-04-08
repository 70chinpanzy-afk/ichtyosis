"""Visualization: equity curve, trade log, and pattern review HTML."""

import json
from pathlib import Path
import pandas as pd
from config import RESULT_DIR


def generate_equity_chart_html(equity_df: pd.DataFrame, trade_df: pd.DataFrame,
                               stats: dict, output_path: Path | None = None) -> Path:
    """Generate an HTML file with equity curve and trade statistics."""
    if output_path is None:
        output_path = RESULT_DIR / "backtest_results.html"

    # Prepare equity data for Plotly
    timestamps = equity_df["timestamp"].astype(str).tolist()
    equities = equity_df["equity"].tolist()

    # Trade markers
    if not trade_df.empty:
        buy_times = trade_df[trade_df["direction"] == "long"]["entry_time"].astype(str).tolist()
        sell_times = trade_df[trade_df["direction"] == "short"]["entry_time"].astype(str).tolist()
    else:
        buy_times = []
        sell_times = []

    stats_html = ""
    for key, val in stats.items():
        label = key.replace("_", " ").title()
        stats_html += f"<tr><td>{label}</td><td><strong>{val}</strong></td></tr>\n"

    trade_rows = ""
    if not trade_df.empty:
        for _, row in trade_df.iterrows():
            pnl_class = "positive" if row["pnl"] > 0 else "negative"
            trade_rows += f"""<tr>
                <td>{row['entry_time']}</td>
                <td>{row['exit_time']}</td>
                <td>{row['direction']}</td>
                <td>${row['entry_price']:,.2f}</td>
                <td>${row['exit_price']:,.2f}</td>
                <td class="{pnl_class}">${row['pnl']:,.2f}</td>
                <td>{row['exit_reason']}</td>
            </tr>\n"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Trading Bot Backtest Results</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 20px; background: #1a1a2e; color: #e0e0e0; }}
    h1, h2 {{ color: #00d4ff; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    #equity-chart {{ width: 100%; height: 400px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
    th, td {{ border: 1px solid #333; padding: 8px 12px; text-align: left; }}
    th {{ background: #16213e; color: #00d4ff; }}
    tr:nth-child(even) {{ background: #16213e; }}
    .positive {{ color: #26a69a; font-weight: bold; }}
    .negative {{ color: #ef5350; font-weight: bold; }}
    .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 20px 0; }}
    .stat-card {{ background: #16213e; border-radius: 8px; padding: 15px; text-align: center; }}
    .stat-card .value {{ font-size: 24px; color: #00d4ff; font-weight: bold; }}
    .stat-card .label {{ font-size: 12px; color: #888; margin-top: 5px; }}
</style>
</head>
<body>
<div class="container">
<h1>Trading Bot Backtest Results</h1>

<div class="stats-grid">
    <div class="stat-card"><div class="value">{stats.get('total_trades', 0)}</div><div class="label">Total Trades</div></div>
    <div class="stat-card"><div class="value">{stats.get('win_rate', 0)}%</div><div class="label">Win Rate</div></div>
    <div class="stat-card"><div class="value">{stats.get('profit_factor', 0)}</div><div class="label">Profit Factor</div></div>
    <div class="stat-card"><div class="value">{stats.get('total_return_pct', 0)}%</div><div class="label">Total Return</div></div>
    <div class="stat-card"><div class="value">{stats.get('max_drawdown_pct', 0)}%</div><div class="label">Max Drawdown</div></div>
    <div class="stat-card"><div class="value">{stats.get('sharpe_ratio', 0)}</div><div class="label">Sharpe Ratio</div></div>
</div>

<h2>Equity Curve</h2>
<div id="equity-chart"></div>

<h2>Trade Log</h2>
<table>
<thead><tr><th>Entry</th><th>Exit</th><th>Direction</th><th>Entry Price</th><th>Exit Price</th><th>PnL</th><th>Exit Reason</th></tr></thead>
<tbody>{trade_rows}</tbody>
</table>

<h2>Statistics</h2>
<table>
<thead><tr><th>Metric</th><th>Value</th></tr></thead>
<tbody>{stats_html}</tbody>
</table>

</div>

<script>
var trace = {{
    x: {json.dumps(timestamps)},
    y: {json.dumps(equities)},
    type: 'scatter',
    mode: 'lines',
    line: {{color: '#00d4ff', width: 2}},
    fill: 'tozeroy',
    fillcolor: 'rgba(0, 212, 255, 0.1)'
}};

Plotly.newPlot('equity-chart', [trace], {{
    paper_bgcolor: '#1a1a2e',
    plot_bgcolor: '#16213e',
    font: {{color: '#e0e0e0'}},
    xaxis: {{gridcolor: '#333'}},
    yaxis: {{gridcolor: '#333', title: 'Equity ($)'}},
    margin: {{t: 20}}
}});
</script>
</body>
</html>"""

    output_path.write_text(html)
    print(f"Backtest results saved to {output_path}")
    return output_path


def generate_pattern_review_html(signals: list[dict], output_path: Path | None = None) -> Path:
    """Generate HTML to review Gemini's pattern judgments with chart images."""
    if output_path is None:
        output_path = RESULT_DIR / "pattern_review.html"

    cards = ""
    for sig in signals:
        pattern = sig.get("pattern", "none")
        confidence = sig.get("confidence", 0)
        direction = sig.get("direction", "none")
        reasoning = sig.get("reasoning", "")
        image_path = sig.get("image_path", "")
        start_idx = sig.get("start_index", 0)

        if pattern == "none":
            border_color = "#555"
            badge_color = "#555"
        elif direction == "long":
            border_color = "#26a69a"
            badge_color = "#26a69a"
        else:
            border_color = "#ef5350"
            badge_color = "#ef5350"

        # Make image path relative
        if image_path:
            rel_path = Path(image_path).relative_to(Path(image_path).parent.parent) if image_path else ""
        else:
            rel_path = ""

        cards += f"""
        <div class="card" style="border-color: {border_color}">
            <div class="card-header">
                <span class="badge" style="background: {badge_color}">{pattern}</span>
                <span class="confidence">Confidence: {confidence:.0%}</span>
                <span class="direction">{direction}</span>
                <span class="index">Index: {start_idx}</span>
            </div>
            <img src="../{rel_path}" alt="Chart {start_idx}" onerror="this.style.display='none'">
            <p class="reasoning">{reasoning}</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Pattern Review</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 20px; background: #1a1a2e; color: #e0e0e0; }}
    h1 {{ color: #00d4ff; }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 15px; }}
    .card {{ background: #16213e; border: 2px solid; border-radius: 8px; padding: 10px; }}
    .card-header {{ display: flex; gap: 10px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }}
    .badge {{ color: white; padding: 3px 10px; border-radius: 12px; font-size: 13px; font-weight: bold; }}
    .confidence, .direction, .index {{ font-size: 12px; color: #888; }}
    .card img {{ width: 100%; border-radius: 4px; }}
    .reasoning {{ font-size: 13px; color: #aaa; margin-top: 8px; }}
    .filter-bar {{ margin: 20px 0; display: flex; gap: 10px; }}
    .filter-btn {{ background: #16213e; color: #e0e0e0; border: 1px solid #333; padding: 8px 16px; border-radius: 6px; cursor: pointer; }}
    .filter-btn.active {{ background: #00d4ff; color: #1a1a2e; }}
</style>
</head>
<body>
<div class="container">
<h1>Pattern Review ({len(signals)} analyses)</h1>

<div class="filter-bar">
    <button class="filter-btn active" onclick="filter('all')">All</button>
    <button class="filter-btn" onclick="filter('detected')">Detected</button>
    <button class="filter-btn" onclick="filter('long')">Long</button>
    <button class="filter-btn" onclick="filter('short')">Short</button>
</div>

<div class="grid" id="grid">{cards}</div>

</div>
<script>
function filter(type) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.card').forEach(card => {{
        const badge = card.querySelector('.badge').textContent;
        const dir = card.querySelector('.direction').textContent;
        if (type === 'all') card.style.display = '';
        else if (type === 'detected') card.style.display = badge === 'none' ? 'none' : '';
        else card.style.display = dir === type ? '' : 'none';
    }});
}}
</script>
</body>
</html>"""

    output_path.write_text(html)
    print(f"Pattern review saved to {output_path}")
    return output_path
