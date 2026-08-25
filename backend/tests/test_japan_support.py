"""日本の制度・支援ソースのテスト

既存ソースは研究と海外の話に偏っており、日本の患者・家族が実際に
手続きできる情報が入っていなかった。ここは締切があるので取りこぼすと痛い。
"""

import pytest

pytest.importorskip("bs4")

from bs4 import BeautifulSoup  # noqa: E402

from ichthyosis_curator.sources import japan_support  # noqa: E402
from ichthyosis_curator.sources.japan_support import (  # noqa: E402
    fetch_nanbyou_news,
    fetch_shouman_news,
    get_japan_support_articles,
    parse_japanese_date,
)

# 実サイトの構造をそのまま縮めたもの
NANBYOU_HTML = """
<div class="news_article">
  <div class="news_date"><span class="news_date">R8年6月24日</span></div>
  <div class="news_contents"><p>（厚生労働省からのお知らせ）<br>
  「特定医療費の支給認定について」の一部改正について
  <a href="/wp-content/uploads/2026/06/R080624_kaisei01up.pdf">通知</a></p></div>
</div>
<div class="news_article">
  <div class="news_date"><span class="news_date">R8年7月24日</span></div>
  <div class="news_contents"><p>難病情報センターの全てのページに音声読み上げボタンを配置しました</p></div>
</div>
"""

SHOUMAN_HTML = """
<ul>
  <li class="topics" data-category="topics">
    <p class="date"><strong>2026-06-09</strong></p>
    <p><a href="/news/topics/169">第19回自立支援員研修会【基礎編】開催案内</a></p>
  </li>
  <li class="topics" data-category="topics">
    <p class="date"><strong>2019-01-01</strong></p>
    <p><a href="/news/topics/1">古いお知らせ</a></p>
  </li>
</ul>
"""


@pytest.mark.parametrize("text,expected", [
    ("R8年7月24日", "2026-07-24"),
    ("令和8年7月6日", "2026-07-06"),
    ("令和元年5月1日", "2019-05-01"),
    ("H31年4月1日", "2019-04-01"),
    ("2026-07-28", "2026-07-28"),
    ("2026年7月28日", "2026-07-28"),
])
def test_和暦と西暦を正規化する(text: str, expected: str):
    assert parse_japanese_date(text) == expected


@pytest.mark.parametrize("text", ["不明", "", "R8年13月40日"])
def test_解釈できない日付は空文字(text: str):
    assert parse_japanese_date(text) == ""


def _stub_soup(monkeypatch, html: str):
    monkeypatch.setattr(
        japan_support, "_get_soup", lambda url: BeautifulSoup(html, "html.parser")
    )


def test_難病情報センターのお知らせを取れる(monkeypatch):
    _stub_soup(monkeypatch, NANBYOU_HTML)

    articles = fetch_nanbyou_news(days_back=3650)

    assert len(articles) == 2
    first = articles[0]
    assert first.published_date == "2026-06-24"
    assert "特定医療費の支給認定" in first.title
    assert first.url.startswith("https://www.nanbyou.or.jp/wp-content/")
    assert first.language == "ja"


def test_詳細リンクが無い告知も一覧ページを指して取り込む(monkeypatch):
    _stub_soup(monkeypatch, NANBYOU_HTML)

    articles = fetch_nanbyou_news(days_back=3650)

    linkless = articles[1]
    assert linkless.url == japan_support.NANBYOU_NEWS_URL
    assert linkless.source_id != articles[0].source_id


def test_小慢のお知らせを取れる(monkeypatch):
    _stub_soup(monkeypatch, SHOUMAN_HTML)

    articles = fetch_shouman_news(days_back=3650)

    assert len(articles) == 2
    assert articles[0].url == "https://www.shouman.jp/news/topics/169"
    assert "自立支援員研修会" in articles[0].title


def test_期間より古いお知らせは落とす(monkeypatch):
    _stub_soup(monkeypatch, SHOUMAN_HTML)

    articles = fetch_shouman_news(days_back=90)

    assert [a.published_date for a in articles] == ["2026-06-09"]


def test_取得に失敗しても空リストで返る(monkeypatch):
    monkeypatch.setattr(japan_support, "_get_soup", lambda url: None)

    assert fetch_nanbyou_news() == []
    assert fetch_shouman_news() == []


def test_片方が落ちてももう片方は返す(monkeypatch):
    def boom(days_back=90):
        raise RuntimeError("構造が変わった")

    monkeypatch.setattr(japan_support, "fetch_nanbyou_news", boom)
    monkeypatch.setattr(
        japan_support, "fetch_shouman_news",
        lambda days_back=90: [
            japan_support.RawArticle(source="s", source_id="1", title="t", url="https://e.com")
        ],
    )

    assert len(get_japan_support_articles()) == 1


# --- 臨床試験の参加条件（要約だけでは「自分に当てはまるか」が判断できない） ---

from ichthyosis_curator.sources.clinical_trials import _trial_context  # noqa: E402


def test_日本で参加できる募集中の試験がわかる():
    protocol = {
        "statusModule": {"overallStatus": "RECRUITING"},
        "contactsLocationsModule": {"locations": [
            {"country": "Japan"}, {"country": "United States"}, {"country": "Japan"},
        ]},
        "eligibilityModule": {
            "minimumAge": "12 Years", "maximumAge": "65 Years", "stdAges": ["CHILD", "ADULT"],
        },
    }

    context = _trial_context(protocol)

    assert "Recruiting now: yes" in context
    assert "Available in Japan: yes" in context
    assert "Japan, United States" in context  # 重複は除いて並べる
    assert "12 Years to 65 Years" in context


def test_終了した試験は募集中にしない():
    context = _trial_context({"statusModule": {"overallStatus": "TERMINATED"}})

    assert "Recruiting now: no" in context
    assert "Available in Japan: unknown" in context


def test_実施国が多いときは省略して件数を出す():
    protocol = {
        "statusModule": {"overallStatus": "RECRUITING"},
        "contactsLocationsModule": {
            "locations": [{"country": f"Country{i:02d}"} for i in range(12)]
        },
    }

    assert "and 4 more" in _trial_context(protocol)


def test_情報が無くても落ちない():
    context = _trial_context({})

    assert "UNKNOWN" in context
    assert "not specified" in context
