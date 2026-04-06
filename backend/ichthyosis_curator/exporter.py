"""静的JSONエクスポーター: DB → frontend/public/data/ にJSONファイルを出力"""

import json
import os
import logging
from pathlib import Path

from ichthyosis_curator.db import get_digest_dates, get_articles_by_date, get_article_by_id

logger = logging.getLogger(__name__)


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

        # 日別JSON
        with open(out / "digests" / f"{date}.json", "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2, default=str)

        # 個別article JSON
        for article in articles:
            article_path = out / "articles" / f"{article['id']}.json"
            with open(article_path, "w", encoding="utf-8") as f:
                json.dump(article, f, ensure_ascii=False, indent=2, default=str)

        total_articles += len(articles)

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
