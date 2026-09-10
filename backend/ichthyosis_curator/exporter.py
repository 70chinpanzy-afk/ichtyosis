"""静的JSONエクスポーター: DB → frontend/public/data/ にJSONファイルを出力"""

import json
import os
import re
import logging
from pathlib import Path

from ichthyosis_curator.db import get_digest_dates, get_articles_by_date, get_article_by_id
from ichthyosis_curator.identifiers import article_slug

logger = logging.getLogger(__name__)

_DATE_FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")


def _write_article(out: Path, article: dict) -> None:
    """個別article JSONを slug 名で書き出す（旧 id 名も後方互換で残す）"""
    slug = article.get("slug") or article_slug(
        article.get("source", ""), article.get("source_id", "")
    )
    if slug:
        article["slug"] = slug
        with open(out / "articles" / f"{slug}.json", "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=2, default=str)

    # 既存の /article/<id> リンクを壊さないため id 名でも残す
    if article.get("id") is not None:
        with open(out / "articles" / f"{article['id']}.json", "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=2, default=str)


def _backfill_slugs(out: Path) -> tuple[int, int]:
    """既存の digests/*.json に slug を付与し、articles/<slug>.json を補完する。

    DBの id は CI 実行のたびに 1 から振り直されるため、過去日の
    articles/<id>.json は翌日の実行で上書きされ、過去記事ページが
    別記事の内容になっていた。digest ファイル自体は日付ごとに正しい
    内容を保持しているので、そこから slug 単位のファイルを作り直せば
    アーカイブ全体を復旧できる。

    同じ記事が複数の日に再キュレーションされている場合（要約の訳文が
    日によって異なる）は、最も新しい日付の版を記事ページの内容とする。

    Returns:
        (slugを付けた行数, 書き出したarticleファイル数)
    """
    digests_dir = out / "digests"
    if not digests_dir.exists():
        return (0, 0)

    articles_dir = out / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    rows_updated = 0
    # slug -> (digest_date, row)。日付が新しいものを採用する
    latest: dict[str, tuple[str, dict]] = {}

    for path in sorted(digests_dir.iterdir()):
        if not path.is_file():
            continue
        m = _DATE_FILENAME_RE.match(path.name)
        if not m:
            continue
        file_date = m.group(1)
        try:
            with open(path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"digests/{path.name} の読み込みに失敗したためスキップ: {e}")
            continue
        if not isinstance(rows, list):
            continue

        changed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            slug = article_slug(row.get("source", ""), row.get("source_id", ""))
            if not slug:
                continue
            if row.get("slug") != slug:
                row["slug"] = slug
                rows_updated += 1
                changed = True

            known = latest.get(slug)
            if known is None or file_date >= known[0]:
                latest[slug] = (file_date, row)

        if changed:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
            except OSError as e:
                logger.warning(f"digests/{path.name} の書き戻しに失敗: {e}")

    articles_written = 0
    for slug, (_, row) in latest.items():
        article_path = articles_dir / f"{slug}.json"
        payload = json.dumps(row, ensure_ascii=False, indent=2, default=str)
        # 内容が変わらないなら書かない（毎回の差分を無駄に増やさない）
        if article_path.exists():
            try:
                if article_path.read_text(encoding="utf-8") == payload:
                    continue
            except OSError:
                pass
        try:
            article_path.write_text(payload, encoding="utf-8")
            articles_written += 1
        except OSError as e:
            logger.warning(f"articles/{slug}.json の書き込みに失敗: {e}")

    return (rows_updated, articles_written)


def export_static_json(db_path: str, output_dir: str) -> int:
    """
    SQLiteの全キュレーションデータを静的JSONファイルとしてエクスポート。
    既存のJSONファイルを保持しつつ、新しいデータをマージする。

    出力ファイル構成:
      data/
        digests.json           - 日付一覧 [{date, article_count}, ...]
        digests/
          2025-03-15.json      - 各日のarticle配列
        articles/
          1.json, 2.json, ...  - 個別article

    Returns:
        エクスポートした記事数
    """
    out = Path(output_dir)

    # ディレクトリ作成
    (out / "digests").mkdir(parents=True, exist_ok=True)
    (out / "articles").mkdir(parents=True, exist_ok=True)

    # 日付一覧取得（DBから）
    dates = get_digest_dates(db_path, limit=365)
    total_articles = 0

    for date in dates:
        articles = get_articles_by_date(db_path, date)
        for article in articles:
            article["slug"] = article_slug(
                article.get("source", ""), article.get("source_id", "")
            )

        # 日別JSON
        with open(out / "digests" / f"{date}.json", "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2, default=str)

        # 個別article JSON
        for article in articles:
            _write_article(out, article)

        total_articles += len(articles)

    # 過去ぶんの slug バックフィル（過去記事ページが別記事を指す問題の解消）
    backfilled_rows, backfilled_articles = _backfill_slugs(out)
    if backfilled_rows or backfilled_articles:
        logger.info(
            f"slugバックフィル: {backfilled_rows} 行に slug を付与、"
            f"{backfilled_articles} 件の articles/<slug>.json を生成"
        )

    # digests一覧JSON: 既存ファイル + DBデータをマージ
    digest_map = {}

    # 1. 既存のdigests.jsonを読み込み
    digests_path = out / "digests.json"
    if digests_path.exists():
        try:
            with open(digests_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            for entry in existing:
                digest_map[entry["date"]] = entry["article_count"]
        except (json.JSONDecodeError, KeyError):
            pass

    # 2. 既存の日付別JSONファイルからも補完
    for digest_file in (out / "digests").glob("*.json"):
        date = digest_file.stem
        if date not in digest_map:
            try:
                with open(digest_file, "r", encoding="utf-8") as f:
                    articles_data = json.load(f)
                digest_map[date] = len(articles_data)
            except (json.JSONDecodeError, ValueError):
                pass

    # 3. DBからの新データで上書き
    for date in dates:
        articles = get_articles_by_date(db_path, date)
        digest_map[date] = len(articles)

    # 日付降順でソート
    digest_list = [
        {"date": d, "article_count": c}
        for d, c in sorted(digest_map.items(), reverse=True)
    ]

    with open(digests_path, "w", encoding="utf-8") as f:
        json.dump(digest_list, f, ensure_ascii=False, indent=2)

    logger.info(f"エクスポート完了: {len(digest_list)} dates, {total_articles} new articles → {output_dir}")
    return total_articles
