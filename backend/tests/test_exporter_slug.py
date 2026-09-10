"""記事slug（公開URL用の安定ID）のテスト

DBのidはCI実行ごとに1から振り直されるため、articles/<id>.json が
日々上書きされて過去記事ページが別記事の内容になっていた。
"""

import json
from pathlib import Path

import pytest

from ichthyosis_curator.exporter import _backfill_slugs, _write_article
from ichthyosis_curator.identifiers import article_slug


def _write_digest(out: Path, day: str, rows: list[dict]) -> None:
    (out / "digests").mkdir(parents=True, exist_ok=True)
    (out / "digests" / f"{day}.json").write_text(
        json.dumps(rows, ensure_ascii=False), encoding="utf-8"
    )


def _row(article_id: int, source_id: str, title: str, **kwargs) -> dict:
    row = {
        "id": article_id,
        "source": "pubmed",
        "source_id": source_id,
        "title_ja": title,
        "summary_ja": "要約",
        "url": "https://example.com",
    }
    row.update(kwargs)
    return row


@pytest.fixture
def out(tmp_path: Path) -> Path:
    (tmp_path / "articles").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_過去のdigestにslugを付けて記事ファイルを作る(out: Path):
    _write_digest(out, "2026-08-20", [_row(1, "aaa", "記事A")])

    rows_updated, articles_written = _backfill_slugs(out)

    assert (rows_updated, articles_written) == (1, 1)
    slug = article_slug("pubmed", "aaa")
    assert json.loads((out / "articles" / f"{slug}.json").read_text())["title_ja"] == "記事A"
    assert json.loads((out / "digests" / "2026-08-20.json").read_text())[0]["slug"] == slug


def test_二回実行しても何も変わらない(out: Path):
    _write_digest(out, "2026-08-20", [_row(1, "aaa", "記事A")])
    _backfill_slugs(out)

    assert _backfill_slugs(out) == (0, 0)


def test_日をまたいで衝突するidでも記事ページが混ざらない(out: Path):
    # CIではDBが毎回空から作られるので、別々の記事が同じ id=1 を持つ
    _write_digest(out, "2026-08-20", [_row(1, "aaa", "記事A")])
    _write_digest(out, "2026-08-21", [_row(1, "bbb", "記事B")])

    _backfill_slugs(out)

    a = json.loads((out / "articles" / f"{article_slug('pubmed', 'aaa')}.json").read_text())
    b = json.loads((out / "articles" / f"{article_slug('pubmed', 'bbb')}.json").read_text())
    assert a["title_ja"] == "記事A"
    assert b["title_ja"] == "記事B"


def test_同じ記事が再キュレーションされたら新しい日の版を使う(out: Path):
    # 同じ論文でも日によってLLMの訳文が変わるため、最新の版を記事ページにする
    _write_digest(out, "2026-08-20", [_row(1, "aaa", "古い訳")])
    _write_digest(out, "2026-08-21", [_row(1, "aaa", "新しい訳")])

    _backfill_slugs(out)

    slug = article_slug("pubmed", "aaa")
    assert json.loads((out / "articles" / f"{slug}.json").read_text())["title_ja"] == "新しい訳"


def test_壊れたファイルや想定外のファイル名は無視する(out: Path):
    _write_digest(out, "2026-08-20", [_row(1, "aaa", "記事A")])
    (out / "digests" / "2026-08-21.json").write_text("{ broken", encoding="utf-8")
    (out / "digests" / "notadate.json").write_text('[{"source": "x"}]', encoding="utf-8")

    rows_updated, articles_written = _backfill_slugs(out)

    assert (rows_updated, articles_written) == (1, 1)


def test_source情報が無い行はスキップする(out: Path):
    _write_digest(out, "2026-08-20", [{"id": 1, "title_ja": "壊れた行"}])

    assert _backfill_slugs(out) == (0, 0)


def test_digestsディレクトリが無くても落ちない(out: Path):
    assert _backfill_slugs(out) == (0, 0)


def test_記事ファイルはslug名とid名の両方で書かれる(out: Path):
    article = _row(7, "aaa", "記事A")

    _write_article(out, article)

    slug = article_slug("pubmed", "aaa")
    assert (out / "articles" / f"{slug}.json").exists()
    # 既存の /article/7 リンクを壊さないため id 名も残す
    assert (out / "articles" / "7.json").exists()
    assert article["slug"] == slug
