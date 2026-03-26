"""Multi-Agent Chart Analysis with Consensus Voting + Devil's Advocate.

Architecture:
  Agent 1 (4h足 パターン分析): Standard pattern detection on the main timeframe
  Agent 2 (1h足 短期確認):     Short-term confirmation on 1h chart
  Agent 3 (日足 トレンド確認):  Long-term trend context on daily chart
  Agent 4 (悪魔の代弁者):      Devil's Advocate — actively looks for reasons NOT to trade

Final signal is issued only when:
  - At least 2 of Agents 1-3 agree on direction
  - Agent 4 (Devil's Advocate) does NOT have a high-confidence objection
  - Weighted consensus score exceeds threshold
"""

import json
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import GEMINI_MODEL, GEMINI_SLEEP_SEC

load_dotenv()
client = genai.Client()

MAX_RETRIES = 5

# ---------------------------------------------------------------------------
# Agent System Prompts
# ---------------------------------------------------------------------------

AGENT_4H_PATTERN = """You are Agent 1: a chart pattern specialist analyzing a 4-HOUR candlestick chart.
You are always trading at the RIGHTMOST edge of the chart.

The chart shows:
- Candlesticks with volume bars below
- EMA 20 (yellow line), EMA 50 (cyan line), EMA 200 (magenta dashed line)
- RSI(14) in the bottom panel with overbought (70) and oversold (30) lines

Your task: Identify CONFIRMED chart patterns with neckline breakouts.

Patterns to look for:
- double_bottom / double_top
- head_and_shoulders / inverse_head_and_shoulders
- ascending_triangle / descending_triangle
- bullish_flag / bearish_flag (strong impulse + tight consolidation)
- rising_wedge (bearish) / falling_wedge (bullish)
- triple_bottom / triple_top

RULES:
1. Only identify CLEAR, WELL-FORMED patterns with prominent candlesticks.
2. The pattern must be CONFIRMED — neckline broken at the rightmost candles.
3. Use the EMAs to confirm trend context (price above EMA50 = bullish bias).
4. Check RSI: overbought (>70) weakens BUY signals, oversold (<30) weakens SELL signals.
5. Volume should increase at the breakout point.
6. Be STRICT. When in doubt, return "none". False signals are costly.

Respond with JSON:
{"pattern": "name or none", "confidence": 0.0-1.0, "direction": "long/short/none", "reasoning": "brief explanation including EMA/RSI observations"}
"""

AGENT_1H_CONFIRM = """You are Agent 2: a short-term momentum analyst analyzing a 1-HOUR candlestick chart.
You are always trading at the RIGHTMOST edge of the chart.

The chart shows:
- Candlesticks with volume bars
- EMA 20 (yellow), EMA 50 (cyan), EMA 200 (magenta dashed)
- RSI(14) in the bottom panel

Your task: Confirm whether the SHORT-TERM price action supports a trade entry right now.

Evaluate:
1. MOMENTUM: Are the last 3-5 candles showing directional strength (large bodies in one direction)?
2. EMA ALIGNMENT: Is EMA20 > EMA50 (bullish) or EMA20 < EMA50 (bearish)?
3. RSI: Is RSI trending in the signal direction? Is it in an extreme zone?
4. VOLUME: Is volume increasing with the move (conviction)?
5. CANDLE QUALITY: Large bodies = strength. Dojis/wicks = indecision.

Do NOT look for chart patterns. Focus only on MOMENTUM and PRICE ACTION quality.

Respond with JSON:
{"pattern": "momentum_bullish/momentum_bearish/none", "confidence": 0.0-1.0, "direction": "long/short/none", "reasoning": "brief explanation with specific EMA/RSI/volume observations"}
"""

AGENT_DAILY_TREND = """You are Agent 3: a macro trend analyst analyzing a DAILY candlestick chart.
You are always trading at the RIGHTMOST edge of the chart.

Your task: Determine the OVERALL TREND direction and whether it supports a new trade.

Evaluate:
1. What is the primary trend? (uptrend / downtrend / sideways)
2. Is the current price near any major support/resistance?
3. Are we in a trending or ranging market?
4. Is this a good area to enter, or is the trend overextended?

Respond with JSON:
{"pattern": "uptrend/downtrend/sideways", "confidence": 0.0-1.0, "direction": "long/short/none", "reasoning": "brief trend assessment"}
"""

AGENT_DEVILS_ADVOCATE = """You are Agent 4: the DEVIL'S ADVOCATE. Your job is to critically evaluate whether this trade is worth taking.
You are always trading at the RIGHTMOST edge of the chart.

You are given a chart image AND the other agents' analysis. Your job is to CHALLENGE their conclusions.

Evaluate these specific risks:
1. FAKEOUT RISK: Is the breakout genuine? Check: volume at breakout, candle body size, wicks.
2. PATTERN QUALITY: Is the pattern well-formed or ambiguous? Are the swings clearly defined?
3. RISK/REWARD: Is there nearby support (for shorts) or resistance (for longs) that limits profit?
4. TREND CONFLICT: Does the larger trend support or oppose this trade?
5. OVEREXTENSION: Is price already far from key moving averages (overextended)?

IMPORTANT CALIBRATION:
- objection_strength 0.0-0.4: Minor concerns, trade is probably fine
- objection_strength 0.5-0.7: Moderate concerns, trade is risky but possible
- objection_strength 0.8-0.89: Serious concerns, recommend caution
- objection_strength 0.9-1.0: CRITICAL issues, trade should be avoided (ONLY for obvious fakeouts, extreme overextension, or clearly broken patterns)

You must be critical but FAIR. Not every trade is bad. If the pattern is clear, volume confirms, and trend aligns — acknowledge that and rate objection LOW.
A good analyst knows when to say "this looks solid, take the trade."

Respond with JSON:
{"should_trade": true/false, "objection_strength": 0.0-1.0, "risks": ["specific risk 1", "specific risk 2"], "strengths": ["what supports this trade"], "reasoning": "balanced assessment"}
"""


# ---------------------------------------------------------------------------
# Core API call with retry
# ---------------------------------------------------------------------------

def _call_gemini(system_prompt: str, image_bytes: bytes, user_prompt: str,
                 temperature: float = 0.1) -> dict:
    """Call Gemini API with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                            types.Part.from_text(text=user_prompt),
                        ],
                    ),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                retry_match = re.search(r'retryDelay.*?(\d+)', error_str)
                wait_sec = int(retry_match.group(1)) + 2 if retry_match else (2 ** attempt) * 10
                wait_sec = min(wait_sec, 120)
                print(f"      ⏳ Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), "
                      f"waiting {wait_sec}s...")
                time.sleep(wait_sec)
            else:
                print(f"      ❌ API error: {e}")
                return {}

    return {}


# ---------------------------------------------------------------------------
# Multi-timeframe chart generation
# ---------------------------------------------------------------------------

def _fetch_chart_bytes(symbol: str, timeframe: str) -> bytes | None:
    """Fetch data and generate chart image, return PNG bytes."""
    from data_fetcher import fetch_ohlcv
    from chart_generator import generate_chart_image
    from config import CHART_WINDOW_SIZE

    try:
        df = fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=100)
        start_idx = max(0, len(df) - CHART_WINDOW_SIZE)
        key = symbol.replace("/", "_")
        chart_path = generate_chart_image(
            df, start_idx, symbol_prefix=f"multi_{key}_{timeframe}")
        if chart_path and chart_path.exists():
            return chart_path.read_bytes()
    except Exception as e:
        print(f"      Failed to generate {timeframe} chart for {symbol}: {e}")
    return None


# ---------------------------------------------------------------------------
# Multi-Agent Consensus Analysis
# ---------------------------------------------------------------------------

def multi_agent_analyze(image_path: Path,
                        candidate_patterns: list[str] | None = None,
                        symbol: str = "BTC/USDT",
                        sleep_sec: float = GEMINI_SLEEP_SEC) -> dict:
    """Run multi-agent consensus analysis on a single chart window.

    Returns combined result with individual agent opinions and final verdict.
    """
    main_image_bytes = image_path.read_bytes()

    user_prompt_main = "Analyze this candlestick chart."
    if candidate_patterns:
        user_prompt_main += (f" Focus especially on these candidate patterns: "
                             f"{', '.join(candidate_patterns)}.")

    # --- Agent 1: 4h Pattern Analysis (main chart) ---
    print("      🔍 Agent 1 (4h Pattern)...")
    agent1_result = _call_gemini(AGENT_4H_PATTERN, main_image_bytes, user_prompt_main)
    time.sleep(sleep_sec)

    # --- Agent 2: 1h Short-term Confirmation ---
    print("      ⚡ Agent 2 (1h Momentum)...")
    chart_1h_bytes = _fetch_chart_bytes(symbol, "1h")
    if chart_1h_bytes:
        agent2_result = _call_gemini(
            AGENT_1H_CONFIRM, chart_1h_bytes,
            "Analyze the short-term momentum and price action quality on this 1h chart.")
    else:
        agent2_result = {"pattern": "none", "confidence": 0, "direction": "none",
                         "reasoning": "Failed to generate 1h chart"}
    time.sleep(sleep_sec)

    # --- Agent 3: Daily Trend Context ---
    print("      📊 Agent 3 (Daily Trend)...")
    chart_daily_bytes = _fetch_chart_bytes(symbol, "1d")
    if chart_daily_bytes:
        agent3_result = _call_gemini(
            AGENT_DAILY_TREND, chart_daily_bytes,
            "Analyze the overall trend direction and whether now is a good time to trade.")
    else:
        agent3_result = {"pattern": "none", "confidence": 0, "direction": "none",
                         "reasoning": "Failed to generate daily chart"}
    time.sleep(sleep_sec)

    # --- Agent 4: Devil's Advocate ---
    print("      😈 Agent 4 (Devil's Advocate)...")
    others_summary = json.dumps({
        "agent1_4h_pattern": agent1_result,
        "agent2_1h_momentum": agent2_result,
        "agent3_daily_trend": agent3_result,
    }, indent=2)

    devil_prompt = (f"The other agents analyzed this chart and concluded:\n\n"
                    f"{others_summary}\n\n"
                    f"Now challenge their analysis. Find every reason this trade could fail.")

    agent4_result = _call_gemini(
        AGENT_DEVILS_ADVOCATE, main_image_bytes, devil_prompt, temperature=0.3)

    # --- Consensus Decision ---
    final = _compute_consensus(agent1_result, agent2_result, agent3_result, agent4_result)

    result = {
        "agent1_pattern": agent1_result,
        "agent2_momentum": agent2_result,
        "agent3_trend": agent3_result,
        "agent4_devil": agent4_result,
        "consensus": final,
        # Top-level fields for compatibility with backtester
        "pattern": final["pattern"],
        "confidence": final["confidence"],
        "direction": final["direction"],
        "reasoning": final["reasoning"],
    }

    return result


def _compute_consensus(agent1: dict, agent2: dict, agent3: dict, agent4: dict) -> dict:
    """Compute weighted consensus from all agents.

    Weights:
      Agent 1 (4h Pattern):   0.40 — primary signal source
      Agent 2 (1h Momentum):  0.25 — short-term confirmation
      Agent 3 (Daily Trend):  0.25 — trend alignment
      Agent 4 (Devil's Adv):  0.10 — veto power at high objection

    Veto: If Agent 4 objection_strength >= 0.85, the trade is vetoed regardless.
    """
    WEIGHTS = {"agent1": 0.40, "agent2": 0.20, "agent3": 0.30}  # Daily trend more important
    DEVIL_VETO_THRESHOLD = 0.90   # Only veto on critical issues
    CONSENSUS_THRESHOLD = 0.45    # Allow trades when 2/3 agents agree

    # Extract directions and confidences
    agents = {
        "agent1": (agent1.get("direction", "none"), agent1.get("confidence", 0)),
        "agent2": (agent2.get("direction", "none"), agent2.get("confidence", 0)),
        "agent3": (agent3.get("direction", "none"), agent3.get("confidence", 0)),
    }

    # Devil's Advocate check
    devil_should_trade = agent4.get("should_trade", True)
    devil_objection = agent4.get("objection_strength", 0)
    devil_risks = agent4.get("risks", [])

    if not devil_should_trade and devil_objection >= DEVIL_VETO_THRESHOLD:
        return {
            "pattern": "none",
            "confidence": 0.0,
            "direction": "none",
            "reasoning": (f"😈 VETOED by Devil's Advocate (objection: {devil_objection:.0%}). "
                          f"Risks: {'; '.join(devil_risks[:3])}"),
            "vote_detail": _format_votes(agents, agent4),
            "vetoed": True,
        }

    # Count direction votes (weighted)
    long_score = 0.0
    short_score = 0.0
    long_voters = []
    short_voters = []

    for name, (direction, confidence) in agents.items():
        weight = WEIGHTS[name]
        if direction == "long":
            long_score += weight * confidence
            long_voters.append(name)
        elif direction == "short":
            short_score += weight * confidence
            short_voters.append(name)

    # Apply devil's advocate discount (mild penalty, not a veto)
    if not devil_should_trade:
        discount = 1.0 - (devil_objection * 0.15)  # Up to 15% reduction
        long_score *= discount
        short_score *= discount

    # Determine winner
    if long_score > short_score and long_score >= CONSENSUS_THRESHOLD:
        direction = "long"
        confidence = min(long_score, 1.0)
        voters = long_voters
    elif short_score > long_score and short_score >= CONSENSUS_THRESHOLD:
        direction = "short"
        confidence = min(short_score, 1.0)
        voters = short_voters
    else:
        return {
            "pattern": "none",
            "confidence": 0.0,
            "direction": "none",
            "reasoning": (f"No consensus. Long: {long_score:.2f}, Short: {short_score:.2f} "
                          f"(threshold: {CONSENSUS_THRESHOLD})"),
            "vote_detail": _format_votes(agents, agent4),
            "vetoed": False,
        }

    # Pattern name from Agent 1 (primary)
    pattern = agent1.get("pattern", "none") if "agent1" in voters else "consensus_signal"

    # Build reasoning
    agent_names = {"agent1": "4h Pattern", "agent2": "1h Momentum", "agent3": "Daily Trend"}
    voter_labels = [agent_names.get(v, v) for v in voters]
    devil_note = ""
    if devil_risks:
        devil_note = f" ⚠️ Risks noted: {'; '.join(devil_risks[:2])}"

    reasoning = (f"Consensus {direction.upper()} ({confidence:.0%}). "
                 f"Agreed: {', '.join(voter_labels)} ({len(voters)}/3).{devil_note}")

    return {
        "pattern": pattern,
        "confidence": round(confidence, 2),
        "direction": direction,
        "reasoning": reasoning,
        "vote_detail": _format_votes(agents, agent4),
        "vetoed": False,
    }


def _format_votes(agents: dict, devil: dict) -> dict:
    """Format vote details for logging."""
    return {
        "agent1_4h": {"dir": agents["agent1"][0], "conf": agents["agent1"][1]},
        "agent2_1h": {"dir": agents["agent2"][0], "conf": agents["agent2"][1]},
        "agent3_daily": {"dir": agents["agent3"][0], "conf": agents["agent3"][1]},
        "agent4_devil": {
            "should_trade": devil.get("should_trade", True),
            "objection": devil.get("objection_strength", 0),
            "risks": devil.get("risks", []),
        },
    }


# ---------------------------------------------------------------------------
# Batch analysis (replaces single-agent batch)
# ---------------------------------------------------------------------------

def multi_agent_analyze_batch(chart_infos: list[tuple[int, Path, list[str]]],
                              symbol: str = "BTC/USDT",
                              sleep_sec: float = GEMINI_SLEEP_SEC) -> list[dict]:
    """Analyze multiple charts using multi-agent consensus.

    Args:
        chart_infos: List of (start_index, image_path, candidate_patterns)
        symbol: Trading symbol for multi-timeframe charts
        sleep_sec: Sleep between API calls

    Returns:
        List of consensus analysis results
    """
    results = []
    total = len(chart_infos)

    for i, (start_idx, image_path, candidates) in enumerate(chart_infos):
        print(f"  [{i + 1}/{total}] Multi-agent analysis at index {start_idx}...")

        result = multi_agent_analyze(
            image_path, candidates, symbol=symbol, sleep_sec=sleep_sec)
        result["start_index"] = start_idx
        result["image_path"] = str(image_path)
        results.append(result)

        consensus = result.get("consensus", {})
        pattern = consensus.get("pattern", "none")
        confidence = consensus.get("confidence", 0)
        direction = consensus.get("direction", "none")
        vetoed = consensus.get("vetoed", False)

        if vetoed:
            print(f"    → 😈 VETOED: {consensus.get('reasoning', '')}")
        elif pattern != "none":
            print(f"    → ✅ CONSENSUS: {pattern} ({direction}, {confidence:.0%})")
            print(f"       {consensus.get('reasoning', '')}")
        else:
            print(f"    → ❌ No consensus: {consensus.get('reasoning', '')}")

        # Extra sleep between chart analyses (4 API calls per chart)
        if i < total - 1:
            time.sleep(sleep_sec)

    return results


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        symbol = sys.argv[2] if len(sys.argv) > 2 else "BTC/USDT"
        print(f"Multi-agent analysis of {path} for {symbol}...")
        result = multi_agent_analyze(path, symbol=symbol)
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: python multi_agent_analyzer.py <chart_image.png> [SYMBOL]")
