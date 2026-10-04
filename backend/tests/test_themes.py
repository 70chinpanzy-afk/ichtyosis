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


# --- 打ち消し文の扱い ---
# 「この病気は感染するものではありません」という説明文が感染症テーマに当たり、
# いじめの解説記事が感染症の記事として並んでいた


@pytest.mark.parametrize("text", [
    "この病気は感染するものではありません",
    "魚鱗癬は感染しません。見た目の誤解を解くことが大切です",
    "触れてもうつりません",
])
def test_打ち消し文は該当とみなさない(text: str):
    assert "infection" not in detect_themes(text)


@pytest.mark.parametrize("text", [
    "基礎的な感染対策を工夫し命を救えた",
    "感染のリスクが高まるため清潔に保つ",
    "感染の徴候が見られた女児のケア方法",
])
def test_実際に感染を扱う記述は拾う(text: str):
    assert "infection" in detect_themes(text)


def test_二重否定を打ち消しと誤認しない():
    assert "infection" in detect_themes("皮膚の感染症は珍しくありません")


# --- 実データで見つかった判定漏れ ---


def test_カタカナ表記の病名を拾う():
    # 英語の ectropion では当たらず、Eye Care ガイドが保湿剤テーマにしか入らなかった
    assert "eye" in detect_themes("エクトロピオンという目の病状についても触れています")


def test_目のケアという言い回しを拾う():
    assert "eye" in detect_themes("魚鱗癬を持つ子供の目のケア方法について")


def test_大学生は学校テーマに入れる():
    assert "school" in detect_themes("魚鱗癬を持つ大学生のための生活ガイド。寮の担当者と相談する")


def test_大学病院は学校テーマに入れない():
    # 素の「大学」を判定語にしていたとき、論文記事が学校テーマに混ざっていた
    assert "school" not in detect_themes("研究はイタリアの8つの大学病院で行われました")


def test_友達への伝え方は気持ちのテーマに入れる():
    assert "mental" in detect_themes("友達に自分の病気をどう伝えるか、自信を持って話せるように")
