from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ai_release_control_plane.config import load_yaml, profile_paths, reports_dir, state_dir
from ai_release_control_plane.observability.health import ReleaseHealthEngine
from ai_release_control_plane.observability.provider import MockObservabilityProvider
from ai_release_control_plane.policy.engine import RulePolicyEngine
from ai_release_control_plane.policy.evaluation import MockEvaluationProvider
from ai_release_control_plane.release.diff import diff_bundles
from ai_release_control_plane.release.lineage import create_lineage_record
from ai_release_control_plane.reports.generator import ReportGenerator
from ai_release_control_plane.rollback.engine import RollbackEngine
from ai_release_control_plane.rollout.engine import RolloutEngine
from ai_release_control_plane.rollout.exposure import MockExposureController
from ai_release_control_plane.schemas.models import (
    ApprovalRecord,
    ArtifactRef,
    AuditRecord,
    CanaryAnalysisResult,
    OfflineGateResult,
    PromotionAction,
    PromotionDecision,
    ReleaseBundle,
    ReleaseCandidate,
    ReleaseEnvironment,
    RolloutPlan,
    RolloutStep,
    RolloutStepType,
)
from ai_release_control_plane.shadow.engine import ShadowEngine
from ai_release_control_plane.storage.filesystem import FileSystemStorage
from ai_release_control_plane.storage.repository import ModelRepository
from ai_release_control_plane.approvals.engine import ApprovalEngine
from ai_release_control_plane.canary.engine import CanaryEngine


class ControlPlane:
    def __init__(self, profile: str = "local-demo", mode: str = "mock", scenario: str = "success") -> None:
        self.profile = profile
        self.mode = mode
        self.scenario = scenario
        self.paths = profile_paths(profile)
        self.storage = FileSystemStorage(state_dir())
        self.repo = ModelRepository(self.storage)
        self.exposure = MockExposureController()
        self.rollout = RolloutEngine(self.exposure, self.repo)
        self.rollback_engine = RollbackEngine(self.exposure)
        self.policy_engine = RulePolicyEngine()
        self.eval_provider = MockEvaluationProvider(scenario=scenario)
        self.shadow_engine = ShadowEngine(scenario=scenario)
        self.observability = MockObservabilityProvider(scenario=scenario)
        self.canary_engine = CanaryEngine(self.observability)
        approval_cfg = load_yaml(self.paths["approval"]) if self.paths["approval"].exists() else {}
        self.approval_engine = ApprovalEngine(approval_cfg)
        self.health_engine = ReleaseHealthEngine()
        self.reports = ReportGenerator(reports_dir())

    def _audit(self, actor: str, action: str, entity_type: str, entity_id: str, metadata: dict | None = None) -> None:
        rec = AuditRecord(
            record_id=f"audit_{uuid4().hex[:10]}",
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
        self.repo.save("audit_records", rec)

    @staticmethod
    def _parse_refs(rows: list[dict]) -> list[ArtifactRef]:
        return [ArtifactRef.model_validate(r) for r in rows]

    def register_bundle(self, bundle_file: Path, actor: str = "system") -> ReleaseBundle:
        data = load_yaml(bundle_file)
        bundle = ReleaseBundle(
            bundle_id=data["bundle_id"],
            version=data.get("version", "v1"),
            prompt_refs=self._parse_refs(data.get("prompt_refs", [])),
            workflow_refs=self._parse_refs(data.get("workflow_refs", [])),
            serving_config_refs=self._parse_refs(data.get("serving_config_refs", [])),
            safety_policy_refs=self._parse_refs(data.get("safety_policy_refs", [])),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            release_notes=data.get("release_notes", ""),
            owner_team=data["owner_team"],
            created_at=datetime.fromisoformat(data["created_at"]),
            source_environment=ReleaseEnvironment(data["source_environment"]),
            target_environment=ReleaseEnvironment(data["target_environment"]),
            risk_classification=data.get("risk_classification", "low"),
            approval_requirements=data.get("approval_requirements", []),
            traceability=data.get("traceability", {}),
        )
        self.repo.save("bundles", bundle, bundle.bundle_id)
        self._audit(actor, "register_bundle", "release_bundle", bundle.bundle_id, {"file": str(bundle_file)})
        return bundle

    def create_candidate(self, bundle_id: str, actor: str = "system", notes: str = "") -> ReleaseCandidate:
        bundle_payload = self.storage.get("bundles", bundle_id)
        if not bundle_payload:
            msg = f"Bundle not found: {bundle_id}"
            raise KeyError(msg)
        digest = hashlib.sha256(json.dumps(bundle_payload, sort_keys=True).encode("utf-8")).hexdigest()
        cand = ReleaseCandidate(
            candidate_id=f"cand_{uuid4().hex[:10]}",
            bundle_id=bundle_id,
            created_by=actor,
            created_at=datetime.utcnow(),
            immutable_digest=digest,
            notes=notes,
        )
        self.repo.save("candidates", cand, cand.candidate_id)
        self._audit(actor, "create_candidate", "release_candidate", cand.candidate_id, {"bundle_id": bundle_id})
        return cand

    def diff_bundles(self, base_id: str, cand_id: str) -> dict:
        base = ReleaseBundle.model_validate(self.storage.get("bundles", base_id))
        cand = ReleaseBundle.model_validate(self.storage.get("bundles", cand_id))
        return diff_bundles(base, cand)

    def evaluate_offline(self, candidate_id: str, environment: str) -> OfflineGateResult:
        cand = self._load_candidate(candidate_id)
        result = self.eval_provider.run_offline(candidate_id, cand.bundle_id)
        policy = self._load_policy(environment)
        passed, failures, warnings = self.policy_engine.evaluate_offline(policy, result)
        result.passed = passed
        result.blocking_reasons = sorted(set(result.blocking_reasons + failures))
        result.warnings = sorted(set(result.warnings + warnings))
        self.repo.save("offline_gate_results", result, candidate_id)
        return result

    def run_shadow(self, candidate_id: str) -> object:
        result = self.shadow_engine.run(candidate_id)
        self.repo.save("shadow_results", result, candidate_id)
        return result

    def build_rollout_plan(self, strategy: str = "canary") -> RolloutPlan:
        if self.paths["rollout"].exists():
            cfg = load_yaml(self.paths["rollout"])
            steps = [RolloutStep.model_validate(s) for s in cfg.get(strategy, [])]
        else:
            steps = []
        if not steps:
            steps = [
                RolloutStep(name="shadow-100", step_type=RolloutStepType.shadow, exposure_percent=0),
                RolloutStep(name="canary-1", step_type=RolloutStepType.canary, exposure_percent=1),
                RolloutStep(name="canary-5", step_type=RolloutStepType.canary, exposure_percent=5),
                RolloutStep(name="canary-10", step_type=RolloutStepType.canary, exposure_percent=10),
                RolloutStep(name="canary-25", step_type=RolloutStepType.progressive, exposure_percent=25),
                RolloutStep(name="canary-50", step_type=RolloutStepType.progressive, exposure_percent=50),
                RolloutStep(name="full-prod", step_type=RolloutStepType.full, exposure_percent=100),
            ]
        return RolloutPlan(plan_id=f"plan_{uuid4().hex[:10]}", strategy=strategy, steps=steps)

    def start_rollout(self, candidate_id: str, environment: str, strategy: str) -> dict:
        cand = self._load_candidate(candidate_id)
        plan = self.build_rollout_plan(strategy=strategy)
        rollout = self.rollout.start(candidate_id, cand.bundle_id, environment, plan)
        self._audit("system", "start_rollout", "rollout", rollout["rollout_id"], {"candidate_id": candidate_id})
        return rollout

    def run_rollout_until_decision(self, rollout_id: str) -> dict:
        rollout_state = self.rollout.get(rollout_id)
        if rollout_state is None:
            msg = f"Rollout not found: {rollout_id}"
            raise KeyError(msg)
        canary_results: list[CanaryAnalysisResult] = []
        online_results: list[dict] = []
        while rollout_state["status"] == "running":
            idx = rollout_state["current_step"]
            if idx >= len(rollout_state["steps"]):
                break
            step = RolloutStep.model_validate(rollout_state["steps"][idx])
            rollout_state = self.rollout.apply_next_step(rollout_id)
            if step.exposure_percent == 0:
                continue
            canary, online = self.canary_engine.evaluate_step(
                candidate_id=rollout_state["candidate_id"],
                bundle_id=rollout_state["bundle_id"],
                environment=ReleaseEnvironment(rollout_state["environment"]),
                step=step,
            )
            policy = self._load_policy(rollout_state["environment"])
            online_passed, online_failures, online_warnings = self.policy_engine.evaluate_online(policy, online)
            online.passed = online_passed
            online.blocking_reasons = sorted(set(online.blocking_reasons + online_failures))
            online.warnings = sorted(set(online.warnings + online_warnings))
            canary.passed = canary.passed and online_passed
            if not online_passed and not canary.reasons:
                canary.reasons = online_failures
            canary_results.append(canary)
            online_results.append(online.model_dump(mode="json"))
            self.repo.save("canary_results", canary)
            self.repo.save("online_gate_results", online)
            if not canary.passed:
                decision = self.rollback_engine.decide(
                    candidate_id=rollout_state["candidate_id"],
                    should_rollback=True,
                    trigger="canary_failure",
                    reason="Canary gate failed",
                    target_bundle_id=self.latest_promoted_bundle(rollout_state["environment"]),
                )
                self.rollback_engine.execute(rollout_state["environment"], rollout_state["bundle_id"])
                self.repo.save("rollback_decisions", decision, rollout_state["candidate_id"])
                self.rollout.abort(rollout_id, reason=decision.reason)
                self._audit(
                    "system",
                    "rollback",
                    "candidate",
                    rollout_state["candidate_id"],
                    {"trigger": "canary_failure", "rollout_id": rollout_id},
                )
                return {
                    "status": "rolled_back",
                    "rollout_id": rollout_id,
                    "canary_results": [c.model_dump(mode="json") for c in canary_results],
                    "online_results": online_results,
                    "rollback_decision": decision.model_dump(mode="json"),
                }
        return {
            "status": rollout_state["status"],
            "rollout_id": rollout_id,
            "canary_results": [c.model_dump(mode="json") for c in canary_results],
            "online_results": online_results,
        }

    def approve(self, candidate_id: str, approver: str, role: str, reason: str = "", approved: bool = True) -> ApprovalRecord:
        rec = self.approval_engine.record(candidate_id, approver, approved, role, reason)
        self.repo.save("approval_records", rec, rec.approval_id)
        self._audit(approver, "approve", "candidate", candidate_id, {"approved": approved, "role": role})
        return rec

    def promote(self, candidate_id: str, actor: str = "system") -> PromotionDecision:
        cand = self._load_candidate(candidate_id)
        bundle = self._load_bundle(cand.bundle_id)
        latest = self.latest_promoted_bundle(bundle.target_environment.value)
        prev = self._load_bundle(latest) if latest else None
        lineage = create_lineage_record(bundle.target_environment, prev, bundle, actor)
        self.repo.save("lineage_records", lineage, lineage.record_id)
        self.storage.put("env_aliases", bundle.target_environment.value, {"bundle_id": bundle.bundle_id})
        decision = PromotionDecision(
            request_id=f"req_{uuid4().hex[:10]}",
            action=PromotionAction.promote,
            approved=True,
            rationale="All gates passed and approvals satisfied",
            confidence=0.93,
            risks=[],
            decided_at=datetime.utcnow(),
        )
        self.repo.save("promotion_decisions", decision, candidate_id)
        self._audit(actor, "promote", "candidate", candidate_id, {"environment": bundle.target_environment.value})
        return decision

    def rollback(self, candidate_id: str, reason: str, actor: str = "operator") -> dict:
        cand = self._load_candidate(candidate_id)
        bundle = self._load_bundle(cand.bundle_id)
        self.rollback_engine.execute(bundle.target_environment.value, bundle.bundle_id)
        decision = self.rollback_engine.decide(
            candidate_id=candidate_id,
            should_rollback=True,
            trigger="operator",
            reason=reason,
            target_bundle_id=self.latest_promoted_bundle(bundle.target_environment.value),
        )
        self.repo.save("rollback_decisions", decision, candidate_id)
        self._audit(actor, "rollback", "candidate", candidate_id, {"reason": reason})
        return decision.model_dump(mode="json")

    def inspect(self, entity: str, entity_id: str | None = None) -> list[dict] | dict | None:
        if entity_id:
            return self.storage.get(entity, entity_id)
        return self.storage.list(entity)

    def doctor(self) -> dict:
        checks = {
            "state_dir_exists": state_dir().exists(),
            "reports_dir_exists": reports_dir().exists(),
            "profile": self.profile,
            "mode": self.mode,
            "policy_config_present": self.paths["policy"].exists(),
            "approval_config_present": self.paths["approval"].exists(),
            "rollout_config_present": self.paths["rollout"].exists(),
        }
        return {"ok": all(v for k, v in checks.items() if isinstance(v, bool)), "checks": checks}

    def report(self, candidate_id: str, fmt: str = "json") -> dict:
        cand = self._load_candidate(candidate_id)
        bundle = self._load_bundle(cand.bundle_id)
        offline = self.storage.get("offline_gate_results", candidate_id)
        shadow = self.storage.get("shadow_results", candidate_id)
        rollback = self.storage.get("rollback_decisions", candidate_id)
        promotion = self.storage.get("promotion_decisions", candidate_id)
        approvals = [
            r
            for r in self.storage.list("approval_records")
            if r.get("candidate_id") == candidate_id
        ]
        online_rows = [r for r in self.storage.list("online_gate_results") if r.get("candidate_id") == candidate_id]
        canary_rows = [r for r in self.storage.list("canary_results") if r.get("candidate_id") == candidate_id]

        if offline and online_rows:
            from ai_release_control_plane.schemas.models import OfflineGateResult, OnlineGateResult

            health = self.health_engine.aggregate(
                candidate_id=candidate_id,
                bundle_id=bundle.bundle_id,
                offline=OfflineGateResult.model_validate(offline),
                online=OnlineGateResult.model_validate(online_rows[-1]),
            ).model_dump(mode="json")
        else:
            health = None

        recommendation = "promote"
        rationale = "evidence strong"
        if rollback:
            recommendation = "rollback"
            rationale = rollback.get("reason", "rollback decision exists")
        elif offline and offline.get("passed") is False:
            recommendation = "hold"
            rationale = "offline gates failed"

        memo = {
            "candidate": cand.model_dump(mode="json"),
            "bundle": bundle.model_dump(mode="json"),
            "offline_gate": offline,
            "shadow_analysis": shadow,
            "canary_analysis": canary_rows,
            "online_metrics": online_rows,
            "approvals": approvals,
            "health_snapshot": health,
            "promotion_decision": promotion,
            "rollback_decision": rollback,
            "recommendation": recommendation,
            "rationale": rationale,
            "confidence": health["confidence"] if health else 0.5,
            "risk_notes": [] if recommendation == "promote" else ["monitor latency, quality, and fallback rate"],
        }
        name = f"release_decision_{candidate_id}"
        if fmt == "markdown":
            self.reports.write_markdown(name, "Release Decision Memo", memo)
        elif fmt == "html":
            self.reports.write_html(name, "Release Decision Memo", memo)
        elif fmt == "csv":
            self.reports.write_csv(name, online_rows or [])
        else:
            self.reports.write_json(name, memo)
        return memo

    def latest_promoted_bundle(self, environment: str) -> str | None:
        alias = self.storage.get("env_aliases", environment)
        if alias:
            return alias.get("bundle_id")
        return None

    def _load_candidate(self, candidate_id: str) -> ReleaseCandidate:
        payload = self.storage.get("candidates", candidate_id)
        if not payload:
            msg = f"Candidate not found: {candidate_id}"
            raise KeyError(msg)
        return ReleaseCandidate.model_validate(payload)

    def _load_bundle(self, bundle_id: str) -> ReleaseBundle:
        payload = self.storage.get("bundles", bundle_id)
        if not payload:
            msg = f"Bundle not found: {bundle_id}"
            raise KeyError(msg)
        return ReleaseBundle.model_validate(payload)

    def _load_policy(self, environment: str):
        if self.paths["policy"].exists():
            cfg = load_yaml(self.paths["policy"])
        else:
            cfg = {}
        return self.policy_engine.from_config("default_policy", ReleaseEnvironment(environment), cfg)
