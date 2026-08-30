"""困りごとテーマのテスト

収集が研究の世界に偏っていて、読者が実際に困る場面（学校0件・夏の汗1件・
制度2件）がほぼ集まっていなかった。テーマ定義が検索クエリとテーマ判定の
両方の元になるので、ここが壊れると素材が元に戻る。
"""

from datetime import date

import pytest

from ichthyosis_curator.curation.themes import (
    THEMES,
    THEMES_BY_KEY,
    all_pubmed_queries,
    detect_themes,
    rotating_themes,
)


def test_テーマのキーは重複しない():
    keys = [t.key for t in THEMES]
    assert len(keys) == len(set(keys))


def test_全テーマに判定語と検索クエリがある():
    for theme in THEMES:
        assert theme.keywords, f"{theme.key} に判定語がない"
        assert theme.queries_ja or theme.queries_en, f"{theme.key} に検索クエリがない"


@pytest.mark.parametrize("text,expected", [
    ("夏の汗で悪化するため保育園の先生に相談した", {"heat", "school"}),
    ("眼瞼外反の手術について", {"eye"}),
    ("耳垢が詰まって聞こえにくい", {"ear"}),
    ("医療費助成の申請に必要な書類", {"support"}),
    ("Ichthyosis and heat intolerance in summer", {"heat"}),
])
def test_本文からテーマを判定できる(text: str, expected: set):
    assert expected <= set(detect_themes(text))


def test_関係ない文章ではテーマが立たない():
    assert detect_themes("本日のシステムメンテナンスのお知らせ") == []
    assert detect_themes("") == []


def test_日替わりでテーマが一巡する():
    seen = set()
    for offset in range(len(THEMES)):
        day = date(2026, 1, 1).toordinal() + offset
        seen.update(t.key for t in rotating_themes(3, date.fromordinal(day)))
    # 数日回せば全テーマが登場する
    assert seen == set(THEMES_BY_KEY)


def test_同じ日なら同じテーマが返る():
    day = date(2026, 8, 30)
    assert [t.key for t in rotating_themes(4, day)] == [t.key for t in rotating_themes(4, day)]


def test_要求数がテーマ数以上なら全部返す():
    assert len(rotating_themes(999, date(2026, 8, 30))) == len(THEMES)


def test_生活場面の空白を埋めるテーマが定義されている():
    # 実データで収集ゼロ〜数件だった場面
    for key in ("school", "heat", "support", "ear", "eye", "travel"):
        assert key in THEMES_BY_KEY


def test_PubMedクエリは臨床文献のあるテーマにだけある():
    queries = all_pubmed_queries()
    assert queries
    assert all("ichthyosis" in q.lower() or "collodion" in q.lower() for q in queries)
