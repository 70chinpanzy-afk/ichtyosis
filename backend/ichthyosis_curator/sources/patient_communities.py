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
# https://www.firstskinfoundation.org
#
# 旧ドメイン www.ichthyosis.org は既に消滅しており（DNS解決自体が失敗）、
# 2026-07 時点の調査ではこれを「WAFによるTLS遮断」と誤って結論づけていた。
# 実際には団体がリブランドして firstskinfoundation.org へ移転していただけで、
# 新ドメインには生きたRSS（/news/feed）がある。この取り違えのため、FIRSTは
# 全期間を通じて1件も取得できていなかった。
# --------------------------------------------------------------------------- #

FIRST_BASE = "https://www.firstskinfoundation.org"

FIRST_RSS_FEEDS = [
    f"{FIRST_BASE}/news/feed",
]

FIRST_NEWS_PAGE = f"{FIRST_BASE}/news"

# 実用ガイド。ニュースと違って更新されない静的ページだが、収集が空白だった
# 生活場面（夏の汗・学校・見た目・入浴）をそのまま埋める内容が載っている。
# 重複排除が効くので、初回に一度だけ取り込まれて以後は蓄積資産になる。
FIRST_GUIDE_PAGES = [
    ("overheating", "夏の暑さ・体温調節"),
    ("school-resources", "学校での配慮と先生への説明"),
    ("mental-health", "見た目・気持ちの支え"),
    ("bathing", "入浴と角質ケア"),
]

# ガイド本文の最大取得文字数（LLMに渡すのでトークン節約のため切る）
GUIDE_MAX_CHARS = 4000


def fetch_first_guides() -> list[RawArticle]:
    """FIRSTの実用ガイドページを取り込む

    著作権に配慮し、全文を再配布する目的では使わない。要約と原典リンクを
    出すための素材として扱う（キュレーション側で日本語の要点にまとめ、
    記事ページから原文へリンクする）。
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("beautifulsoup4 未インストール。pip install beautifulsoup4")
        return []

    articles: list[RawArticle] = []

    for slug, label in FIRST_GUIDE_PAGES:
        url = f"{FIRST_BASE}/{slug}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"FIRSTガイドの取得に失敗 ({slug}): {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "form"]):
            tag.decompose()

        main = soup.find("main") or soup.find("article") or soup.body
        if main is None:
            continue

        text = " ".join(main.get_text(" ", strip=True).split())
        if len(text) < 200:
            logger.warning(f"FIRSTガイドの本文が短すぎるためスキップ ({slug})")
            continue

        articles.append(RawArticle(
            source="patient_org:FIRST_guide",
            source_id=_url_hash(url),
            title=f"[FIRST] {label} (Living with Ichthyosis guide)",
            abstract=text[:GUIDE_MAX_CHARS],
            url=url,
            published_date=None,
            language="en",
        ))
        time.sleep(1.0)

    logger.info(f"FIRST guides: {len(articles)} pages")
    return articles


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
# ISG (英) と Inspire は取得元として撤去した
#
# ISG (ichthyosis.org.uk): サイトは生きているが RSS が存在せず（/feed, /news/feed,
#   /blog/feed などいずれも404）、ニュース欄自体が無い。発信は Facebook に
#   移っており、スクレイプ可能な更新情報が無い。
# Inspire (inspire.com): 魚鱗癬グループのURLが404。別スラッグも見つからず、
#   グループ自体が無くなったと判断した。
#
# どちらも実装は存在したが、全期間を通じて1件も取得できていなかった。
# 動かないコードを残すと「取得できているつもり」になるため削除する。
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# note.com - 魚鱗癬患者・家族による日本語体験談ブログ
#
# 以前は特定ユーザーのRSS（safe_magpie2015 氏）だけを追っていたが、それでは
# 5か月で13件しか集まらず、患者側の情報が薄いままだった。
# note.com には検索API（/api/v3/searches）があり、「魚鱗癬」で297件がヒットする。
# 「魚鱗癬 保育園」のような困りごと単位で引くと、研究論文には絶対に出てこない
# 「娘の足の裏を『キモい』と笑われた日」のような記事が拾える。ここが
# 学校・保育園まわりの空白（収集0件）を埋める主力になる。
# --------------------------------------------------------------------------- #

NOTE_SEARCH_API = "https://note.com/api/v3/searches"

# 病名そのもの。ここが本体で、テーマ別クエリは困りごとの穴を埋める補助。
NOTE_BASE_QUERIES = ("魚鱗癬", "先天性魚鱗癬様紅皮症")

# 1クエリあたりの取得件数。noteは公開順ではなく関連順で返るため多く取りすぎない
NOTE_PAGE_SIZE = 20

# テーマ別クエリを1回の実行で何件回すか（日替わりで一巡させる）
NOTE_THEME_QUERIES_PER_RUN = 6


# note の検索は語のAND一致ではないため、「魚鱗癬 夏 体温」のようなテーマ別クエリを
# 投げると「ペイ・フォワード企画」のような無関係の記事が大量に返ってくる。
# テーマ別クエリの結果は病名を含むものだけに絞る（病名そのもののクエリは絞らない）。
NOTE_DISEASE_TERMS = ("魚鱗癬", "魚鱗症", "ぎょりんせん", "ichthyosis", "紅皮症", "コロジオン")


def _note_url(urlname: str, key: str) -> str:
    return f"https://note.com/{urlname}/n/{key}"


def _mentions_disease(*texts: str) -> bool:
    joined = " ".join(t or "" for t in texts).lower()
    return any(term.lower() in joined for term in NOTE_DISEASE_TERMS)


def _fetch_note_search(
    query: str, days_back: int, require_disease: bool = False
) -> list[RawArticle]:
    """note.comの検索APIから1クエリ分を取得する

    require_disease: タイトル・概要に病名が出てくるものだけ残す
        （テーマ別クエリのノイズ対策）
    """
    params = {"context": "note", "q": query, "size": NOTE_PAGE_SIZE}
    try:
        resp = requests.get(
            NOTE_SEARCH_API, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.debug(f"note.com 検索に失敗 (q={query}): {e}")
        return []

    contents = ((payload.get("data") or {}).get("notes") or {}).get("contents") or []

    articles: list[RawArticle] = []
    for note in contents:
        user = note.get("user") or {}
        urlname = user.get("urlname")
        key = note.get("key")
        if not urlname or not key:
            continue

        title = (note.get("name") or "").strip()
        if not title:
            continue

        if require_disease and not _mentions_disease(title, note.get("description")):
            continue

        published = (note.get("publish_at") or "")[:10]
        if not _is_recent(published, days_back):
            continue

        url = _note_url(urlname, key)
        description = (note.get("description") or "").strip()

        # 反応の多さは「多くの人に刺さった内容か」の手がかりになるので残す
        stats = f"[スキ {note.get('like_count', 0)} / コメント {note.get('comment_count', 0)}]"

        articles.append(RawArticle(
            source=f"patient_blog:note_{urlname}",
            source_id=_url_hash(url),
            title=f"[note] {title}",
            abstract=f"{stats} {description}".strip() or "[Patient/family blog post from note.com]",
            url=url,
            published_date=published or None,
            language="ja",
        ))

    return articles


def get_note_ichthyosis_articles(days_back: int = 60) -> list[RawArticle]:
    """note.comの検索APIから魚鱗癬関連の体験談を取得する

    病名クエリに加えて、困りごとテーマ別のクエリを日替わりで回す。
    テーマ別に引かないと、研究寄りの記事ばかり集まって学校・夏の汗といった
    生活場面が空白のままになる。

    Args:
        days_back: 何日前までの記事を対象にするか（noteは更新頻度が低いので長め）
    """
    from ichthyosis_curator.curation.themes import rotating_themes

    # 病名そのもののクエリは絞らない。テーマ別クエリは病名を含むものだけ残す。
    queries: list[tuple[str, bool]] = [(q, False) for q in NOTE_BASE_QUERIES]
    for theme in rotating_themes(NOTE_THEME_QUERIES_PER_RUN):
        queries.extend((q, True) for q in theme.queries_ja)

    articles: list[RawArticle] = []
    seen: set[str] = set()

    for query, require_disease in queries:
        for article in _fetch_note_search(query, days_back, require_disease):
            if article.url in seen:
                continue
            seen.add(article.url)
            articles.append(article)
        time.sleep(0.5)  # 検索APIに連続で叩き込まない

    logger.info(f"note.com: {len(articles)} articles found ({len(queries)} queries)")
    return articles


# --------------------------------------------------------------------------- #
# 統合エントリーポイント
# --------------------------------------------------------------------------- #

def get_patient_community_posts(days_back: int = 14) -> list[RawArticle]:
    """
    全患者コミュニティソースから情報を収集して返す。

    Sources:
        - FIRST (firstskinfoundation.org) - 米国患者団体のニュースと実用ガイド
        - note.com - 魚鱗癬患者・家族による日本語体験談ブログ

    Args:
        days_back: 何日前までのコンテンツを対象にするか
    """
    all_articles: list[RawArticle] = []
    seen_ids: set[str] = set()

    sources = [
        ("FIRST", lambda: get_first_articles(days_back=max(days_back, 30))),
        ("FIRST guides", fetch_first_guides),
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
