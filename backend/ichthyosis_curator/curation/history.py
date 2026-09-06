"""配信履歴モジュール: コミット済みの digests/*.json を永続ストアとして扱う

GitHub Actions では SQLite DB が毎回空から生成されるため、DB ベースの
重複排除は日をまたいで機能しない（同じ記事が最大5日連続で再送されていた）。
一方 `frontend/public/data/digests/*.json` は毎日コミットされ、CI が
checkout するたびに手元に揃う。ここを実質的な永続ストアとして読むことで、
DB に依存せず日をまたいだ重複排除と週次まとめの構築ができる。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from ichthyosis_curator.identifiers import compute_article_hash
from ichthyosis_curator.timeutil import today_jst
from ichthyosis_curator.schemas import DeliveryItem

logger = logging.getLogger(__name__)

# exporter.py の _DATE_FILENAME_RE と同じ規約（YYYY-MM-DD.json のみ対象）
_DATE_FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")


def _today() -> date:
    return today_jst()


def _load_digest_files(data_dir: str, since: date) -> list[tuple[date, list[dict]]]:
    """digests/ 配下から since 以降の日付ファイルを読み、(日付, 記事行) を返す。

    ファイル名が YYYY-MM-DD.json でないもの、JSON として壊れているもの、
    中身が配列でないものはスキップする（exporter.py と同じ防御方針）。
    """
    digests_dir = Path(data_dir) / "digests"
    if not digests_dir.exists():
        logger.warning(f"digests ディレクトリが見つかりません: {digests_dir}")
        return []

    loaded: list[tuple[date, list[dict]]] = []
    for path in sorted(digests_dir.iterdir()):
        if not path.is_file():
            continue
        m = _DATE_FILENAME_RE.match(path.name)
        if not m:
            continue
        try:
            file_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if file_date < since:
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"digests/{path.name} の読み込みに失敗したためスキップ: {e}")
            continue
        if not isinstance(rows, list):
            logger.warning(f"digests/{path.name} の中身が配列でないためスキップ")
            continue
        loaded.append((file_date, rows))

    return loaded


def load_seen_hashes(data_dir: str, days: int = 60, today: date | None = None) -> set[str]:
    """直近 days 日ぶんの配信済み記事ハッシュを返す。

    source_id は PMID / NCT ID / URLハッシュ / YouTube動画ID のいずれかで、
    日をまたいで安定していることを実データで確認済み。
    """
    today = today or _today()
    since = today - timedelta(days=days)

    seen: set[str] = set()
    for _, rows in _load_digest_files(data_dir, since):
        for row in rows:
            source = row.get("source")
            source_id = row.get("source_id")
            if not source or not source_id:
                continue
            seen.add(compute_article_hash(source, source_id))

    logger.info(f"配信履歴: 直近{days}日で {len(seen)} 件の既出記事を読み込み")
    return seen


def load_recent_items(
    data_dir: str, days: int = 7, today: date | None = None
) -> list[DeliveryItem]:
    """直近 days 日ぶん（今日を含む期間）の記事を DeliveryItem として返す。

    今日ぶんの digests/*.json は curation 実行時点ではまだ書き出されていない
    （--export はワークフローの後段ステップ）ため、ここに含まれるのは
    基本的に前日までのぶん。当日ぶんは呼び出し側でメモリ上の結果を足す。
    """
    today = today or _today()
    since = today - timedelta(days=days - 1)

    items: list[DeliveryItem] = []
    for _, rows in _load_digest_files(data_dir, since):
        for row in rows:
            items.append(DeliveryItem.from_row(row))
    return items
