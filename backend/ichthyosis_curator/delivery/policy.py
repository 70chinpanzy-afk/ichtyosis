"""LINE配信ポリシー: 週次まとめ + 締切・速報だけ即時

毎日プッシュすると、重複記事と日常ケアの一般論が繰り返されて通知疲れを起こす。
そこで配信を2系統に分ける:

  - 週次まとめ（月曜）: 直近7日ぶんをスコア順にまとめて1回
  - 即時アラート: 締切・募集・承認など「期限があって行動が決まるもの」だけ

即時送信済みの記事は alerted.json に記録し、週次まとめの本文からは外す
（ヘッダーに件数だけ出して「今週の速報◯件は送信済み」と分かるようにする）。
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from ichthyosis_curator.identifiers import compute_article_hash
from ichthyosis_curator.curation.history import load_recent_items
from ichthyosis_curator.timeutil import today_jst
from ichthyosis_curator.schemas import DeliveryItem

logger = logging.getLogger(__name__)

# --- 即時アラートの判定基準 ---
# 「期限があって行動が決まるもの」だけを通す。緩めると週次集約の意味がなくなる。
URGENT_SCORE_THRESHOLD = 0.9
URGENT_CATEGORIES = {"新薬・治療法", "ニュース", "制度・支援"}

# キーワード側は誤爆（研究論文の「FDA承認を目指す」等）を避けるため
# スコア下限と併用する
URGENT_KEYWORD_MIN_SCORE = 0.7
URGENT_KEYWORDS_JA = (
    "承認", "募集", "締切", "締め切り", "助成", "申請",
    "認定", "認可", "給付", "公募", "治験参加",
)
URGENT_KEYWORDS_EN = (
    "approval", "approved", "recruiting", "enrolling",
    "deadline", "grant", "authorized",
)

# 1日に即時送信する上限。悪い日に通知が連発するのを防ぐ
MAX_URGENT_PER_RUN = 3

WEEKLY_WEEKDAY = 0  # 月曜
WEEKLY_LIMIT = 10
ALERTED_FILENAME = "alerted.json"
ALERTED_RETENTION_DAYS = 90


def _today() -> date:
    return today_jst()


def item_hash(item: DeliveryItem) -> str:
    return compute_article_hash(item.source, item.source_id)


def is_urgent(item: DeliveryItem) -> bool:
    """この記事を即時アラートとして送るべきか"""
    haystack = " ".join(
        [item.title_ja or "", item.original_title or "", item.summary_ja or ""]
    )
    lowered = haystack.lower()

    if item.relevance_score >= URGENT_KEYWORD_MIN_SCORE:
        if any(kw in haystack for kw in URGENT_KEYWORDS_JA):
            return True
        if any(kw in lowered for kw in URGENT_KEYWORDS_EN):
            return True

    if item.relevance_score >= URGENT_SCORE_THRESHOLD and item.category in URGENT_CATEGORIES:
        return True

    return False


def select_urgent(
    items: list[DeliveryItem],
    already_alerted: set[str] | None = None,
    limit: int = MAX_URGENT_PER_RUN,
) -> list[DeliveryItem]:
    """即時アラート対象をスコア降順で最大 limit 件返す"""
    already_alerted = already_alerted or set()
    urgent = [
        item
        for item in items
        if is_urgent(item) and item_hash(item) not in already_alerted
    ]
    urgent.sort(key=lambda i: i.relevance_score, reverse=True)
    return urgent[:limit]


def should_send_weekly(today: date | None = None) -> bool:
    """週次まとめを送る日か（月曜）"""
    today = today or _today()
    return today.weekday() == WEEKLY_WEEKDAY


def build_weekly_items(
    data_dir: str,
    today_items: list[DeliveryItem],
    days: int = 7,
    limit: int = WEEKLY_LIMIT,
    exclude: set[str] | None = None,
    today: date | None = None,
) -> list[DeliveryItem]:
    """直近 days 日ぶんの記事を重複排除してスコア降順に最大 limit 件返す。

    today_items は当日ぶん（まだ digests/*.json に書き出されていない）。
    exclude には即時送信済みのハッシュを渡す。
    """
    exclude = exclude or set()
    past_items = load_recent_items(data_dir, days=days, today=today)

    merged: dict[str, DeliveryItem] = {}
    # 当日ぶんを先に入れて、同一記事が過去日にもある場合は当日版を優先する
    for item in list(today_items) + past_items:
        h = item_hash(item)
        if h in exclude or h in merged:
            continue
        merged[h] = item

    result = sorted(merged.values(), key=lambda i: i.relevance_score, reverse=True)
    return result[:limit]


# --- 即時送信済みの記録（alerted.json） ---
# 記事IDとタイトルのみで個人情報を含まないため公開データ側に置いてよい


def _alerted_path(data_dir: str) -> Path:
    return Path(data_dir) / ALERTED_FILENAME


def _read_alerted(data_dir: str) -> list[dict]:
    path = _alerted_path(data_dir)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"{ALERTED_FILENAME} の読み込みに失敗したため空として扱います: {e}")
        return []
    if not isinstance(data, list):
        logger.warning(f"{ALERTED_FILENAME} の中身が配列でないため空として扱います")
        return []
    return [row for row in data if isinstance(row, dict)]


def load_alerted(data_dir: str, days: int = 30, today: date | None = None) -> set[str]:
    """直近 days 日ぶんの即時送信済みハッシュを返す"""
    today = today or _today()
    since = today - timedelta(days=days)

    hashes: set[str] = set()
    for row in _read_alerted(data_dir):
        h = row.get("hash")
        if not h:
            continue
        raw_date = row.get("date")
        if raw_date:
            try:
                if datetime.strptime(raw_date, "%Y-%m-%d").date() < since:
                    continue
            except ValueError:
                pass
        hashes.add(h)
    return hashes


def record_alerted(
    data_dir: str, items: list[DeliveryItem], today: date | None = None
) -> None:
    """即時送信した記事を alerted.json に追記し、古い記録を捨てる"""
    if not items:
        return

    today = today or _today()
    cutoff = today - timedelta(days=ALERTED_RETENTION_DAYS)
    today_str = today.strftime("%Y-%m-%d")

    rows = []
    for row in _read_alerted(data_dir):
        raw_date = row.get("date")
        if raw_date:
            try:
                if datetime.strptime(raw_date, "%Y-%m-%d").date() < cutoff:
                    continue
            except ValueError:
                pass
        rows.append(row)

    known = {row.get("hash") for row in rows}
    for item in items:
        h = item_hash(item)
        if h in known:
            continue
        rows.append({
            "hash": h,
            "date": today_str,
            "title": item.title_ja or item.original_title or "",
        })
        known.add(h)

    path = _alerted_path(data_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error(f"{ALERTED_FILENAME} の書き込みに失敗: {e}")
