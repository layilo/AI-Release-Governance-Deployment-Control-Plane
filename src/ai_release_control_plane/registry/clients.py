from __future__ import annotations

from abc import ABC, abstractmethod

from ai_release_control_plane.schemas.models import (
    PromptArtifact,
    SafetyPolicyArtifact,
    ServingConfigArtifact,
    WorkflowArtifact,
)


class PromptRegistryClient(ABC):
    @abstractmethod
    def resolve(self, artifact_id: str, version: str) -> PromptArtifact:
        raise NotImplementedError


class WorkflowRegistryClient(ABC):
    @abstractmethod
    def resolve(self, artifact_id: str, version: str) -> WorkflowArtifact:
        raise NotImplementedError


class ServingConfigClient(ABC):
    @abstractmethod
    def resolve(self, artifact_id: str, version: str) -> ServingConfigArtifact:
        raise NotImplementedError


class SafetyPolicyClient(ABC):
    @abstractmethod
    def resolve(self, artifact_id: str, version: str) -> SafetyPolicyArtifact:
        raise NotImplementedError


class InMemoryArtifactRegistry(
    PromptRegistryClient,
    WorkflowRegistryClient,
    ServingConfigClient,
    SafetyPolicyClient,
):
    def __init__(
        self,
        prompts: dict[str, PromptArtifact] | None = None,
        workflows: dict[str, WorkflowArtifact] | None = None,
        serving_configs: dict[str, ServingConfigArtifact] | None = None,
        safety_policies: dict[str, SafetyPolicyArtifact] | None = None,
    ) -> None:
        self.prompts = prompts or {}
        self.workflows = workflows or {}
        self.serving_configs = serving_configs or {}
        self.safety_policies = safety_policies or {}

    @staticmethod
    def _key(artifact_id: str, version: str) -> str:
        return f"{artifact_id}:{version}"

    def resolve(self, artifact_id: str, version: str):  # type: ignore[override]
        key = self._key(artifact_id, version)
        for store in (self.prompts, self.workflows, self.serving_configs, self.safety_policies):
            if key in store:
                return store[key]
        msg = f"Artifact not found: {key}"
        raise KeyError(msg)
