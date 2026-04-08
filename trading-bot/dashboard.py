"""Streamlit real-time monitoring dashboard for AI Trading Bot."""

import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st

# Ensure the trading-bot directory is on the path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from data_fetcher import fetch_ohlcv
from chart_generator import generate_chart_image
from numerical_filter import prefilter_window
from gemini_analyzer import analyze_chart
from backtester import run_backtest, compute_stats, calculate_atr, calculate_ema
from config import (
    SYMBOL, TIMEFRAME, CHART_WINDOW_SIZE, INITIAL_CAPITAL,
    ATR_SL_MULTIPLIER, ATR_TP_MULTIPLIER,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Trading Bot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
_defaults = {
    "signals": [],
    "scan_results": [],
    "last_scan_time": None,
    "discord_webhook": "",
    "line_token": "",
    "trade_df": pd.DataFrame(),
    "equity_df": pd.DataFrame(),
    "backtest_stats": {},
    "ohlcv_df": pd.DataFrame(),
}
for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ---------------------------------------------------------------------------
# Notification helper
# ---------------------------------------------------------------------------

def send_notification(message: str, discord_webhook: str | None = None,
                      line_token: str | None = None) -> None:
    """Send alert notifications to Discord and/or LINE Notify."""
    if discord_webhook:
        try:
            requests.post(discord_webhook, json={"content": message}, timeout=10)
        except Exception as e:
            st.warning(f"Discord notification failed: {e}")

    if line_token:
        try:
            requests.post(
                "https://notify-api.line.me/api/notify",
                headers={"Authorization": f"Bearer {line_token}"},
                data={"message": message},
                timeout=10,
            )
        except Exception as e:
            st.warning(f"LINE notification failed: {e}")

# ---------------------------------------------------------------------------
# Cached data fetcher
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner="Fetching OHLCV data...")
def cached_fetch_ohlcv(symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
    """Fetch OHLCV with 5-minute cache."""
    return fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)


@st.cache_data(ttl=60, show_spinner="Fetching live price...")
def fetch_live_price(symbol: str) -> float | None:
    """Fetch current price from Binance via ccxt."""
    try:
        import ccxt
        exchange = ccxt.binance({"enableRateLimit": True})
        ticker = exchange.fetch_ticker(symbol)
        return ticker["last"]
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Scan logic
# ---------------------------------------------------------------------------

def run_scan(symbol: str, timeframe: str, min_confidence: float,
             sl_mult: float, tp_mult: float) -> None:
    """Run a full scan cycle: fetch -> chart -> filter -> Gemini -> backtest."""
    try:
        with st.spinner("Fetching latest candles..."):
            df = cached_fetch_ohlcv(symbol, timeframe, limit=100)
            st.session_state["ohlcv_df"] = df

        # Generate chart for the last 60 candles
        window_start = max(0, len(df) - CHART_WINDOW_SIZE)
        window_df = df.iloc[window_start:].copy()

        with st.spinner("Running numerical pre-filter..."):
            candidates = prefilter_window(window_df)

        new_signals: list[dict] = []

        if candidates:
            with st.spinner(f"Generating chart & calling Gemini API (candidates: {candidates})..."):
                chart_path = generate_chart_image(df, window_start)
                if chart_path and chart_path.exists():
                    result = analyze_chart(chart_path, candidates)
                    result["start_index"] = window_start
                    result["image_path"] = str(chart_path)
                    result["scan_time"] = datetime.utcnow().isoformat()

                    pattern = result.get("pattern", "none")
                    confidence = result.get("confidence", 0.0)

                    if pattern != "none" and confidence >= min_confidence:
                        result["status"] = "Active"
                        new_signals.append(result)

                        # Send notification
                        direction = result.get("direction", "?")
                        msg = (
                            f"[AI Trading Bot] {direction.upper()} signal detected!\n"
                            f"Pattern: {pattern} | Confidence: {confidence:.0%}\n"
                            f"Symbol: {symbol} | Timeframe: {timeframe}\n"
                            f"Reasoning: {result.get('reasoning', 'N/A')}"
                        )
                        send_notification(
                            msg,
                            discord_webhook=st.session_state.get("discord_webhook") or None,
                            line_token=st.session_state.get("line_token") or None,
                        )
                    else:
                        result["status"] = "Filtered"
                        new_signals.append(result)
        else:
            st.info("No pattern candidates detected by numerical pre-filter.")

        # Update session state
        st.session_state["scan_results"] = new_signals
        st.session_state["signals"] = st.session_state["signals"] + [
            s for s in new_signals if s.get("status") == "Active"
        ]
        st.session_state["last_scan_time"] = datetime.utcnow().isoformat()

        # Run backtest on accumulated signals
        if st.session_state["signals"]:
            with st.spinner("Running backtest..."):
                trade_df, equity_df = run_backtest(
                    df, st.session_state["signals"],
                    min_confidence=min_confidence,
                    sl_mult=sl_mult,
                    tp_mult=tp_mult,
                )
                stats = compute_stats(trade_df, equity_df)
                st.session_state["trade_df"] = trade_df
                st.session_state["equity_df"] = equity_df
                st.session_state["backtest_stats"] = stats

        st.success("Scan complete!")

    except Exception as e:
        st.error(f"Scan failed: {e}")

# ---------------------------------------------------------------------------
# Plotly chart builders
# ---------------------------------------------------------------------------

def build_candlestick_chart(df: pd.DataFrame, signals: list[dict]) -> go.Figure:
    """Build an interactive candlestick chart with volume, EMA50, and signal markers."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
        subplot_titles=("Price", "Volume"),
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df["open"], high=df["high"],
            low=df["low"], close=df["close"], name="OHLC",
            increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
        ),
        row=1, col=1,
    )

    # EMA 50
    ema50 = calculate_ema(df["close"], 50)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=ema50, mode="lines",
            name="EMA50", line=dict(color="#ffa726", width=1.5),
        ),
        row=1, col=1,
    )

    # Volume bars
    colors = [
        "#26a69a" if c >= o else "#ef5350"
        for c, o in zip(df["close"], df["open"])
    ]
    fig.add_trace(
        go.Bar(x=df.index, y=df["volume"], name="Volume",
               marker_color=colors, opacity=0.5),
        row=2, col=1,
    )

    # Signal markers
    for sig in signals:
        if sig.get("pattern", "none") == "none":
            continue
        idx = sig.get("start_index", 0) + CHART_WINDOW_SIZE - 1
        if idx >= len(df):
            continue
        ts = df.index[idx]
        price = df["close"].iloc[idx]
        direction = sig.get("direction", "none")
        if direction == "long":
            fig.add_trace(
                go.Scatter(
                    x=[ts], y=[price * 0.998],
                    mode="markers", name="Long Signal",
                    marker=dict(symbol="triangle-up", size=14, color="#00e676"),
                    text=sig.get("pattern", ""), hoverinfo="text+x+y",
                    showlegend=False,
                ),
                row=1, col=1,
            )
        elif direction == "short":
            fig.add_trace(
                go.Scatter(
                    x=[ts], y=[price * 1.002],
                    mode="markers", name="Short Signal",
                    marker=dict(symbol="triangle-down", size=14, color="#ff1744"),
                    text=sig.get("pattern", ""), hoverinfo="text+x+y",
                    showlegend=False,
                ),
                row=1, col=1,
            )

    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        margin=dict(l=50, r=50, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(type="category", row=2, col=1, showticklabels=False)

    return fig


def build_equity_curve(equity_df: pd.DataFrame) -> go.Figure:
    """Build equity curve plotly chart."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=equity_df["timestamp"], y=equity_df["equity"],
            mode="lines", name="Equity",
            line=dict(color="#42a5f5", width=2),
            fill="tozeroy", fillcolor="rgba(66,165,245,0.1)",
        )
    )
    fig.update_layout(
        height=400,
        template="plotly_dark",
        yaxis_title="Equity ($)",
        xaxis_title="Time",
        margin=dict(l=50, r=50, t=30, b=30),
    )
    return fig

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Settings")

    all_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
    symbol = st.selectbox("Symbol", all_symbols, index=0)
    timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=1)

    st.subheader("Risk Parameters")
    sl_mult = st.slider("ATR SL Multiplier", 0.5, 3.0, ATR_SL_MULTIPLIER, 0.1)
    tp_mult = st.slider("ATR TP Multiplier", 0.5, 5.0, ATR_TP_MULTIPLIER, 0.1)
    min_confidence = st.slider("Min Confidence", 0.5, 1.0, 0.6, 0.05)

    st.divider()

    if st.button("🔍 Scan Current", use_container_width=True, type="primary"):
        run_scan(symbol, timeframe, min_confidence, sl_mult, tp_mult)

    if st.button("🔍 Scan ALL Symbols", use_container_width=True):
        for sym in all_symbols:
            run_scan(sym, timeframe, min_confidence, sl_mult, tp_mult)

    st.divider()

    st.subheader("Notifications")
    st.session_state["discord_webhook"] = st.text_input(
        "Discord Webhook URL",
        value=st.session_state.get("discord_webhook", ""),
        type="password",
    )
    st.session_state["line_token"] = st.text_input(
        "LINE Notify Token",
        value=st.session_state.get("line_token", ""),
        type="password",
    )

    st.divider()
    if st.session_state["last_scan_time"]:
        st.caption(f"Last scan: {st.session_state['last_scan_time']}")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

col_title, col_price, col_refresh = st.columns([4, 2, 1])
with col_title:
    st.title("🤖 AI Trading Bot Dashboard")
with col_price:
    live_price = fetch_live_price(symbol)
    if live_price is not None:
        st.metric(label=f"{symbol} Price", value=f"${live_price:,.2f}")
    else:
        st.metric(label=f"{symbol} Price", value="N/A")
with col_refresh:
    st.write("")  # spacing
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# Auto-refresh (5 min)
# ---------------------------------------------------------------------------
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5 * 60 * 1000, limit=None, key="auto_refresh")
except ImportError:
    pass  # Graceful fallback if streamlit-autorefresh is not installed

# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------
tab_chart, tab_signals, tab_perf, tab_paper = st.tabs(["📈 Live Chart", "🚨 Signals", "📊 Performance", "📝 Paper Trade"])

# --- Tab 1: Live Chart ---
with tab_chart:
    try:
        df = st.session_state.get("ohlcv_df")
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            with st.spinner("Loading chart data..."):
                df = cached_fetch_ohlcv(symbol, timeframe, limit=100)
                st.session_state["ohlcv_df"] = df

        signals_for_chart = st.session_state.get("signals", [])
        fig = build_candlestick_chart(df, signals_for_chart)
        st.plotly_chart(fig, use_container_width=True)

        # Quick stats row
        if not df.empty:
            c1, c2, c3, c4 = st.columns(4)
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            change = latest["close"] - prev["close"]
            change_pct = change / prev["close"] * 100

            atr = calculate_atr(df)
            current_atr = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0

            c1.metric("Close", f"${latest['close']:,.2f}",
                       f"{change_pct:+.2f}%")
            c2.metric("24h High", f"${latest['high']:,.2f}")
            c3.metric("24h Low", f"${latest['low']:,.2f}")
            c4.metric("ATR(14)", f"${current_atr:,.2f}")
    except Exception as e:
        st.error(f"Chart error: {e}")

# --- Tab 2: Signals ---
with tab_signals:
    all_signals = st.session_state.get("scan_results", []) + st.session_state.get("signals", [])
    # Deduplicate by scan_time + pattern
    seen = set()
    unique_signals = []
    for s in all_signals:
        key = (s.get("scan_time", ""), s.get("pattern", ""), s.get("start_index", ""))
        if key not in seen:
            seen.add(key)
            unique_signals.append(s)

    if unique_signals:
        rows = []
        for s in unique_signals:
            rows.append({
                "Time": s.get("scan_time", "N/A"),
                "Pattern": s.get("pattern", "none"),
                "Direction": s.get("direction", "none"),
                "Confidence": s.get("confidence", 0.0),
                "Status": s.get("status", "N/A"),
            })
        sig_df = pd.DataFrame(rows)

        def color_direction(val):
            if val == "long":
                return "color: #00e676; font-weight: bold"
            elif val == "short":
                return "color: #ff1744; font-weight: bold"
            return ""

        styled = sig_df.style.applymap(color_direction, subset=["Direction"])
        styled = styled.format({"Confidence": "{:.0%}"})
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Expandable chart images
        for s in unique_signals:
            img_path = s.get("image_path")
            if img_path and Path(img_path).exists():
                pattern = s.get("pattern", "none")
                direction = s.get("direction", "none")
                conf = s.get("confidence", 0)
                with st.expander(f"{pattern} ({direction}) - {conf:.0%} confidence"):
                    st.image(str(img_path), use_container_width=True)
                    st.caption(s.get("reasoning", ""))
    else:
        st.info("No signals detected yet. Click **Scan Now** in the sidebar to run a scan.")

# --- Tab 3: Performance ---
with tab_perf:
    stats = st.session_state.get("backtest_stats", {})
    trade_df = st.session_state.get("trade_df", pd.DataFrame())
    equity_df = st.session_state.get("equity_df", pd.DataFrame())

    if stats and stats.get("total_trades", 0) > 0:
        # Metric cards
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Win Rate", f"{stats.get('win_rate', 0):.1f}%")
        m2.metric("Profit Factor", f"{stats.get('profit_factor', 0):.2f}")
        m3.metric("Total Return", f"{stats.get('total_return_pct', 0):.2f}%")
        m4.metric("Max Drawdown", f"{stats.get('max_drawdown_pct', 0):.2f}%")
        m5.metric("Sharpe Ratio", f"{stats.get('sharpe_ratio', 0):.2f}")

        st.divider()

        # Equity curve
        if not equity_df.empty:
            st.subheader("Equity Curve")
            eq_fig = build_equity_curve(equity_df)
            st.plotly_chart(eq_fig, use_container_width=True)

        # Trade log
        if not trade_df.empty:
            st.subheader("Trade Log")

            display_df = trade_df.copy()
            for col in ["entry_time", "exit_time"]:
                if col in display_df.columns:
                    display_df[col] = display_df[col].astype(str)

            def color_pnl(val):
                try:
                    v = float(val)
                    if v > 0:
                        return "color: #00e676"
                    elif v < 0:
                        return "color: #ff1744"
                except (ValueError, TypeError):
                    pass
                return ""

            styled_trades = display_df.style.applymap(color_pnl, subset=["pnl"])
            styled_trades = styled_trades.format({
                "entry_price": "${:,.2f}",
                "exit_price": "${:,.2f}",
                "pnl": "${:,.2f}",
                "capital_after": "${:,.2f}",
            })
            st.dataframe(styled_trades, use_container_width=True, hide_index=True)
    else:
        st.info("No backtest data available. Run a scan first to generate signals and backtest results.")

# --- Tab 4: Paper Trade ---
with tab_paper:
    from paper_trader import PaperTrader, JOURNAL_PATH, STATE_PATH

    st.subheader("📝 Paper Trading")

    # Load current state
    paper_state_file = STATE_PATH
    paper_journal_file = JOURNAL_PATH

    pc1, pc2 = st.columns(2)
    with pc1:
        if st.button("▶️ Run One Scan (All Symbols)", use_container_width=True, type="primary"):
            trader = PaperTrader(sl_mult=sl_mult, tp_mult=tp_mult, min_confidence=min_confidence)
            with st.spinner("Running paper trade scan on all symbols..."):
                trader.scan_all()
            st.success("Scan complete!")
            st.rerun()
    with pc2:
        if st.button("🗑️ Reset Paper Trading", use_container_width=True):
            trader = PaperTrader()
            trader.reset()
            st.success("Paper trading state reset!")
            st.rerun()

    # Display state
    import json as _json
    if paper_state_file.exists():
        with open(paper_state_file) as _f:
            pstate = _json.load(_f)

        capital = pstate.get("capital", 10000)
        init_cap = pstate.get("initial_capital", 10000)
        pnl = capital - init_cap
        pnl_pct = pnl / init_cap * 100

        ps1, ps2, ps3, ps4 = st.columns(4)
        ps1.metric("Capital", f"${capital:,.2f}")
        ps2.metric("P&L", f"${pnl:+,.2f}")
        ps3.metric("Return", f"{pnl_pct:+.2f}%")
        positions = pstate.get("positions", {})
        ps4.metric("Open Positions", f"{len(positions)}")

        # Open positions
        if positions:
            st.subheader("Open Positions")
            pos_rows = []
            for sym, pos in positions.items():
                pos_rows.append({
                    "Symbol": sym,
                    "Direction": pos["direction"].upper(),
                    "Entry": f"${pos['entry_price']:,.2f}",
                    "SL": f"${pos['stop_loss']:,.2f}",
                    "TP": f"${pos['take_profit']:,.2f}",
                    "Pattern": pos.get("pattern", ""),
                    "Since": pos.get("entry_time", "")[:19],
                })
            st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No paper trading state yet. Click **Run One Scan** to start.")

    # Journal
    if paper_journal_file.exists():
        with open(paper_journal_file) as _f:
            journal = _json.load(_f)
        if journal:
            st.subheader(f"Trade Journal ({len(journal)} trades)")
            jdf = pd.DataFrame(journal)

            # Summary stats
            if len(jdf) > 0:
                wins = len(jdf[jdf["pnl"] > 0])
                losses = len(jdf[jdf["pnl"] <= 0])
                wr = wins / len(jdf) * 100
                total_pnl = jdf["pnl"].sum()

                js1, js2, js3, js4 = st.columns(4)
                js1.metric("Win Rate", f"{wr:.1f}%")
                js2.metric("Wins / Losses", f"{wins}W / {losses}L")
                js3.metric("Total PnL", f"${total_pnl:+,.2f}")
                avg_pnl = jdf["pnl"].mean()
                js4.metric("Avg PnL/Trade", f"${avg_pnl:+,.2f}")

            # Trade table
            display_cols = ["symbol", "direction", "entry_price", "exit_price",
                            "pnl", "pnl_pct", "exit_reason", "pattern",
                            "entry_time", "exit_time"]
            available = [c for c in display_cols if c in jdf.columns]
            show_jdf = jdf[available].copy()

            def color_pnl_paper(val):
                try:
                    v = float(val)
                    return "color: #00e676" if v > 0 else "color: #ff1744"
                except (ValueError, TypeError):
                    return ""

            if "pnl" in show_jdf.columns:
                styled_j = show_jdf.style.applymap(color_pnl_paper, subset=["pnl"])
                st.dataframe(styled_j, use_container_width=True, hide_index=True)
            else:
                st.dataframe(show_jdf, use_container_width=True, hide_index=True)
