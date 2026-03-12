from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ai_release_control_plane.storage.base import StorageBackend


class SQLiteStorage(StorageBackend):
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    collection TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY(collection, item_id)
                )
                """
            )
            conn.commit()

    def put(self, collection: str, item_id: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO kv(collection, item_id, payload) VALUES (?, ?, ?)",
                (collection, item_id, json.dumps(payload, default=str)),
            )
            conn.commit()

    def get(self, collection: str, item_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM kv WHERE collection = ? AND item_id = ?",
                (collection, item_id),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def list(self, collection: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM kv WHERE collection = ? ORDER BY item_id",
                (collection,),
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def delete(self, collection: str, item_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM kv WHERE collection = ? AND item_id = ?", (collection, item_id))
            conn.commit()
