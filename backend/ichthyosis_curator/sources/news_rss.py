"""Google News RSSによるニュース記事検索"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser

from ichthyosis_curator.schemas import RawArticle

logger = logging.getLogger(__name__)

GOOGLE_NEWS_FEEDS = [
    # 魚鱗癬 直接（英語）
    "https://news.google.com/rss/search?q=ichthyosis+treatment&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=ichthyosis+erythroderma&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=ichthyosis+gene+therapy&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=orphan+drug+ichthyosis&hl=en&gl=US&ceid=US:en",
    # 類似疾患（英語）
    "https://news.google.com/rss/search?q=atopic+dermatitis+skin+barrier+treatment&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=JAK+inhibitor+skin+disease&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=rare+skin+disease+drug&hl=en&gl=US&ceid=US:en",
    # 日本語
    "https://news.google.com/rss/search?q=%E9%AD%9A%E9%B1%97%E7%99%AC+%E6%B2%BB%E7%99%82&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=%E9%AD%9A%E9%B1%97%E7%99%AC+%E6%96%B0%E8%96%AC&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=%E7%B4%85%E7%9A%AE%E7%97%87&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=%E3%82%A2%E3%83%88%E3%83%94%E3%83%BC+%E7%9A%AE%E8%86%9A%E3%83%90%E3%83%AA%E3%82%A2+%E6%96%B0%E8%96%AC&hl=ja&gl=JP&ceid=JP:ja",
]

# 上のクエリは treatment / 新薬 / gene therapy と研究寄りで、生活場面の記事が
# 集まらない。困りごとテーマ由来のクエリを日替わりで足す。
# 希少疾患なのでニュース自体が少なく、ヒットは多くない想定だが、
# 制度・支援や季節の注意喚起はここから入ってくる。
THEME_FEEDS_PER_RUN = 5


def _theme_feed_urls() -> list[str]:
    """困りごとテーマ由来のGoogle News RSS URL（日替わり）"""
    from urllib.parse import quote

    from ichthyosis_curator.curation.themes import rotating_themes

    urls: list[str] = []
    for theme in rotating_themes(THEME_FEEDS_PER_RUN):
        for query in theme.queries_ja:
            urls.append(
                f"https://news.google.com/rss/search?q={quote(query)}"
                "&hl=ja&gl=JP&ceid=JP:ja"
            )
        for query in theme.queries_en:
            urls.append(
                f"https://news.google.com/rss/search?q={quote(query)}"
                "&hl=en&gl=US&ceid=US:en"
            )
    return urls


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _is_recent(entry, days_back: int) -> bool:
    """RSSエントリが指定日数以内かどうか"""
    published = entry.get("published_parsed")
    if not published:
        return True  # 日付不明なら含める

    try:
        pub_dt = datetime.fromtimestamp(mktime(published), tz=timezone.utc)
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
        return pub_dt >= cutoff
    except Exception:
        return True


def fetch_google_news(days_back: int = 7) -> list[RawArticle]:
    """Google News RSSからニュース記事を取得"""
    articles: list[RawArticle] = []
    seen_urls: set[str] = set()

    for feed_url in GOOGLE_NEWS_FEEDS + _theme_feed_urls():
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                url = entry.get("link", "")
                if not url or url in seen_urls:
                    continue

                if not _is_recent(entry, days_back):
                    continue

                seen_urls.add(url)

                title = entry.get("title", "")
                if not title:
                    continue

                # 公開日
                pub_date = ""
                if entry.get("published_parsed"):
                    try:
                        pub_dt = datetime.fromtimestamp(
                            mktime(entry.published_parsed), tz=timezone.utc
                        )
                        pub_date = pub_dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass

                # 言語推定
                language = "ja" if "hl=ja" in feed_url else "en"

                # ソース名を抽出（Google Newsのタイトルは「タイトル - ソース名」形式）
                source_name = entry.get("source", {}).get("title", "news")

                articles.append(
                    RawArticle(
                        source=f"google_news:{source_name}",
                        source_id=_url_hash(url),
                        title=title,
                        abstract=entry.get("summary", ""),
                        url=url,
                        published_date=pub_date,
                        language=language,
                    )
                )

        except Exception as e:
            logger.warning(f"RSS feed fetch failed for {feed_url[:60]}...: {e}")
            continue

    logger.info(f"Google News RSS: {len(articles)} articles found")
    return articles


def get_news_articles(days_back: int = 7) -> list[RawArticle]:
    """ニュース記事を取得"""
    return fetch_google_news(days_back)
