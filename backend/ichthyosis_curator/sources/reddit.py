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
import os
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

# 1回の実行で回す困りごとテーマの数（日替わりで一巡させる）
THEME_QUERIES_PER_RUN = 4


def _theme_sources() -> list[dict]:
    """困りごとテーマ由来の検索条件。

    既存クエリは treatment / moisturizer / gene therapy と研究寄りに偏っており、
    学校・夏の汗・耳といった生活場面がまったく集まっていなかった。
    r/ichthyosis には当事者の生の相談が集まっているので、テーマ名で引く。
    """
    from ichthyosis_curator.curation.themes import rotating_themes

    sources: list[dict] = []
    for theme in rotating_themes(THEME_QUERIES_PER_RUN):
        for query in theme.queries_en:
            sources.append({"subreddit": "ichthyosis", "query": query, "type": "search"})
    return sources

HEADERS = {
    "User-Agent": "IchthyoCure/1.0 (medical curation bot; contact: curator@example.com)",
}

# Reddit は未認証の *.json アクセスを事実上遮断しており、JSONではなく
# HTMLのログイン誘導ページが返る。そのためこのソースは 2026-03-19 を最後に
# 5か月間まったく取得できていなかった（runner が例外を握りつぶすため、
# 失敗が表に出ていなかった）。アプリ登録して client credentials を渡せば
# oauth.reddit.com 経由で取得できる。
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_OAUTH_BASE = "https://oauth.reddit.com"
REDDIT_PUBLIC_BASE = "https://www.reddit.com"

_token_cache: dict[str, str] = {}


def _get_access_token() -> str | None:
    """client credentials でアクセストークンを取る（未設定なら None）"""
    if "token" in _token_cache:
        return _token_cache["token"]

    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None

    try:
        resp = requests.post(
            REDDIT_TOKEN_URL,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        token = resp.json().get("access_token")
    except Exception as e:
        logger.warning(f"Reddit の認証に失敗しました: {e}")
        return None

    if not token:
        logger.warning("Reddit の認証レスポンスに access_token がありません")
        return None

    _token_cache["token"] = token
    return token


def _reddit_get(path: str, params: dict | None = None) -> list[dict]:
    """Reddit APIを叩いて children を返す。認証があれば oauth 経由。

    未認証だとHTMLが返るので、JSONとして読めなかった場合は「認証が要る」ことが
    分かるログを出す（黙って0件にしない）。
    """
    token = _get_access_token()
    if token:
        url = f"{REDDIT_OAUTH_BASE}{path}"
        headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    else:
        url = f"{REDDIT_PUBLIC_BASE}{path}.json"
        headers = HEADERS

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except ValueError:
        logger.warning(
            f"Reddit がJSONを返しませんでした ({path})。"
            "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET を設定してください"
        )
        return []
    except Exception as e:
        logger.warning(f"Reddit fetch failed ({path}): {e}")
        return []

    return data.get("data", {}).get("children", [])


def _post_hash(permalink: str) -> str:
    return hashlib.sha256(permalink.encode()).hexdigest()[:16]


def _fetch_subreddit_new(subreddit: str, days_back: int, limit: int = 25) -> list[dict]:
    """サブレディットの新着投稿を取得"""
    return _reddit_get(f"/r/{subreddit}/new", {"limit": limit})


def _fetch_search(subreddit: str | None, query: str, days_back: int, limit: int = 25) -> list[dict]:
    """Reddit検索API（サブレディット指定 or 全体検索）"""
    if subreddit:
        path = f"/r/{subreddit}/search"
        params = {"q": query, "restrict_sr": "on", "sort": "new", "t": "month", "limit": limit}
    else:
        path = "/search"
        params = {"q": query, "sort": "new", "t": "month", "limit": limit}

    return _reddit_get(path, params)


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

    for source in REDDIT_SOURCES + _theme_sources():
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
