"""News Sentiment Analysis — uses Gemini to analyze crypto news.

Fetches recent crypto news from free APIs and uses Gemini to determine
whether the sentiment is bullish, bearish, or neutral for each symbol.

This is where LLMs actually excel — language understanding, not chart images.

Usage:
    from sentiment import get_sentiment
    result = get_sentiment("BTC/USDT")
    # {"label": "bullish", "score": 0.7, "modifier": 1.15, "headlines": [...]}
"""

import json
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

# CryptoPanic API (free tier: 5 requests/min)
CRYPTOPANIC_URL = "https://cryptopanic.com/api/free/v1/posts/"
CRYPTOPANIC_TOKEN = os.getenv("CRYPTOPANIC_TOKEN", "")

# Fallback: CoinGecko trending + news (no key needed)
COINGECKO_URL = "https://api.coingecko.com/api/v3"

# Symbol to search terms
SYMBOL_KEYWORDS = {
    "BTC/USDT": ["bitcoin", "BTC"],
    "ETH/USDT": ["ethereum", "ETH"],
    "XRP/USDT": ["ripple", "XRP"],
    "SOL/USDT": ["solana", "SOL"],
    "BNB/USDT": ["binance coin", "BNB"],
}


def _fetch_news_cryptopanic(symbol: str, limit: int = 10) -> list:
    """Fetch news from CryptoPanic API."""
    if not CRYPTOPANIC_TOKEN:
        return []

    keywords = SYMBOL_KEYWORDS.get(symbol, [])
    currency = keywords[1] if len(keywords) > 1 else ""

    try:
        params = {
            "auth_token": CRYPTOPANIC_TOKEN,
            "currencies": currency,
            "kind": "news",
            "filter": "important",
            "public": "true",
        }
        resp = requests.get(CRYPTOPANIC_URL, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])[:limit]
            return [{"title": r.get("title", ""), "source": r.get("source", {}).get("title", "")}
                    for r in results]
    except Exception:
        pass
    return []


def _fetch_news_fallback(symbol: str, limit: int = 10) -> list:
    """Fetch news headlines via web search fallback."""
    keywords = SYMBOL_KEYWORDS.get(symbol, [symbol])
    query = keywords[0] if keywords else symbol

    # Use CoinGecko's simple endpoint to at least get market context
    try:
        coin_id = {
            "BTC/USDT": "bitcoin",
            "ETH/USDT": "ethereum",
            "XRP/USDT": "ripple",
            "SOL/USDT": "solana",
            "BNB/USDT": "binancecoin",
        }.get(symbol, "bitcoin")

        resp = requests.get(
            f"{COINGECKO_URL}/coins/{coin_id}",
            params={"localization": "false", "tickers": "false",
                    "market_data": "true", "community_data": "false",
                    "developer_data": "false"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            desc = data.get("description", {}).get("en", "")[:500]
            market = data.get("market_data", {})
            price_change_24h = market.get("price_change_percentage_24h", 0)
            price_change_7d = market.get("price_change_percentage_7d", 0)

            return [{
                "title": f"{query} 24h change: {price_change_24h:+.1f}%, 7d change: {price_change_7d:+.1f}%",
                "source": "CoinGecko",
            }]
    except Exception:
        pass
    return []


def _analyze_with_gemini(headlines: list, symbol: str) -> dict:
    """Use Gemini to analyze sentiment of news headlines."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client()

        news_text = "\n".join([f"- {h['title']} ({h.get('source', '')})" for h in headlines])
        keywords = SYMBOL_KEYWORDS.get(symbol, [symbol])
        coin_name = keywords[0]

        prompt = f"""Analyze these recent {coin_name} news headlines and determine the overall market sentiment.

Headlines:
{news_text}

Respond with JSON only:
{{"label": "bullish/bearish/neutral", "score": 0.0-1.0, "reasoning": "brief explanation"}}

Rules:
- "bullish" = positive news that would push price up
- "bearish" = negative news that would push price down
- "neutral" = mixed or no clear direction
- score: 0.0 = extremely bearish, 0.5 = neutral, 1.0 = extremely bullish
- Be conservative. Most news is neutral. Only rate bullish/bearish for clearly directional news.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"  Sentiment analysis error: {e}")
        return {"label": "neutral", "score": 0.5, "reasoning": f"Error: {e}"}


def get_sentiment(symbol: str) -> dict:
    """Get news sentiment for a symbol.

    Returns:
        {
            "label": "bullish" | "bearish" | "neutral",
            "score": 0.0-1.0,
            "modifier": float,  # Multiply signal strength by this
            "headlines": list,
            "reasoning": str,
        }
    """
    # Fetch news
    headlines = _fetch_news_cryptopanic(symbol)
    if not headlines:
        headlines = _fetch_news_fallback(symbol)

    if not headlines:
        return {
            "label": "neutral",
            "score": 0.5,
            "modifier": 1.0,
            "headlines": [],
            "reasoning": "No news data available",
        }

    # Analyze with Gemini
    result = _analyze_with_gemini(headlines, symbol)
    label = result.get("label", "neutral")
    score = result.get("score", 0.5)

    # Convert to modifier
    # bullish (score > 0.6): boost signal strength up to 1.2x
    # bearish (score < 0.4): reduce signal strength down to 0.7x
    # neutral: no change (1.0x)
    if score > 0.6:
        modifier = 1.0 + (score - 0.6) * 0.5  # Max 1.2 at score=1.0
    elif score < 0.4:
        modifier = 1.0 - (0.4 - score) * 0.75  # Min 0.7 at score=0.0
    else:
        modifier = 1.0

    return {
        "label": label,
        "score": round(score, 2),
        "modifier": round(modifier, 2),
        "headlines": [h["title"] for h in headlines[:5]],
        "reasoning": result.get("reasoning", ""),
    }


def get_all_sentiments(symbols: list) -> dict:
    """Get sentiment for multiple symbols with rate limiting."""
    results = {}
    for symbol in symbols:
        results[symbol] = get_sentiment(symbol)
        time.sleep(1)  # Rate limit
    return results


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    symbols = ["BTC/USDT", "XRP/USDT"]
    for symbol in symbols:
        print(f"\n{'=' * 40}")
        print(f"Sentiment for {symbol}")
        print(f"{'=' * 40}")
        result = get_sentiment(symbol)
        print(f"  Label: {result['label']}")
        print(f"  Score: {result['score']}")
        print(f"  Modifier: {result['modifier']}")
        print(f"  Reasoning: {result['reasoning']}")
        for h in result.get("headlines", []):
            print(f"  - {h}")
