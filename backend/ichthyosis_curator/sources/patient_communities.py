"""患者コミュニティ・患者団体サイトからの情報収集

対象:
- FIRST (Foundation for Ichthyosis & Related Skin Types) - ichthyosis.org
- ISG (Ichthyosis Support Group UK) - ichthyosis.org.uk
- Inspire.com - 希少疾患患者コミュニティ
- note.com の魚鱗癬患者・家族による日本語体験談ブログ

患者・家族が実際に行っているスキンケアや生活の工夫、体験談を収集する。
"""

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import feedparser
import requests

from ichthyosis_curator.schemas import RawArticle

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "IchthyoCure/1.0 Medical Curation Bot (contact: ichthyocure@example.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
}

REQUEST_TIMEOUT = 20


# --------------------------------------------------------------------------- #
# ユーティリティ
# --------------------------------------------------------------------------- #

def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _is_recent(pub_date: str, days_back: int) -> bool:
    """YYYY-MM-DD 形式の日付が days_back 日以内かチェック"""
    if not pub_date:
        return True  # 日付不明は含める
    try:
        dt = datetime.strptime(pub_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
        return dt >= cutoff
    except ValueError:
        return True


def _parse_feedparser_date(entry: Any) -> str:
    """feedparserのエントリから日付文字列を取得"""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d")
        except Exception:
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:3]).strftime("%Y-%m-%d")
        except Exception:
            pass
    return ""


# --------------------------------------------------------------------------- #
# FIRST (Foundation for Ichthyosis & Related Skin Types)
# https://www.ichthyosis.org
# --------------------------------------------------------------------------- #

# 既知の制約:
# www.ichthyosis.org へのHTTPS接続はTLSハンドシェイクの段階で失敗する
# （SSL alert handshake failure / sslv3 alert handshake failure）。
# curl、openssl s_client、Python requests のいずれで直接検証しても同じ失敗が
# 再現し、User-Agentや暗号スイート・TLSバージョンの指定を変えても解消しない
# ことを確認済み（2026-07時点）。サーバー側のWAF等によるボット遮断の可能性が高く、
# クライアント側の設定変更では対処できないため、現状維持とする。
# なお ISG UK (ichthyosis.org.uk) は接続自体は成功するが、/feed/ が301リダイレクト
# の後404を返す状態（RSS自体が現状存在しない）。こちらはTLSレベルの問題ではない。
FIRST_RSS_FEEDS = [
    "https://www.ichthyosis.org/feed/",          # WordPress標準RSS
    "https://www.ichthyosis.org/news/feed/",      # ニュースカテゴリ
    "https://www.ichthyosis.org/blog/feed/",      # ブログ
]

FIRST_NEWS_PAGE = "https://www.ichthyosis.org/news/"


def _fetch_first_rss(days_back: int) -> list[RawArticle]:
    """FIRST公式サイトのRSSフィードから記事取得"""
    articles: list[RawArticle] = []
    seen: set[str] = set()

    for feed_url in FIRST_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo and not feed.entries:
                continue

            for entry in feed.entries:
                url = getattr(entry, "link", "")
                if not url or url in seen:
                    continue

                title = getattr(entry, "title", "").strip()
                if not title:
                    continue

                pub_date = _parse_feedparser_date(entry)
                if not _is_recent(pub_date, days_back):
                    continue

                # 概要取得（summary > content > なし）
                summary = ""
                if hasattr(entry, "summary"):
                    summary = entry.summary[:1000]
                elif hasattr(entry, "content") and entry.content:
                    summary = entry.content[0].get("value", "")[:1000]

                # HTMLタグを簡易除去
                import re
                summary = re.sub(r"<[^>]+>", " ", summary).strip()
                summary = re.sub(r"\s+", " ", summary)[:800]

                seen.add(url)
                articles.append(RawArticle(
                    source="patient_org:FIRST",
                    source_id=_url_hash(url),
                    title=f"[FIRST] {title}",
                    abstract=summary or "[Patient advocacy content from ichthyosis.org]",
                    url=url,
                    published_date=pub_date,
                    language="en",
                ))

            if articles:
                logger.info(f"FIRST RSS ({feed_url}): {len(articles)} entries")
                break  # 1つのフィードで取得できたら終了

        except Exception as e:
            logger.debug(f"FIRST RSS fetch failed ({feed_url}): {e}")
            continue

    return articles


def get_first_articles(days_back: int = 30) -> list[RawArticle]:
    """FIRST (ichthyosis.org) から患者向け情報を取得"""
    articles = _fetch_first_rss(days_back)
    if articles:
        return articles

    # RSSが取れない場合のフォールバック: ニュースページをスクレイプ
    try:
        articles = _scrape_first_news_page(days_back)
    except Exception as e:
        logger.warning(f"FIRST news page scrape failed: {e}")

    logger.info(f"FIRST: {len(articles)} articles found")
    return articles


def _scrape_first_news_page(days_back: int) -> list[RawArticle]:
    """FIRSTニュースページのHTMLをスクレイプ"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("beautifulsoup4 未インストール。pip install beautifulsoup4")
        return []

    try:
        resp = requests.get(FIRST_NEWS_PAGE, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"FIRST news page fetch failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles: list[RawArticle] = []
    seen: set[str] = set()

    # WordPressの典型的な記事構造を探索
    for article_el in soup.find_all(["article", "div"], class_=lambda c: c and ("post" in c or "entry" in c or "news" in c)):
        # タイトルとリンク
        title_el = article_el.find(["h1", "h2", "h3", "h4"])
        if not title_el:
            continue
        link_el = title_el.find("a") or article_el.find("a", href=True)
        if not link_el:
            continue

        url = link_el.get("href", "")
        if not url or url in seen:
            continue

        title = title_el.get_text(strip=True)
        if not title:
            continue

        # 日付
        date_el = article_el.find(["time", "span"], class_=lambda c: c and "date" in str(c))
        pub_date = ""
        if date_el:
            dt_attr = date_el.get("datetime", "")
            if dt_attr:
                pub_date = dt_attr[:10]

        if not _is_recent(pub_date, days_back):
            continue

        # 概要
        excerpt_el = article_el.find(["div", "p"], class_=lambda c: c and ("excerpt" in str(c) or "summary" in str(c)))
        summary = excerpt_el.get_text(strip=True)[:500] if excerpt_el else ""

        seen.add(url)
        articles.append(RawArticle(
            source="patient_org:FIRST",
            source_id=_url_hash(url),
            title=f"[FIRST] {title}",
            abstract=summary or "[Patient advocacy content from ichthyosis.org]",
            url=url,
            published_date=pub_date,
            language="en",
        ))

    return articles


# --------------------------------------------------------------------------- #
# ISG (Ichthyosis Support Group UK)
# https://www.ichthyosis.org.uk
# --------------------------------------------------------------------------- #

ISG_RSS_FEEDS = [
    "https://www.ichthyosis.org.uk/feed/",
    "https://www.ichthyosis.org.uk/news/feed/",
    "https://ichthyosis.org.uk/feed/",
]


def get_isg_articles(days_back: int = 30) -> list[RawArticle]:
    """ISG (ichthyosis.org.uk) から患者コミュニティ情報を取得"""
    articles: list[RawArticle] = []
    seen: set[str] = set()

    for feed_url in ISG_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo and not feed.entries:
                continue

            for entry in feed.entries:
                url = getattr(entry, "link", "")
                if not url or url in seen:
                    continue

                title = getattr(entry, "title", "").strip()
                if not title:
                    continue

                pub_date = _parse_feedparser_date(entry)
                if not _is_recent(pub_date, days_back):
                    continue

                summary = ""
                if hasattr(entry, "summary"):
                    import re
                    summary = re.sub(r"<[^>]+>", " ", entry.summary).strip()
                    summary = re.sub(r"\s+", " ", summary)[:600]

                seen.add(url)
                articles.append(RawArticle(
                    source="patient_org:ISG_UK",
                    source_id=_url_hash(url),
                    title=f"[ISG UK] {title}",
                    abstract=summary or "[Patient support content from ichthyosis.org.uk]",
                    url=url,
                    published_date=pub_date,
                    language="en",
                ))

            if articles:
                logger.info(f"ISG UK RSS ({feed_url}): {len(articles)} entries")
                break

        except Exception as e:
            logger.debug(f"ISG RSS fetch failed ({feed_url}): {e}")
            continue

    logger.info(f"ISG UK: {len(articles)} articles found")
    return articles


# --------------------------------------------------------------------------- #
# Inspire.com - 希少疾患患者コミュニティ
# ichthyosisサポートグループの投稿を取得
# --------------------------------------------------------------------------- #

INSPIRE_ICHTHYOSIS_URL = "https://www.inspire.com/groups/ichthyosis-support-network/discussion/"


def get_inspire_posts(days_back: int = 14) -> list[RawArticle]:
    """Inspire.comから魚鱗癬コミュニティの投稿を取得"""
    # Inspire.comはログイン不要でRSSを提供していないため、
    # 公開討論ページをスクレイプ。取得できない場合は0件で継続。
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.debug("beautifulsoup4未インストール。Inspire.comスキップ")
        return []

    try:
        resp = requests.get(INSPIRE_ICHTHYOSIS_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.debug(f"Inspire.com: HTTP {resp.status_code}")
            return []
    except Exception as e:
        logger.debug(f"Inspire.com fetch failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles: list[RawArticle] = []

    # 投稿リストを探索
    for post_el in soup.find_all(["div", "article"], class_=lambda c: c and "discussion" in str(c).lower()):
        title_el = post_el.find(["h2", "h3", "a"])
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        link_el = post_el.find("a", href=True)
        if not link_el:
            continue

        href = link_el.get("href", "")
        url = f"https://www.inspire.com{href}" if href.startswith("/") else href
        if not url:
            continue

        excerpt_el = post_el.find(["p", "div"], class_=lambda c: c and "excerpt" in str(c).lower())
        summary = excerpt_el.get_text(strip=True)[:500] if excerpt_el else ""

        articles.append(RawArticle(
            source="patient_community:Inspire",
            source_id=_url_hash(url),
            title=f"[Inspire] {title}",
            abstract=summary or "[Patient community post from Inspire.com]",
            url=url,
            published_date="",
            language="en",
        ))

    logger.info(f"Inspire.com: {len(articles)} posts found")
    return articles


# --------------------------------------------------------------------------- #
# note.com - 魚鱗癬患者・家族による日本語体験談ブログ
#
# note.comはユーザー単位で `https://note.com/{urlname}/rss` 形式のRSSフィードを
# 提供している。urlname: safe_magpie2015（「浄化太郎」氏）は魚鱗癬の子を持つ
# 父親で「魚鱗癬と歩んだ家族の物語」という体験談シリーズを連載しており、
# curlでの実地検証で200 OK・実データ取得を確認済み（2026-07時点）。
# 全記事が魚鱗癬に直接関係するわけではない個人ブログのため、関連性の絞り込みは
# LLMキュレーション側の関連性スコア閾値（0.3）に委ねる。
# --------------------------------------------------------------------------- #

NOTE_RSS_FEEDS = [
    # 浄化太郎氏「魚鱗癬と歩んだ家族の物語」シリーズ
    {"urlname": "safe_magpie2015", "label": "浄化太郎"},
]


def get_note_ichthyosis_articles(days_back: int = 60) -> list[RawArticle]:
    """note.comの魚鱗癬患者・家族による体験談ブログから記事を取得

    Args:
        days_back: 何日前までの記事を対象にするか（noteは更新頻度が低いブログも
            あるため、他ソースよりデフォルトを長め（60日）に設定）
    """
    import re

    articles: list[RawArticle] = []
    seen: set[str] = set()

    for feed_info in NOTE_RSS_FEEDS:
        urlname = feed_info["urlname"]
        feed_url = f"https://note.com/{urlname}/rss"

        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo and not feed.entries:
                logger.debug(f"note.com RSS parse failed ({feed_url})")
                continue

            for entry in feed.entries:
                url = getattr(entry, "link", "")
                if not url or url in seen:
                    continue

                title = getattr(entry, "title", "").strip()
                if not title:
                    continue

                pub_date = _parse_feedparser_date(entry)
                if not _is_recent(pub_date, days_back):
                    continue

                summary = ""
                if hasattr(entry, "summary"):
                    summary = re.sub(r"<[^>]+>", " ", entry.summary).strip()
                    summary = re.sub(r"\s+", " ", summary)[:800]
                elif hasattr(entry, "description"):
                    summary = re.sub(r"<[^>]+>", " ", entry.description).strip()
                    summary = re.sub(r"\s+", " ", summary)[:800]

                seen.add(url)
                articles.append(RawArticle(
                    source=f"patient_blog:note_{urlname}",
                    source_id=_url_hash(url),
                    title=f"[note] {title}",
                    abstract=summary or "[Patient/family blog post from note.com]",
                    url=url,
                    published_date=pub_date,
                    language="ja",
                ))

            logger.info(f"note.com RSS ({feed_url}): {len(articles)} entries")

        except Exception as e:
            logger.debug(f"note.com RSS fetch failed ({feed_url}): {e}")
            continue

    logger.info(f"note.com: {len(articles)} articles found")
    return articles


# --------------------------------------------------------------------------- #
# 統合エントリーポイント
# --------------------------------------------------------------------------- #

def get_patient_community_posts(days_back: int = 14) -> list[RawArticle]:
    """
    全患者コミュニティソースから情報を収集して返す。

    Sources:
        - FIRST (ichthyosis.org) - 米国患者団体
        - ISG UK (ichthyosis.org.uk) - 英国患者サポートグループ
        - Inspire.com - 希少疾患患者コミュニティ
        - note.com - 魚鱗癬患者・家族による日本語体験談ブログ

    Args:
        days_back: 何日前までのコンテンツを対象にするか
    """
    all_articles: list[RawArticle] = []
    seen_ids: set[str] = set()

    sources = [
        ("FIRST", lambda: get_first_articles(days_back=max(days_back, 30))),
        ("ISG UK", lambda: get_isg_articles(days_back=max(days_back, 30))),
        ("Inspire", lambda: get_inspire_posts(days_back=days_back)),
        ("note.com", lambda: get_note_ichthyosis_articles(days_back=max(days_back, 60))),
    ]

    for name, fetch_fn in sources:
        try:
            posts = fetch_fn()
            new_posts = [p for p in posts if p.source_id not in seen_ids]
            seen_ids.update(p.source_id for p in new_posts)
            all_articles.extend(new_posts)
            time.sleep(2.0)  # サーバー負荷対策
        except Exception as e:
            logger.warning(f"患者コミュニティ取得失敗 ({name}): {e}")

    logger.info(f"患者コミュニティ合計: {len(all_articles)} posts")
    return all_articles
