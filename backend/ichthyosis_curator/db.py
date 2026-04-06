"""SQLiteデータベース操作モジュール"""

import sqlite3
import json
from datetime import datetime
from typing import Optional
from contextlib import contextmanager


@contextmanager
def get_db_connection(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_hash TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT,
                url TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS curated_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                digest_date TEXT NOT NULL,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                original_title TEXT,
                title_ja TEXT,
                summary_ja TEXT,
                category TEXT,
                relevance_score REAL,
                url TEXT,
                published_date TEXT,
                curation_reasoning TEXT,
                drugs_json TEXT DEFAULT '[]',
                patient_insight TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 既存テーブルにdrugs_jsonカラムがない場合は追加（マイグレーション）
        try:
            cursor.execute("SELECT drugs_json FROM curated_articles LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE curated_articles ADD COLUMN drugs_json TEXT DEFAULT '[]'")

        # 既存テーブルにpatient_insightカラムがない場合は追加（マイグレーション）
        try:
            cursor.execute("SELECT patient_insight FROM curated_articles LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE curated_articles ADD COLUMN patient_insight TEXT DEFAULT ''")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sources_scanned INTEGER DEFAULT 0,
                articles_found INTEGER DEFAULT 0,
                articles_curated INTEGER DEFAULT 0,
                articles_sent INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ok',
                error_message TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_article_hash
            ON seen_articles(article_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_digest_date
            ON curated_articles(digest_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_curated_category
            ON curated_articles(category)
        """)


def is_article_seen(db_path: str, article_hash: str) -> bool:
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM seen_articles WHERE article_hash = ?",
            (article_hash,),
        )
        return cursor.fetchone() is not None


def mark_article_seen(
    db_path: str,
    article_hash: str,
    source: str,
    source_id: str,
    title: str,
    url: str,
) -> None:
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO seen_articles
            (article_hash, source, source_id, title, url)
            VALUES (?, ?, ?, ?, ?)""",
            (article_hash, source, source_id, title, url),
        )


def save_curated_article(
    db_path: str,
    digest_date: str,
    source: str,
    source_id: str,
    original_title: str,
    title_ja: str,
    summary_ja: str,
    category: str,
    relevance_score: float,
    url: str,
    published_date: Optional[str],
    curation_reasoning: str,
    drugs_json: str = "[]",
    patient_insight: str = "",
) -> int:
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO curated_articles
            (digest_date, source, source_id, original_title, title_ja, summary_ja,
             category, relevance_score, url, published_date, curation_reasoning,
             drugs_json, patient_insight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                digest_date, source, source_id, original_title, title_ja,
                summary_ja, category, relevance_score, url, published_date,
                curation_reasoning, drugs_json, patient_insight,
            ),
        )
        return cursor.lastrowid


def get_digest_dates(db_path: str, limit: int = 30) -> list[str]:
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT DISTINCT digest_date FROM curated_articles
            ORDER BY digest_date DESC LIMIT ?""",
            (limit,),
        )
        return [row["digest_date"] for row in cursor.fetchall()]


def get_articles_by_date(db_path: str, digest_date: str) -> list[dict]:
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM curated_articles
            WHERE digest_date = ?
            ORDER BY relevance_score DESC""",
            (digest_date,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_article_by_id(db_path: str, article_id: int) -> Optional[dict]:
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM curated_articles WHERE id = ?", (article_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def search_articles(db_path: str, query: str, limit: int = 50) -> list[dict]:
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        like_q = f"%{query}%"
        cursor.execute(
            """SELECT * FROM curated_articles
            WHERE title_ja LIKE ? OR summary_ja LIKE ? OR original_title LIKE ?
            ORDER BY digest_date DESC, relevance_score DESC
            LIMIT ?""",
            (like_q, like_q, like_q, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def log_run(
    db_path: str,
    sources_scanned: int,
    articles_found: int,
    articles_curated: int,
    articles_sent: int,
    status: str = "ok",
    error_message: Optional[str] = None,
) -> None:
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO run_log
            (sources_scanned, articles_found, articles_curated, articles_sent, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (sources_scanned, articles_found, articles_curated, articles_sent, status, error_message),
        )
