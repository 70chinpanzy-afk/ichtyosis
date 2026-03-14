"""PostgreSQL database module for Sales Copilot."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, List, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return database_url


@contextmanager
def get_db_connection() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(get_database_url(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id BIGSERIAL PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    customer_company TEXT NOT NULL,
                    conversation_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversations_customer_id
                ON conversations(customer_id);
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversations_created_at
                ON conversations(created_at DESC);
                """
            )


def check_db_health() -> bool:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                row = cur.fetchone()
                return bool(row)
    except Exception:
        return False


def _format_row(row: dict) -> dict:
    metadata = row.get("metadata")
    created_at = row.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    return {
        "id": row.get("id"),
        "customer_id": row.get("customer_id"),
        "customer_name": row.get("customer_name"),
        "customer_company": row.get("customer_company"),
        "conversation_type": row.get("conversation_type"),
        "content": row.get("content"),
        "metadata": metadata,
        "created_at": created_at,
    }


def save_conversation(
    customer_id: str,
    customer_name: str,
    customer_company: str,
    conversation_type: str,
    content: str,
    metadata: Optional[dict] = None,
) -> int:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (
                    customer_id,
                    customer_name,
                    customer_company,
                    conversation_type,
                    content,
                    metadata
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    customer_id,
                    customer_name,
                    customer_company,
                    conversation_type,
                    content,
                    Json(metadata) if metadata is not None else None,
                ),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Failed to insert conversation")
            return int(row["id"])


def get_conversations_by_customer(customer_id: str, limit: int = 50) -> List[dict]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    customer_id,
                    customer_name,
                    customer_company,
                    conversation_type,
                    content,
                    metadata,
                    created_at
                FROM conversations
                WHERE customer_id = %s
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (customer_id, limit),
            )
            rows = cur.fetchall()
    return [_format_row(row) for row in rows]


def get_all_conversations(limit: int = 100) -> List[dict]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    customer_id,
                    customer_name,
                    customer_company,
                    conversation_type,
                    content,
                    metadata,
                    created_at
                FROM conversations
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()
    return [_format_row(row) for row in rows]


def delete_conversation(conversation_id: int) -> bool:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM conversations WHERE id = %s;", (conversation_id,))
            return cur.rowcount > 0
