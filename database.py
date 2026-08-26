from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "data" / "autoposter.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                hashtags TEXT DEFAULT '',
                platforms TEXT NOT NULL DEFAULT 'youtube',
                scheduled_at TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_error TEXT,
                platform_results TEXT DEFAULT '{}'
            )
            """
        )
        conn.commit()


def add_post(post: dict[str, Any]) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO posts
            (filename,title,description,hashtags,platforms,scheduled_at,status,created_at,updated_at,last_error,platform_results)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                post["filename"], post.get("title", ""), post.get("description", ""),
                post.get("hashtags", ""), ",".join(post.get("platforms", [])),
                post.get("scheduled_at"), post.get("status", "queued"),
                post["created_at"], post["updated_at"], post.get("last_error"),
                post.get("platform_results", "{}"),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_posts() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def update_post(post_id: int, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = fields.get("updated_at")
    fields = {k: v for k, v in fields.items() if v is not None}
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [post_id]
    with connect() as conn:
        conn.execute(f"UPDATE posts SET {assignments} WHERE id = ?", values)
        conn.commit()


def get_due_posts(now_iso: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM posts WHERE status = 'queued' AND scheduled_at IS NOT NULL AND scheduled_at <= ? ORDER BY id",
            (now_iso,),
        ).fetchall()
    return [dict(row) for row in rows]


init_db()
