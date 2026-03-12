from __future__ import annotations

import json
import random
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ai_release_control_plane.schemas.models import OnlineGateResult, ReleaseEnvironment, TelemetryEvent


class ObservabilityProvider(ABC):
    @abstractmethod
    def collect_online_gate(
        self, candidate_id: str, bundle_id: str, environment: ReleaseEnvironment, exposure_percent: int
    ) -> OnlineGateResult:
        raise NotImplementedError


class MockObservabilityProvider(ObservabilityProvider):
    def __init__(self, scenario: str = "success", seed: int = 42) -> None:
        self.scenario = scenario
        self.rng = random.Random(seed)

    def collect_online_gate(
        self, candidate_id: str, bundle_id: str, environment: ReleaseEnvironment, exposure_percent: int
    ) -> OnlineGateResult:
        factor = max(1, exposure_percent / 10)
        if self.scenario == "rollback_canary" and exposure_percent >= 10:
            success_rate = 0.86
            error_rate = 0.11
            p95 = 1600
            p99 = 2400
            fallback = 0.14
            malformed = 0.06
            cost_spike = 1.8
            passed = False
            reasons = ["canary_latency_spike", "error_rate_spike"]
        else:
            success_rate = 0.98 - self.rng.uniform(0.0, 0.01) * factor / 10
            error_rate = 0.01 + self.rng.uniform(0.0, 0.005) * factor / 10
            p95 = 700 + self.rng.uniform(0, 80) * factor / 10
            p99 = 980 + self.rng.uniform(0, 120) * factor / 10
            fallback = 0.02 + self.rng.uniform(0.0, 0.01) * factor / 10
            malformed = 0.01 + self.rng.uniform(0.0, 0.01) * factor / 10
            cost_spike = 1.05 + self.rng.uniform(0.0, 0.05) * factor / 10
            passed = True
            reasons = []
        return OnlineGateResult(
            candidate_id=candidate_id,
            passed=passed,
            success_rate=round(success_rate, 4),
            error_rate=round(error_rate, 4),
            p95_latency_ms=round(p95, 2),
            p99_latency_ms=round(p99, 2),
            fallback_rate=round(fallback, 4),
            malformed_output_rate=round(malformed, 4),
            cost_spike_ratio=round(cost_spike, 4),
            custom_metrics={"acceptance_rate": round(success_rate - 0.02, 4)},
            blocking_reasons=reasons,
            warnings=[],
            created_at=datetime.utcnow(),
        )

    def synthetic_event(
        self, bundle_id: str, environment: ReleaseEnvironment, release_phase: str
    ) -> TelemetryEvent:
        return TelemetryEvent(
            trace_id=uuid4().hex,
            run_id=uuid4().hex[:12],
            environment=environment,
            release_bundle_id=bundle_id,
            prompt_version="customer_support_prompt:v2",
            workflow_version="triage_workflow:v2",
            model_version="gpt-4.1-mini",
            token_usage=650,
            latency_ms=710,
            error=False,
            fallback=False,
            output_valid=True,
            cost_estimate=0.015,
            release_phase=release_phase,
            exposure_cohort="internal",
            user_metadata={"tenant": "sample", "segment": "beta"},
            created_at=datetime.utcnow(),
        )


class FileTelemetryProvider(ObservabilityProvider):
    def __init__(self, path: Path) -> None:
        self.path = path

    def collect_online_gate(
        self, candidate_id: str, bundle_id: str, environment: ReleaseEnvironment, exposure_percent: int
    ) -> OnlineGateResult:
        with self.path.open("r", encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        if not rows:
            msg = f"No telemetry rows found in {self.path}"
            raise ValueError(msg)
        success = [1 for r in rows if not r.get("error")]
        error = [1 for r in rows if r.get("error")]
        p95 = sorted(r.get("latency_ms", 0) for r in rows)[int(len(rows) * 0.95) - 1]
        p99 = sorted(r.get("latency_ms", 0) for r in rows)[int(len(rows) * 0.99) - 1]
        malformed = [1 for r in rows if not r.get("output_valid", True)]
        fallback = [1 for r in rows if r.get("fallback")]
        costs = [r.get("cost_estimate", 0.0) for r in rows]
        cost_spike = (sum(costs) / len(costs)) / 0.02 if costs else 1.0
        return OnlineGateResult(
            candidate_id=candidate_id,
            passed=True,
            success_rate=len(success) / len(rows),
            error_rate=len(error) / len(rows),
            p95_latency_ms=float(p95),
            p99_latency_ms=float(p99),
            fallback_rate=len(fallback) / len(rows),
            malformed_output_rate=len(malformed) / len(rows),
            cost_spike_ratio=cost_spike,
            custom_metrics={},
            blocking_reasons=[],
            warnings=[],
            created_at=datetime.utcnow(),
        )


class OTelExporterStub:
    def export(self, event: TelemetryEvent) -> None:
        _ = event
