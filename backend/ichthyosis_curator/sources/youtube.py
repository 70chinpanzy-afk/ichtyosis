"""YouTube Data API v3 による患者・家族のスキンケア動画収集

患者本人・家族が投稿する魚鱗癬のスキンケアルーティン、
保湿剤レビュー、日常生活の工夫などの動画を収集する。

必要な環境変数:
    YOUTUBE_API_KEY: Google Cloud Console で発行した API キー

API の無料枠:
    1日 10,000 ユニット（search.list = 100 ユニット/回）
    → 1日最大 100 回検索可能（本実装では 8〜10 回程度使用）
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from ichthyosis_curator.schemas import RawArticle

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v={video_id}"

# 検索クエリ（患者・家族の体験動画を狙い打ち）
SEARCH_QUERIES = [
    # 英語（患者体験・ケア動画）
    "ichthyosis skincare routine",
    "ichthyosis moisturizer routine",
    "lamellar ichthyosis daily care",
    "ichthyosis erythroderma treatment home",
    "ichthyosis baby care family",
    "harlequin ichthyosis skincare",
    # 日本語
    "魚鱗癬 スキンケア",
    "魚鱗癬 保湿",
    "魚鱗癬 日常ケア",
]

# 動画の説明文の最大取得文字数
MAX_DESCRIPTION_LENGTH = 800


def _video_hash(video_id: str) -> str:
    return hashlib.sha256(video_id.encode()).hexdigest()[:16]


def _published_after(days_back: int) -> str:
    """YouTube API の publishedAfter パラメータ用 ISO 8601 文字列"""
    dt = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _search_videos(
    api_key: str,
    query: str,
    days_back: int,
    max_results: int = 10,
) -> list[dict]:
    """YouTube検索APIを叩いて動画リストを返す"""
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "date",
        "publishedAfter": _published_after(days_back),
        "maxResults": max_results,
        "relevanceLanguage": "en",
        "key": api_key,
    }

    try:
        resp = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=15)
        if resp.status_code == 403:
            logger.warning(f"YouTube API: 403 Forbidden（APIキーまたは割り当て超過）")
            return []
        if resp.status_code == 400:
            logger.warning(f"YouTube API: 400 Bad Request - {resp.text[:200]}")
            return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", [])
    except Exception as e:
        logger.warning(f"YouTube search failed (q={query}): {e}")
        return []


def _item_to_raw_article(item: dict) -> RawArticle | None:
    """YouTube動画アイテムをRawArticleに変換"""
    snippet = item.get("snippet", {})
    video_id = item.get("id", {}).get("videoId", "")

    if not video_id:
        return None

    title = snippet.get("title", "").strip()
    if not title:
        return None

    # 概要（description）
    description = snippet.get("description", "").strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        description = description[:MAX_DESCRIPTION_LENGTH] + "..."

    channel = snippet.get("channelTitle", "")
    published_at = snippet.get("publishedAt", "")
    pub_date = published_at[:10] if published_at else ""

    url = YOUTUBE_VIDEO_URL.format(video_id=video_id)

    # チャンネル名と説明を合わせて abstract に
    abstract_parts = []
    if channel:
        abstract_parts.append(f"[Channel: {channel}]")
    if description:
        abstract_parts.append(description)
    abstract = " ".join(abstract_parts) if abstract_parts else "[YouTube video]"

    # 言語判定（日本語タイトルなら japan）
    language = "ja" if any(ord(c) > 0x3000 for c in title) else "en"

    return RawArticle(
        source=f"youtube:{channel or 'unknown'}",
        source_id=_video_hash(video_id),
        title=title,
        abstract=abstract,
        url=url,
        published_date=pub_date,
        language=language,
    )


def get_youtube_videos(days_back: int = 30) -> list[RawArticle]:
    """
    YouTube から魚鱗癬関連の患者・家族の動画を収集。

    YOUTUBE_API_KEY が設定されていない場合はスキップ。

    Args:
        days_back: 何日前までの動画を対象にするか（デフォルト30日）
    """
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        logger.info("YouTube: YOUTUBE_API_KEY 未設定 → スキップ")
        return []

    articles: list[RawArticle] = []
    seen_ids: set[str] = set()

    for query in SEARCH_QUERIES:
        items = _search_videos(api_key, query, days_back)
        if not items:
            # API エラーまたは割り当て超過の場合は中断
            if not articles:
                logger.warning(f"YouTube: '{query}' で0件（APIキーを確認してください）")
            continue

        for item in items:
            article = _item_to_raw_article(item)
            if article and article.source_id not in seen_ids:
                seen_ids.add(article.source_id)
                articles.append(article)

        logger.debug(f"YouTube '{query}': {len(items)} videos")

    logger.info(f"YouTube: {len(articles)} videos found")
    return articles
