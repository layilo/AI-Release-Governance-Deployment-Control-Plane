from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    @abstractmethod
    def put(self, collection: str, item_id: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, collection: str, item_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def list(self, collection: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, collection: str, item_id: str) -> None:
        raise NotImplementedError
