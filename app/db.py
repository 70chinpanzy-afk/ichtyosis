"""SQLiteデータベース操作モジュール"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager


DATABASE_PATH = "sales_copilot.db"


@contextmanager
def get_db_connection():
    """データベース接続のコンテキストマネージャー"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """データベースの初期化"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                customer_company TEXT NOT NULL,
                conversation_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # インデックスを作成
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_id 
            ON conversations(customer_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON conversations(created_at)
        """)


def save_conversation(
    customer_id: str,
    customer_name: str,
    customer_company: str,
    conversation_type: str,
    content: str,
    metadata: Optional[dict] = None
) -> int:
    """会話履歴を保存"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations 
            (customer_id, customer_name, customer_company, conversation_type, content, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            customer_name,
            customer_company,
            conversation_type,
            content,
            json.dumps(metadata) if metadata else None
        ))
        return cursor.lastrowid


def get_conversations_by_customer(customer_id: str, limit: int = 50) -> List[dict]:
    """顧客IDで会話履歴を取得"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, customer_id, customer_name, customer_company,
                conversation_type, content, metadata, created_at
            FROM conversations
            WHERE customer_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (customer_id, limit))
        
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "customer_id": row["customer_id"],
                "customer_name": row["customer_name"],
                "customer_company": row["customer_company"],
                "conversation_type": row["conversation_type"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "created_at": row["created_at"]
            }
            for row in rows
        ]


def get_all_conversations(limit: int = 100) -> List[dict]:
    """すべての会話履歴を取得"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, customer_id, customer_name, customer_company,
                conversation_type, content, metadata, created_at
            FROM conversations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "customer_id": row["customer_id"],
                "customer_name": row["customer_name"],
                "customer_company": row["customer_company"],
                "conversation_type": row["conversation_type"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "created_at": row["created_at"]
            }
            for row in rows
        ]


def delete_conversation(conversation_id: int) -> bool:
    """会話履歴を削除"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        return cursor.rowcount > 0
