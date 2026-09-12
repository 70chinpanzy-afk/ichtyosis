"""テーマ索引（困りごとから記事を引くためのインデックス）のテスト

記事が日付順にしか並んでおらず、5か月ぶんの蓄積が読み返せなかった。
テーマは本文から決まる派生データなので、DBに列を足さずエクスポート時に計算する。
"""

import json
from pathlib import Path

import pytest

from ichthyosis_curator.curation.themes import THEMES
from ichthyosis_curator.exporter import _backfill_slugs
from ichthyosis_curator.identifiers import article_slug


def _write_digest(out: Path, day: str, rows: list[dict]) -> None:
    (out / "digests").mkdir(parents=True, exist_ok=True)
    (out / "digests" / f"{day}.json").write_text(
        json.dumps(rows, ensure_ascii=False), encoding="utf-8"
    )


def _row(source_id: str, title: str, summary: str = "", **kwargs) -> dict:
    row = {
        "id": 1,
        "source": "pubmed",
        "source_id": source_id,
        "title_ja": title,
        "summary_ja": summary,
        "patient_insight": "",
        "original_title": "",
        "category": "ケア・対処法",
        "relevance_score": 0.7,
        "url": "https://example.com",
    }
    row.update(kwargs)
    return row


@pytest.fixture
def out(tmp_path: Path) -> Path:
    (tmp_path / "articles").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _themes_index(out: Path) -> dict[str, dict]:
    return {t["key"]: t for t in json.loads((out / "themes.json").read_text())}


def test_本文からテーマを判定して索引に載せる(out: Path):
    _write_digest(out, "2026-09-01", [
        _row("a", "夏の汗と体温調節の工夫"),
        _row("b", "保育園の先生への説明"),
    ])

    _backfill_slugs(out)

    index = _themes_index(out)
    assert index["heat"]["count"] == 1
    assert index["school"]["count"] == 1
    assert index["heat"]["label"] == "夏の汗・体温調節"


def test_1つの記事が複数テーマに載る(out: Path):
    _write_digest(out, "2026-09-01", [_row("a", "夏の汗で悪化するので保育園に相談した")])

    _backfill_slugs(out)

    index = _themes_index(out)
    assert index["heat"]["count"] == 1
    assert index["school"]["count"] == 1


def test_該当なしのテーマも件数0で残す(out: Path):
    # 将来埋まる場所が見えているほうがよいので、0件でも索引から消さない
    _write_digest(out, "2026-09-01", [_row("a", "夏の汗の話")])

    _backfill_slugs(out)

    index = _themes_index(out)
    assert len(index) == len(THEMES)
    assert index["ear"]["count"] == 0
    assert json.loads((out / "themes" / "ear.json").read_text()) == []


def test_テーマ別ファイルはスコア降順(out: Path):
    _write_digest(out, "2026-09-01", [
        _row("low", "夏の汗について", relevance_score=0.4),
        _row("high", "夏の汗と熱中症", relevance_score=0.9),
    ])

    _backfill_slugs(out)

    items = json.loads((out / "themes" / "heat.json").read_text())
    assert [a["relevance_score"] for a in items] == [0.9, 0.4]


def test_記事行にもテーマが書き戻される(out: Path):
    _write_digest(out, "2026-09-01", [_row("a", "耳垢が詰まって聞こえにくい")])

    _backfill_slugs(out)

    row = json.loads((out / "digests" / "2026-09-01.json").read_text())[0]
    assert row["themes"] == ["ear"]


def test_テーマ項目は記事ページへ辿れる情報を持つ(out: Path):
    _write_digest(out, "2026-09-01", [_row("a", "夏の汗の話", "要約です")])

    _backfill_slugs(out)

    item = json.loads((out / "themes" / "heat.json").read_text())[0]
    assert item["slug"] == article_slug("pubmed", "a")
    assert item["date"] == "2026-09-01"
    assert item["summary_ja"] == "要約です"


def test_同じ記事が複数日にあっても索引では1件(out: Path):
    _write_digest(out, "2026-09-01", [_row("a", "夏の汗の話", relevance_score=0.5)])
    _write_digest(out, "2026-09-02", [_row("a", "夏の汗の話（訳し直し）", relevance_score=0.5)])

    _backfill_slugs(out)

    items = json.loads((out / "themes" / "heat.json").read_text())
    assert len(items) == 1
    # 最新日の版を採用する
    assert items[0]["title_ja"] == "夏の汗の話（訳し直し）"


def test_二回実行しても差分が出ない(out: Path):
    _write_digest(out, "2026-09-01", [_row("a", "夏の汗の話")])
    _backfill_slugs(out)
    before = (out / "themes" / "heat.json").read_text()

    assert _backfill_slugs(out) == (0, 0)
    assert (out / "themes" / "heat.json").read_text() == before
