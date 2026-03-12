from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml


class ExposureController(ABC):
    @abstractmethod
    def set_exposure(self, environment: str, bundle_id: str, percent: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def disable(self, environment: str, bundle_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def assign(self, key: str, percent: int) -> bool:
        raise NotImplementedError


class MockExposureController(ExposureController):
    def __init__(self) -> None:
        self.state: dict[tuple[str, str], int] = {}

    def set_exposure(self, environment: str, bundle_id: str, percent: int) -> None:
        self.state[(environment, bundle_id)] = max(0, min(100, percent))

    def disable(self, environment: str, bundle_id: str) -> None:
        self.state[(environment, bundle_id)] = 0

    def assign(self, key: str, percent: int) -> bool:
        h = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16) % 100
        return h < percent


class FeatureFlagControllerStub(MockExposureController):
    pass


class ConfigFileExposureController(ExposureController):
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        if not self.config_path.exists():
            self._write({"exposures": {}})

    def _read(self) -> dict[str, Any]:
        with self.config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _write(self, data: dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=True)

    def set_exposure(self, environment: str, bundle_id: str, percent: int) -> None:
        data = self._read()
        exposures = data.setdefault("exposures", {})
        exposures[f"{environment}:{bundle_id}"] = max(0, min(100, percent))
        self._write(data)

    def disable(self, environment: str, bundle_id: str) -> None:
        self.set_exposure(environment, bundle_id, 0)

    def assign(self, key: str, percent: int) -> bool:
        h = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16) % 100
        return h < percent
