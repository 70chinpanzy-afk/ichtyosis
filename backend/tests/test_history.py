"""配信履歴（digests/*.json を永続ストアとして読む部分）のテスト"""

import json
from datetime import date
from pathlib import Path

import pytest

from ichthyosis_curator.curation.dedup import compute_article_hash, filter_unseen_raw
from ichthyosis_curator.curation.history import load_recent_items, load_seen_hashes
from ichthyosis_curator.identifiers import article_slug
from ichthyosis_curator.schemas import RawArticle


def _write_digest(data_dir: Path, day: str, rows: list[dict]) -> None:
    digests = data_dir / "digests"
    digests.mkdir(parents=True, exist_ok=True)
    (digests / f"{day}.json").write_text(
        json.dumps(rows, ensure_ascii=False), encoding="utf-8"
    )


def _row(source: str, source_id: str, **kwargs) -> dict:
    row = {
        "id": 1,
        "digest_date": "2026-08-20",
        "source": source,
        "source_id": source_id,
        "original_title": "Title",
        "title_ja": "タイトル",
        "summary_ja": "要約",
        "patient_insight": "ポイント",
        "category": "ケア・対処法",
        "relevance_score": 0.7,
        "url": "https://example.com/a",
        "region": "international",  # 現行スキーマにないキー（過去データに存在する）
    }
    row.update(kwargs)
    return row


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    _write_digest(tmp_path, "2026-08-20", [_row("pubmed", "111")])
    _write_digest(tmp_path, "2026-08-21", [_row("pubmed", "222"), _row("youtube:ch", "aaa")])
    return tmp_path


def test_既出ハッシュを日付をまたいで集められる(data_dir: Path):
    seen = load_seen_hashes(str(data_dir), days=60, today=date(2026, 8, 22))
    assert compute_article_hash("pubmed", "111") in seen
    assert compute_article_hash("youtube:ch", "aaa") in seen
    assert len(seen) == 3


def test_期間外の日付は履歴に含めない(data_dir: Path):
    # days=1 は「1日前（8/21）まで遡る」の意味なので 8/20 は window の外
    seen = load_seen_hashes(str(data_dir), days=1, today=date(2026, 8, 22))
    assert compute_article_hash("pubmed", "111") not in seen
    assert compute_article_hash("pubmed", "222") in seen


def test_壊れたファイルと想定外のファイル名はスキップされる(tmp_path: Path):
    _write_digest(tmp_path, "2026-08-21", [_row("pubmed", "222")])
    digests = tmp_path / "digests"
    (digests / "2026-08-22.json").write_text("{ broken", encoding="utf-8")
    (digests / "digests.json").write_text('["not a digest"]', encoding="utf-8")
    (digests / "2026-08-23.json").write_text('{"not": "a list"}', encoding="utf-8")

    seen = load_seen_hashes(str(tmp_path), days=60, today=date(2026, 8, 23))
    assert seen == {compute_article_hash("pubmed", "222")}


def test_digestsディレクトリが無くても落ちない(tmp_path: Path):
    assert load_seen_hashes(str(tmp_path), today=date(2026, 8, 22)) == set()


def test_raw段階でLLM実行前に既出を落とす(data_dir: Path):
    seen = load_seen_hashes(str(data_dir), today=date(2026, 8, 22))
    raw = [
        RawArticle(source="pubmed", source_id="111", title="既出", url="https://a"),
        RawArticle(source="pubmed", source_id="999", title="新着", url="https://b"),
    ]
    unseen = filter_unseen_raw(raw, seen)
    assert [a.source_id for a in unseen] == ["999"]


def test_過去記事をDeliveryItemとして復元できる(data_dir: Path):
    items = load_recent_items(str(data_dir), days=7, today=date(2026, 8, 22))
    assert len(items) == 3
    item = items[0]
    # region など現行スキーマに無いキーがあっても復元できる
    assert item.patient_insight == "ポイント"
    # 公開URLはDBのidではなく (source, source_id) 由来の安定slugを使う
    assert item.slug == article_slug(item.source, item.source_id)


def test_旧カテゴリの過去データも復元できる(tmp_path: Path):
    # sales系プロンプトが混入していた時期のデータが実際に残っている
    _write_digest(tmp_path, "2026-08-21", [_row("google_news", "x", category="経済・ビジネス")])
    items = load_recent_items(str(tmp_path), days=7, today=date(2026, 8, 22))
    assert items[0].category == "経済・ビジネス"
