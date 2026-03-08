# history_repo.py
import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple

@dataclass(frozen=True)
class HistoryRow:
    id: int
    created_at: str
    customer_name: str
    customer_company: str
    meeting_date: str
    mode: str
    tone: str
    memo: str
    response_json: str

def init_history_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            customer_name TEXT,
            customer_company TEXT,
            meeting_date TEXT,
            mode TEXT,
            tone TEXT,
            memo TEXT,
            response_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_history(
    db_path: str,
    customer_name: str,
    customer_company: str,
    meeting_date: str,
    mode: str,
    tone: str,
    memo: str,
    response_obj: dict
) -> int:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO history (
            created_at, customer_name, customer_company, meeting_date, mode, tone, memo, response_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        customer_name, customer_company, meeting_date, mode, tone, memo,
        json.dumps(response_obj, ensure_ascii=False),
    ))
    conn.commit()
    new_id = int(cur.lastrowid)
    conn.close()
    return new_id

def list_history(db_path: str, limit: int = 30) -> List[Tuple]:
    limit = max(1, int(limit))
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # response_json も取得して、失敗履歴を識別できるようにする
    cur.execute("""
        SELECT id, created_at, customer_company, customer_name, meeting_date, mode, tone, response_json
        FROM history
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows
from typing import List, Dict
import sqlite3


def list_history_by_customer(
    db_path: str,
    company: str,
    name: str,
) -> List[Dict]:
    """
    会社名＋顧客名で履歴を取得（新しい順）
    空文字は無効扱い
    """

    company = (company or "").strip()
    name = (name or "").strip()

    if not company or not name:
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, created_at, customer_company, customer_name,
               meeting_date, mode, tone, response_json
        FROM history
        WHERE customer_company = ?
          AND customer_name = ?
        ORDER BY id DESC
        """,
        (company, name),
    )

    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]

def load_history(db_path: str, history_id: int) -> Optional[HistoryRow]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, created_at, customer_name, customer_company, meeting_date, mode, tone, memo, response_json
        FROM historyå
        WHERE id = ?
    """, (history_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return HistoryRow(*row)
