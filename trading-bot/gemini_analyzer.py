"""Use Gemini Vision API to analyze chart images for pattern confirmation."""

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

SYSTEM_PROMPT = """You are an expert technical analyst specializing in candlestick chart pattern recognition.
You are analyzing a candlestick chart image. You are always trading at the rightmost edge of the chart.

Your task is to identify whether the chart contains any of these patterns:
- double_bottom: Two roughly equal lows with a peak between them. The pattern is confirmed when price breaks above the neckline (the peak between the two lows).
- double_top: Two roughly equal highs with a trough between them. The pattern is confirmed when price breaks below the neckline.
- head_and_shoulders: Three peaks where the middle peak is the highest. Confirmed when price breaks below the neckline.
- inverse_head_and_shoulders: Three troughs where the middle trough is the lowest. Confirmed when price breaks above the neckline.
- ascending_triangle: Flat resistance line with rising support. Bullish breakout expected.
- descending_triangle: Flat support line with falling resistance. Bearish breakout expected.

IMPORTANT RULES:
1. Only identify CLEAR, WELL-FORMED patterns with large/prominent candlesticks.
2. The pattern must be CONFIRMED - meaning the neckline has been broken at the rightmost part of the chart.
3. You are trading at the rightmost candle. Only signal if the breakout is happening NOW or just happened.
4. Be STRICT. When in doubt, return no pattern. False signals are costly.
5. Consider the overall trend context.

Respond ONLY with valid JSON in this exact format:
{
  "pattern": "pattern_name or none",
  "confidence": 0.0 to 1.0,
  "direction": "long" or "short" or "none",
  "reasoning": "brief explanation"
}
"""

MAX_RETRIES = 5


def analyze_chart(image_path: Path, candidate_patterns: list[str] | None = None) -> dict:
    """Analyze a chart image using Gemini Vision API.

    Includes automatic retry with exponential backoff for rate limit errors.
    """
    user_prompt = "Analyze this candlestick chart for trading patterns."
    if candidate_patterns:
        user_prompt += f" Focus especially on these candidate patterns: {', '.join(candidate_patterns)}."

    image_bytes = image_path.read_bytes()

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
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            result = json.loads(response.text)
            return result

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                # Extract retry delay from error message
                retry_match = re.search(r'retryDelay.*?(\d+)', error_str)
                wait_sec = int(retry_match.group(1)) + 2 if retry_match else (2 ** attempt) * 10
                wait_sec = min(wait_sec, 120)
                print(f"    ⏳ Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait_sec}s...")
                time.sleep(wait_sec)
            else:
                print(f"  Gemini API error: {e}")
                return {"pattern": "none", "confidence": 0.0, "direction": "none",
                        "reasoning": f"API error: {e}"}

    print(f"  Max retries exceeded")
    return {"pattern": "none", "confidence": 0.0, "direction": "none",
            "reasoning": "Max retries exceeded"}


def analyze_charts_batch(chart_infos: list[tuple[int, Path, list[str]]],
                         sleep_sec: float = GEMINI_SLEEP_SEC) -> list[dict]:
    """Analyze multiple chart images sequentially with rate limiting.

    Args:
        chart_infos: List of (start_index, image_path, candidate_patterns)
        sleep_sec: Sleep between API calls

    Returns:
        List of analysis results with start_index attached
    """
    results = []
    total = len(chart_infos)

    for i, (start_idx, image_path, candidates) in enumerate(chart_infos):
        print(f"  [{i + 1}/{total}] Analyzing chart at index {start_idx} "
              f"(candidates: {candidates})...")

        result = analyze_chart(image_path, candidates)
        result["start_index"] = start_idx
        result["image_path"] = str(image_path)
        results.append(result)

        pattern = result.get("pattern", "none")
        confidence = result.get("confidence", 0)
        direction = result.get("direction", "none")
        print(f"    → Pattern: {pattern}, Confidence: {confidence:.2f}, Direction: {direction}")

        if i < total - 1:
            time.sleep(sleep_sec)

    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        result = analyze_chart(path)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python gemini_analyzer.py <chart_image_path>")
