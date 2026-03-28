"""Google News RSSによるニュース記事検索（営業向け一般時事ニュース）"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser

from ichthyosis_curator.schemas import RawArticle

logger = logging.getLogger(__name__)

# 日本ニュース（日本語）
JAPAN_NEWS_FEEDS = [
    # 経済・ビジネス
    "https://news.google.com/rss/search?q=%E7%B5%8C%E6%B8%88+%E3%83%93%E3%82%B8%E3%83%8D%E3%82%B9&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=%E6%A0%AA%E4%BE%A1+%E5%B8%82%E5%A0%B4+%E6%99%AF%E6%B0%97&hl=ja&gl=JP&ceid=JP:ja",
    # 政治・社会
    "https://news.google.com/rss/search?q=%E6%94%BF%E6%B2%BB+%E6%94%BF%E7%AD%96+%E6%B3%95%E6%94%B9%E6%AD%A3&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=%E7%A4%BE%E4%BC%9A+%E3%83%8B%E3%83%A5%E3%83%BC%E3%82%B9+%E8%A9%B1%E9%A1%8C&hl=ja&gl=JP&ceid=JP:ja",
    # テクノロジー
    "https://news.google.com/rss/search?q=AI+DX+%E3%83%86%E3%82%AF%E3%83%8E%E3%83%AD%E3%82%B8%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja",
    # スポーツ・文化
    "https://news.google.com/rss/search?q=%E3%82%B9%E3%83%9D%E3%83%BC%E3%83%84+%E3%82%A8%E3%83%B3%E3%82%BF%E3%83%A1&hl=ja&gl=JP&ceid=JP:ja",
    # トップニュース（日本）
    "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja",
]

# 海外ニュース（英語）
INTERNATIONAL_NEWS_FEEDS = [
    # Business & Economy
    "https://news.google.com/rss/search?q=business+economy+market&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=stock+market+global+economy&hl=en&gl=US&ceid=US:en",
    # Technology
    "https://news.google.com/rss/search?q=AI+technology+innovation&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=SaaS+startup+digital+transformation&hl=en&gl=US&ceid=US:en",
    # World / Politics
    "https://news.google.com/rss/search?q=world+politics+geopolitics&hl=en&gl=US&ceid=US:en",
    # Sports & Culture
    "https://news.google.com/rss/search?q=sports+entertainment+culture&hl=en&gl=US&ceid=US:en",
    # Top stories (US)
    "https://news.google.com/rss?hl=en&gl=US&ceid=US:en",
]


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


def _fetch_feeds(
    feeds: list[str],
    region: str,
    days_back: int,
) -> list[RawArticle]:
    """フィードリストから記事を取得"""
    articles: list[RawArticle] = []
    seen_urls: set[str] = set()

    for feed_url in feeds:
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
                        region=region,
                    )
                )

        except Exception as e:
            logger.warning(f"RSS feed fetch failed for {feed_url[:60]}...: {e}")
            continue

    return articles


def fetch_japan_news(days_back: int = 3) -> list[RawArticle]:
    """日本ニュースを取得"""
    articles = _fetch_feeds(JAPAN_NEWS_FEEDS, "japan", days_back)
    logger.info(f"Japan News RSS: {len(articles)} articles found")
    return articles


def fetch_international_news(days_back: int = 3) -> list[RawArticle]:
    """海外ニュースを取得"""
    articles = _fetch_feeds(INTERNATIONAL_NEWS_FEEDS, "international", days_back)
    logger.info(f"International News RSS: {len(articles)} articles found")
    return articles


def get_news_articles(days_back: int = 3) -> list[RawArticle]:
    """日本・海外のニュース記事をまとめて取得"""
    japan = fetch_japan_news(days_back)
    international = fetch_international_news(days_back)
    all_articles = japan + international
    logger.info(f"Total News RSS: {len(all_articles)} articles (Japan: {len(japan)}, International: {len(international)})")
    return all_articles
