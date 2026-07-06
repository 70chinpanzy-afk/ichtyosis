"""RedditからのSNS投稿取得（認証不要のJSON API使用）

既知の制約:
GitHub Actionsのrunner（AWS/Azure等のホスティングIPレンジ）からのアクセスは
Reddit側で403 Forbiddenとして継続的にブロックされていることを確認済み。
User-Agent文字列の変更（ブラウザ相当のUAへの偽装含む）では解消しない
（RedditはIPレンジ単位でクラウドプロバイダのbot判定を行っているとみられる）。
ローカル環境（自宅回線等）からは200で取得できるため、コード自体の不具合ではない。
恒久対応にはプロキシ経由アクセスやReddit公式APIの認証利用が必要だが、
個人利用ツールのスコープ外として現状維持とする。
"""

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone

import requests

from ichthyosis_curator.schemas import RawArticle

logger = logging.getLogger(__name__)

# 取得対象のサブレディット + 検索クエリ
REDDIT_SOURCES = [
    # 魚鱗癬専門コミュニティ
    {"subreddit": "ichthyosis", "sort": "new", "type": "subreddit"},
    # 皮膚疾患・アトピー系コミュニティで魚鱗癬を検索
    {"subreddit": "eczema", "query": "ichthyosis", "type": "search"},
    {"subreddit": "SkincareAddiction", "query": "ichthyosis OR keratosis OR skin barrier repair", "type": "search"},
    # 希少疾患コミュニティ
    {"subreddit": "RareDisease", "query": "ichthyosis OR skin condition", "type": "search"},
    # 全体検索（体験談・ケア情報）
    {"subreddit": None, "query": "ichthyosis treatment moisturizer", "type": "search_all"},
    {"subreddit": None, "query": "ichthyosis erythroderma", "type": "search_all"},
    {"subreddit": None, "query": "lamellar ichthyosis care", "type": "search_all"},
    # アトピー関連で応用可能な知見
    {"subreddit": "eczema", "query": "skin barrier ceramide moisturizer", "type": "search"},
]

HEADERS = {
    "User-Agent": "IchthyoCure/1.0 (medical curation bot; contact: curator@example.com)",
}


def _post_hash(permalink: str) -> str:
    return hashlib.sha256(permalink.encode()).hexdigest()[:16]


def _fetch_subreddit_new(subreddit: str, days_back: int, limit: int = 25) -> list[dict]:
    """サブレディットの新着投稿を取得"""
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("children", [])
    except Exception as e:
        logger.warning(f"Reddit r/{subreddit} fetch failed: {e}")
        return []


def _fetch_search(subreddit: str | None, query: str, days_back: int, limit: int = 25) -> list[dict]:
    """Reddit検索API（サブレディット指定 or 全体検索）"""
    if subreddit:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {"q": query, "restrict_sr": "on", "sort": "new", "t": "month", "limit": limit}
    else:
        url = "https://www.reddit.com/search.json"
        params = {"q": query, "sort": "new", "t": "month", "limit": limit}

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("children", [])
    except Exception as e:
        logger.warning(f"Reddit search failed (r/{subreddit} q={query}): {e}")
        return []


def _is_recent(created_utc: float, days_back: int) -> bool:
    post_time = datetime.fromtimestamp(created_utc, tz=timezone.utc)
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
    return post_time >= cutoff


def _post_to_raw_article(post_data: dict, days_back: int) -> RawArticle | None:
    """Reddit投稿をRawArticleに変換"""
    d = post_data.get("data", {})

    # 基本フィルタ
    if d.get("removed_by_category") or d.get("is_robot_indexable") is False:
        return None

    created_utc = d.get("created_utc", 0)
    if not _is_recent(created_utc, days_back):
        return None

    title = d.get("title", "").strip()
    if not title:
        return None

    # 本文（selftext）を要約用に取得
    selftext = d.get("selftext", "").strip()
    # あまりに長いテキストは先頭1500文字に制限
    if len(selftext) > 1500:
        selftext = selftext[:1500] + "..."

    permalink = d.get("permalink", "")
    url = f"https://www.reddit.com{permalink}" if permalink else ""
    subreddit = d.get("subreddit", "unknown")

    pub_date = ""
    if created_utc:
        pub_date = datetime.fromtimestamp(created_utc, tz=timezone.utc).strftime("%Y-%m-%d")

    # スコア（upvotes）情報を付加
    score = d.get("score", 0)
    num_comments = d.get("num_comments", 0)
    engagement = f"[upvotes: {score}, comments: {num_comments}]"

    return RawArticle(
        source=f"reddit:r/{subreddit}",
        source_id=_post_hash(permalink or title),
        title=title,
        abstract=f"{engagement} {selftext}" if selftext else engagement,
        url=url,
        published_date=pub_date,
        language="en",
    )


def get_reddit_posts(days_back: int = 14) -> list[RawArticle]:
    """
    Redditから魚鱗癬関連の投稿を取得。

    Args:
        days_back: 何日前までの投稿を対象にするか（デフォルト14日）
    """
    articles: list[RawArticle] = []
    seen_ids: set[str] = set()

    for source in REDDIT_SOURCES:
        src_type = source["type"]

        if src_type == "subreddit":
            posts = _fetch_subreddit_new(source["subreddit"], days_back)
        elif src_type == "search":
            posts = _fetch_search(source["subreddit"], source["query"], days_back)
        elif src_type == "search_all":
            posts = _fetch_search(None, source["query"], days_back)
        else:
            continue

        for post in posts:
            article = _post_to_raw_article(post, days_back)
            if article and article.source_id not in seen_ids:
                seen_ids.add(article.source_id)
                articles.append(article)

        # Reddit API レート制限対策（1秒間隔）
        time.sleep(1.0)

    logger.info(f"Reddit: {len(articles)} posts found")
    return articles
