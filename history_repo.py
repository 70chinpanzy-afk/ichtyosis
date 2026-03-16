# history_repo.py
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Json
except Exception:  # pragma: no cover - optional dependency at runtime
    psycopg = None
    dict_row = None
    Json = None


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


def _connect(db_url: str) -> psycopg.Connection:
    if psycopg is None or dict_row is None:
        raise RuntimeError("psycopg is not installed. Install requirements-ui.txt or requirements.txt")
    if not (db_url or "").strip():
        raise RuntimeError("History database URL is empty")
    return psycopg.connect(db_url, row_factory=dict_row)


def _to_text(dt: datetime | str | None) -> str:
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


def init_history_db(db_path: str) -> None:
    with _connect(db_path) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    customer_name TEXT,
                    customer_company TEXT,
                    meeting_date TEXT,
                    mode TEXT,
                    tone TEXT,
                    memo TEXT,
                    response_json JSONB
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_history_company_name
                ON history(customer_company, customer_name);
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_history_created_at
                ON history(created_at DESC);
                """
            )


def save_history(
    db_path: str,
    customer_name: str,
    customer_company: str,
    meeting_date: str,
    mode: str,
    tone: str,
    memo: str,
    response_obj: dict,
) -> int:
    with _connect(db_path) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO history (
                    customer_name,
                    customer_company,
                    meeting_date,
                    mode,
                    tone,
                    memo,
                    response_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    customer_name,
                    customer_company,
                    meeting_date,
                    mode,
                    tone,
                    memo,
                    Json(response_obj),
                ),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Failed to insert history row")
            return int(row["id"])


def list_history(db_path: str, limit: int = 30) -> List[Tuple]:
    limit = max(1, int(limit))
    with _connect(db_path) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    created_at,
                    customer_company,
                    customer_name,
                    meeting_date,
                    mode,
                    tone,
                    response_json
                FROM history
                ORDER BY id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()

    out: List[Tuple] = []
    for row in rows:
        response_json = row.get("response_json")
        if response_json is None:
            response_json_text = None
        elif isinstance(response_json, str):
            response_json_text = response_json
        else:
            response_json_text = json.dumps(response_json, ensure_ascii=False)

        out.append(
            (
                int(row["id"]),
                _to_text(row.get("created_at")),
                row.get("customer_company"),
                row.get("customer_name"),
                row.get("meeting_date"),
                row.get("mode"),
                row.get("tone"),
                response_json_text,
            )
        )
    return out


def list_history_by_customer(
    db_path: str,
    company: str,
    name: str,
) -> List[Dict]:
    company = (company or "").strip()
    name = (name or "").strip()

    if not company or not name:
        return []

    with _connect(db_path) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    created_at,
                    customer_company,
                    customer_name,
                    meeting_date,
                    mode,
                    tone,
                    response_json
                FROM history
                WHERE customer_company = %s
                  AND customer_name = %s
                ORDER BY id DESC;
                """,
                (company, name),
            )
            rows = cur.fetchall()

    result = []
    for row in rows:
        created_at = _to_text(row.get("created_at"))
        payload = dict(row)
        payload["created_at"] = created_at
        response_json = payload.get("response_json")
        if response_json is None:
            payload["response_json"] = None
        elif isinstance(response_json, str):
            payload["response_json"] = response_json
        else:
            payload["response_json"] = json.dumps(response_json, ensure_ascii=False)
        result.append(payload)
    return result


def load_history(db_path: str, history_id: int) -> Optional[HistoryRow]:
    with _connect(db_path) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    created_at,
                    customer_name,
                    customer_company,
                    meeting_date,
                    mode,
                    tone,
                    memo,
                    response_json
                FROM history
                WHERE id = %s;
                """,
                (history_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    response_json = row.get("response_json")
    if isinstance(response_json, str):
        response_json_text = response_json
    else:
        response_json_text = json.dumps(response_json, ensure_ascii=False)

    return HistoryRow(
        id=int(row["id"]),
        created_at=_to_text(row.get("created_at")),
        customer_name=row.get("customer_name") or "",
        customer_company=row.get("customer_company") or "",
        meeting_date=row.get("meeting_date") or "",
        mode=row.get("mode") or "",
        tone=row.get("tone") or "",
        memo=row.get("memo") or "",
        response_json=response_json_text,
    )
