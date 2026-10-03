import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    username TEXT,
                    service TEXT NOT NULL,
                    name TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    comment TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at)"
            )

    def add_lead(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        service: str,
        name: str,
        contact: str,
        comment: str,
    ) -> dict[str, Any]:
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO leads (
                    telegram_user_id, username, service, name,
                    contact, comment, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_user_id,
                    username,
                    service,
                    name,
                    contact,
                    comment,
                    created_at,
                ),
            )
            lead_id = cursor.lastrowid

        return {
            "id": lead_id,
            "telegram_user_id": telegram_user_id,
            "username": username,
            "service": service,
            "name": name,
            "contact": contact,
            "comment": comment,
            "created_at": created_at,
        }

    def count_leads(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM leads").fetchone()
        return int(row["count"])

    def count_leads_today(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM leads
                WHERE date(created_at, 'localtime') = date('now', 'localtime')
                """
            ).fetchone()
        return int(row["count"])

    def get_recent_leads(self, limit: int = 10) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM leads ORDER BY id DESC LIMIT ?", (safe_limit,)
            ).fetchall()
        return [dict(row) for row in rows]
