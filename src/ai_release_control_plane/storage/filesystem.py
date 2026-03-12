from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_release_control_plane.storage.base import StorageBackend


class FileSystemStorage(StorageBackend):
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _collection_dir(self, collection: str) -> Path:
        path = self.root_dir / collection
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _item_path(self, collection: str, item_id: str) -> Path:
        return self._collection_dir(collection) / f"{item_id}.json"

    def put(self, collection: str, item_id: str, payload: dict[str, Any]) -> None:
        with self._item_path(collection, item_id).open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True, default=str)

    def get(self, collection: str, item_id: str) -> dict[str, Any] | None:
        path = self._item_path(collection, item_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def list(self, collection: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self._collection_dir(collection).glob("*.json")):
            with path.open("r", encoding="utf-8") as f:
                items.append(json.load(f))
        return items

    def delete(self, collection: str, item_id: str) -> None:
        path = self._item_path(collection, item_id)
        if path.exists():
            path.unlink()
