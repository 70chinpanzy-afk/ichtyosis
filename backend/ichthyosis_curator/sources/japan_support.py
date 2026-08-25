"""日本の制度・支援情報の収集

既存のソース（PubMed / ClinicalTrials.gov / 海外ニュース / Reddit / YouTube /
海外の患者団体）は「研究と海外の話」に偏っており、日本の患者・家族が
実際に手続きできる情報がまったく入っていなかった。

医療費助成の制度改正、申請の受付期間、研修会の申込期限のように
「締切があって、動けば結果が変わる」情報はここにしかない。

対象:
- 難病情報センター (nanbyou.or.jp) — 指定難病の制度・助成・審議会
- 小児慢性特定疾病情報センター (shouman.jp) — 小慢の制度・手続き・研修会

どちらもRSSを持たないためHTMLをスクレイプする。
（nanbyou.or.jp/feed/ は WordPress の無効なフィードテンプレートで404を返す）
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta

import requests

from ichthyosis_curator.schemas import RawArticle

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "IchthyoCure/1.0 Medical Curation Bot (contact: ichthyocure@example.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.8",
}

REQUEST_TIMEOUT = 20

NANBYOU_NEWS_URL = "https://www.nanbyou.or.jp/entry/category/news"
NANBYOU_BASE = "https://www.nanbyou.or.jp"
SHOUMAN_NEWS_URL = "https://www.shouman.jp/news/"
SHOUMAN_BASE = "https://www.shouman.jp"

# 制度系サイトの更新は年に数回なので、既定の取得期間は長めに取る。
# 重複排除は配信履歴側で効くため、同じ告知が何度も配信されることはない。
DEFAULT_DAYS_BACK = 90

# 元号の開始年（元年 = 開始年）。和暦N年 = 開始年 + N - 1
_ERA_START = {"R": 2019, "令和": 2019, "H": 1989, "平成": 1989}

_WAREKI_RE = re.compile(r"(令和|平成|R|H)\s*(\d{1,2}|元)\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_ISO_RE = re.compile(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})")


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def parse_japanese_date(text: str) -> str:
    """和暦・西暦まじりの日付表記を YYYY-MM-DD に正規化する。

    難病情報センターは「R8年7月24日」、小慢は「2026-07-28」と表記が異なる。
    解釈できない場合は空文字を返す。
    """
    if not text:
        return ""

    m = _WAREKI_RE.search(text)
    if m:
        era, year_str, month, day = m.groups()
        start = _ERA_START.get(era)
        if start:
            year_num = 1 if year_str == "元" else int(year_str)
            year = start + year_num - 1
            try:
                return datetime(year, int(month), int(day)).strftime("%Y-%m-%d")
            except ValueError:
                return ""

    m = _ISO_RE.search(text)
    if m:
        year, month, day = m.groups()
        try:
            return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError:
            return ""

    return ""


def _is_recent(date_str: str, days_back: int) -> bool:
    """日付不明のものは落とさず通す（制度の告知は日付表記が揺れやすい）"""
    if not date_str:
        return True
    try:
        published = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return True
    return published >= datetime.now() - timedelta(days=days_back)


def _absolute_url(href: str, base: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"{base}{href}"
    return f"{base}/{href}"


def _get_soup(url: str):
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("beautifulsoup4 未インストール。pip install beautifulsoup4")
        return None

    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"{url} の取得に失敗: {e}")
        return None

    resp.encoding = resp.apparent_encoding or resp.encoding
    return BeautifulSoup(resp.text, "html.parser")


def fetch_nanbyou_news(days_back: int = DEFAULT_DAYS_BACK) -> list[RawArticle]:
    """難病情報センターのお知らせ一覧

    構造:
      <div class="news_article">
        <div class="news_date"><span class="news_date">R8年7月24日</span></div>
        <div class="news_contents"><p>本文 <a href="...">リンク</a></p></div>
      </div>
    """
    soup = _get_soup(NANBYOU_NEWS_URL)
    if soup is None:
        return []

    articles: list[RawArticle] = []
    seen: set[str] = set()

    for block in soup.find_all("div", class_="news_article"):
        date_el = block.find(class_="news_date")
        published = parse_japanese_date(date_el.get_text(strip=True)) if date_el else ""
        if not _is_recent(published, days_back):
            continue

        contents = block.find("div", class_="news_contents")
        if contents is None:
            continue

        text = contents.get_text(" ", strip=True)
        if not text:
            continue

        link_el = contents.find("a", href=True)
        url = _absolute_url(link_el["href"], NANBYOU_BASE) if link_el else NANBYOU_NEWS_URL

        # 詳細リンクが無い告知は本文自体が識別子になる
        key = url if link_el else f"{NANBYOU_NEWS_URL}#{_url_hash(text)}"
        if key in seen:
            continue
        seen.add(key)

        title = text[:80]
        articles.append(RawArticle(
            source="japan_support:難病情報センター",
            source_id=_url_hash(key),
            title=f"[難病情報センター] {title}",
            abstract=text[:1500],
            url=url,
            published_date=published or None,
            language="ja",
        ))

    logger.info(f"難病情報センター: {len(articles)} 件")
    return articles


def fetch_shouman_news(days_back: int = DEFAULT_DAYS_BACK) -> list[RawArticle]:
    """小児慢性特定疾病情報センターのお知らせ

    構造:
      <li class="topics" data-category="topics">
        <p class="date"><strong>2026-07-28</strong></p>
        <p><a href="/news/topics/170">タイトル</a></p>
      </li>
    """
    soup = _get_soup(SHOUMAN_NEWS_URL)
    if soup is None:
        return []

    articles: list[RawArticle] = []
    seen: set[str] = set()

    for item in soup.find_all("li", class_="topics"):
        link_el = item.find("a", href=True)
        if link_el is None:
            continue

        url = _absolute_url(link_el["href"], SHOUMAN_BASE)
        if not url or url in seen:
            continue

        title = link_el.get_text(" ", strip=True)
        if not title:
            continue

        date_el = item.find("p", class_="date")
        published = parse_japanese_date(date_el.get_text(strip=True)) if date_el else ""
        if not _is_recent(published, days_back):
            continue

        seen.add(url)
        articles.append(RawArticle(
            source="japan_support:小児慢性特定疾病情報センター",
            source_id=_url_hash(url),
            title=f"[小児慢性特定疾病] {title}",
            abstract=item.get_text(" ", strip=True)[:1500],
            url=url,
            published_date=published or None,
            language="ja",
        ))

    logger.info(f"小児慢性特定疾病情報センター: {len(articles)} 件")
    return articles


def get_japan_support_articles(days_back: int = DEFAULT_DAYS_BACK) -> list[RawArticle]:
    """日本の制度・支援情報をまとめて取得する。

    片方が落ちてももう片方は返す（スクレイプは構造変更で壊れやすいため）。
    """
    articles: list[RawArticle] = []

    for name, fetcher in (
        ("難病情報センター", fetch_nanbyou_news),
        ("小児慢性特定疾病情報センター", fetch_shouman_news),
    ):
        try:
            articles.extend(fetcher(days_back))
        except Exception as e:
            logger.warning(f"{name} の取得に失敗: {e}")

    logger.info(f"日本の制度・支援: 合計 {len(articles)} 件")
    return articles
