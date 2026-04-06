"""X (Twitter) 自動投稿モジュール"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def post_to_x(
    articles: list[dict],
    site_url: str = "https://ichtyosis.vercel.app",
) -> bool:
    """
    キュレーション結果をXに投稿する。
    X API credentialsが未設定の場合はスキップ。
    """
    api_key = os.environ.get("X_API_KEY")
    api_secret = os.environ.get("X_API_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        logger.info("X API credentials not set, skipping X post")
        return False

    try:
        import tweepy
    except ImportError:
        logger.warning("tweepy not installed, skipping X post")
        return False

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

        tweet_text = _compose_tweet(articles, site_url)
        if not tweet_text:
            logger.info("No articles to tweet about")
            return False

        client.create_tweet(text=tweet_text)
        logger.info(f"X post successful ({len(tweet_text)} chars)")
        return True

    except Exception as e:
        logger.error(f"X post failed: {e}")
        return False


def _compose_tweet(articles: list[dict], site_url: str) -> Optional[str]:
    """280文字以内のツイートを組み立てる"""
    if not articles:
        return None

    from datetime import datetime

    today = datetime.now().strftime("%m/%d")

    hashtags = "#魚鱗癬 #ichthyosis #希少疾患 #皮膚科"
    footer = f"\n\n{site_url}\n{hashtags}"
    footer_len = _tweet_length(footer)

    # ヘッダー
    header = f"【{today} 魚鱗癬ニュース】{len(articles)}件の最新情報\n"
    header_len = _tweet_length(header)

    # 残り文字数で記事タイトルを追加
    remaining = 280 - header_len - footer_len
    body_lines = []

    for article in articles[:3]:
        title = article.get("title_ja") or article.get("original_title", "")
        if not title:
            continue
        line = f"・{title}"
        line_len = _tweet_length(line + "\n")
        if remaining - line_len < 0:
            # タイトルを短縮
            while _tweet_length(line + "…\n") > remaining and len(line) > 5:
                line = line[:-1]
            line += "…"
            line_len = _tweet_length(line + "\n")
            if remaining - line_len >= 0:
                body_lines.append(line)
            break
        body_lines.append(line)
        remaining -= line_len

    if not body_lines:
        return f"{header.strip()}{footer}"

    body = "\n".join(body_lines)
    return f"{header}{body}{footer}"


def _tweet_length(text: str) -> int:
    """
    Twitterの文字数カウント（簡易版）。
    日本語文字は2文字、ASCII/URLは特殊ルール。
    簡易的に: ASCII=1, それ以外=2, URL=23固定
    """
    import re

    # URLを23文字としてカウント
    url_pattern = re.compile(r"https?://\S+")
    urls = url_pattern.findall(text)
    text_without_urls = url_pattern.sub("", text)

    count = 0
    for char in text_without_urls:
        if ord(char) <= 0x7F:
            count += 1  # ASCII
        else:
            count += 2  # CJK etc.

    count += len(urls) * 23  # Each URL = 23 chars on Twitter

    return count
