from __future__ import annotations

from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from ai_release_control_plane.storage.base import StorageBackend

T = TypeVar("T", bound=BaseModel)


class ModelRepository:
    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage

    def save(self, collection: str, model: BaseModel, model_id: str | None = None) -> str:
        item_id = model_id or getattr(model, "bundle_id", None) or getattr(model, "candidate_id", None)
        item_id = item_id or getattr(model, "record_id", None) or str(uuid4())
        self.storage.put(collection, item_id, model.model_dump(mode="json"))
        return item_id

    def get(self, collection: str, item_id: str, model_cls: type[T]) -> T | None:
        payload = self.storage.get(collection, item_id)
        if payload is None:
            return None
        return model_cls.model_validate(payload)

    def list(self, collection: str, model_cls: type[T]) -> list[T]:
        return [model_cls.model_validate(x) for x in self.storage.list(collection)]
