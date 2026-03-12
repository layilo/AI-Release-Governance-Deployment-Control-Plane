from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskClassification(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class PromotionAction(str, Enum):
    promote = "promote"
    hold = "hold"
    rollback = "rollback"


class RolloutStepType(str, Enum):
    shadow = "shadow"
    canary = "canary"
    progressive = "progressive"
    full = "full"
    pause = "pause"
    approval = "approval"


class RolloutStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    aborted = "aborted"
    rolled_back = "rolled_back"


class ReleaseEnvironment(str, Enum):
    dev = "dev"
    qa = "qa"
    staging = "staging"
    prod = "prod"


class ArtifactRef(BaseModel):
    artifact_id: str
    version: str
    alias: str | None = None


class PromptArtifact(BaseModel):
    artifact_id: str
    version: str
    text: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowArtifact(BaseModel):
    artifact_id: str
    version: str
    definition: dict[str, Any]
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServingConfigArtifact(BaseModel):
    artifact_id: str
    version: str
    model: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class SafetyPolicyArtifact(BaseModel):
    artifact_id: str
    version: str
    rules: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ReleaseBundle(BaseModel):
    bundle_id: str
    version: str
    prompt_refs: list[ArtifactRef] = Field(default_factory=list)
    workflow_refs: list[ArtifactRef] = Field(default_factory=list)
    serving_config_refs: list[ArtifactRef] = Field(default_factory=list)
    safety_policy_refs: list[ArtifactRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    release_notes: str = ""
    owner_team: str
    created_at: datetime
    source_environment: ReleaseEnvironment
    target_environment: ReleaseEnvironment
    risk_classification: RiskClassification = RiskClassification.low
    approval_requirements: list[str] = Field(default_factory=list)
    traceability: dict[str, Any] = Field(default_factory=dict)


class ReleaseCandidate(BaseModel):
    candidate_id: str
    bundle_id: str
    created_by: str
    created_at: datetime
    immutable_digest: str
    status: str = "registered"
    notes: str = ""


class ReleasePolicy(BaseModel):
    policy_id: str
    name: str
    environment: ReleaseEnvironment
    hard_fail_rules: dict[str, float] = Field(default_factory=dict)
    warn_only_rules: dict[str, float] = Field(default_factory=dict)
    environment_overrides: dict[str, dict[str, float]] = Field(default_factory=dict)
    approval_escalation: dict[str, list[str]] = Field(default_factory=dict)
    freeze_windows: list[str] = Field(default_factory=list)
    emergency_bypass_allowed: bool = False


class PromotionRequest(BaseModel):
    request_id: str
    candidate_id: str
    from_environment: ReleaseEnvironment
    to_environment: ReleaseEnvironment
    requested_by: str
    requested_at: datetime
    emergency_bypass: bool = False
    reason: str = ""


class PromotionDecision(BaseModel):
    request_id: str
    action: PromotionAction
    approved: bool
    rationale: str
    confidence: float
    risks: list[str] = Field(default_factory=list)
    decided_at: datetime


class RolloutStep(BaseModel):
    name: str
    step_type: RolloutStepType
    exposure_percent: int = 0
    duration_seconds: int = 30
    manual_approval_required: bool = False


class RolloutPlan(BaseModel):
    plan_id: str
    strategy: str
    steps: list[RolloutStep]


class OfflineGateResult(BaseModel):
    candidate_id: str
    passed: bool
    quality_score: float
    regression_delta: float
    structured_output_validity: float
    latency_ms: float
    token_usage: float
    cost_per_1k: float
    safety_score: float
    composite_score: float
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime


class OnlineGateResult(BaseModel):
    candidate_id: str
    passed: bool
    success_rate: float
    error_rate: float
    p95_latency_ms: float
    p99_latency_ms: float
    fallback_rate: float
    malformed_output_rate: float
    cost_spike_ratio: float
    custom_metrics: dict[str, float] = Field(default_factory=dict)
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime


class ShadowTestResult(BaseModel):
    candidate_id: str
    passed: bool
    requests_tested: int
    disagreement_rate: float
    schema_mismatch_rate: float
    latency_delta_ms: float
    cost_delta_ratio: float
    recommendation: PromotionAction
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CanaryAnalysisResult(BaseModel):
    candidate_id: str
    passed: bool
    step_name: str
    exposure_percent: int
    blast_radius_estimate: float
    confidence: float
    recommendation: PromotionAction
    reasons: list[str] = Field(default_factory=list)
    created_at: datetime


class ReleaseHealthSnapshot(BaseModel):
    candidate_id: str
    release_bundle_id: str
    quality: float
    reliability: float
    latency: float
    cost: float
    safety: float
    structured_output_correctness: float
    business_proxy: float
    overall_score: float
    confidence: float
    rollback_recommended: bool
    summary: str
    created_at: datetime


class RollbackDecision(BaseModel):
    candidate_id: str
    should_rollback: bool
    reason: str
    trigger: str
    target_bundle_id: str | None = None
    created_at: datetime


class AuditRecord(BaseModel):
    record_id: str
    actor: str
    action: str
    entity_type: str
    entity_id: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReleaseLineageRecord(BaseModel):
    record_id: str
    environment: ReleaseEnvironment
    previous_bundle_id: str | None
    new_bundle_id: str
    changed_artifacts: list[str] = Field(default_factory=list)
    changed_at: datetime
    changed_by: str


class ApprovalRecord(BaseModel):
    approval_id: str
    candidate_id: str
    approver: str
    approved: bool
    role: str
    reason: str = ""
    timestamp: datetime


class TelemetryEvent(BaseModel):
    trace_id: str
    run_id: str
    environment: ReleaseEnvironment
    release_bundle_id: str
    prompt_version: str
    workflow_version: str
    model_version: str
    token_usage: float
    latency_ms: float
    error: bool
    fallback: bool
    output_valid: bool
    cost_estimate: float
    release_phase: str
    exposure_cohort: str
    user_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

