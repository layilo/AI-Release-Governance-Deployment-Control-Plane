from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ai_release_control_plane.schemas.models import (
    OfflineGateResult,
    OnlineGateResult,
    ReleaseEnvironment,
    ReleasePolicy,
)


class PolicyDecisionEngine(ABC):
    @abstractmethod
    def evaluate_offline(
        self, policy: ReleasePolicy, result: OfflineGateResult
    ) -> tuple[bool, list[str], list[str]]:
        raise NotImplementedError

    @abstractmethod
    def evaluate_online(
        self, policy: ReleasePolicy, result: OnlineGateResult
    ) -> tuple[bool, list[str], list[str]]:
        raise NotImplementedError


class RulePolicyEngine(PolicyDecisionEngine):
    OFFLINE_KEY_MAP = {
        "min_quality_score": ("quality_score", lambda v, t: v >= t),
        "min_structured_output_validity": ("structured_output_validity", lambda v, t: v >= t),
        "max_latency_ms": ("latency_ms", lambda v, t: v <= t),
        "max_token_usage": ("token_usage", lambda v, t: v <= t),
        "max_cost_per_1k": ("cost_per_1k", lambda v, t: v <= t),
        "min_safety_score": ("safety_score", lambda v, t: v >= t),
        "max_regression_delta": ("regression_delta", lambda v, t: v >= -abs(t)),
    }

    ONLINE_KEY_MAP = {
        "min_success_rate": ("success_rate", lambda v, t: v >= t),
        "max_error_rate": ("error_rate", lambda v, t: v <= t),
        "max_p95_latency_ms": ("p95_latency_ms", lambda v, t: v <= t),
        "max_p99_latency_ms": ("p99_latency_ms", lambda v, t: v <= t),
        "max_fallback_rate": ("fallback_rate", lambda v, t: v <= t),
        "max_malformed_output_rate": ("malformed_output_rate", lambda v, t: v <= t),
        "max_cost_spike_ratio": ("cost_spike_ratio", lambda v, t: v <= t),
    }

    @staticmethod
    def from_config(policy_id: str, env: ReleaseEnvironment, data: dict) -> ReleasePolicy:
        return ReleasePolicy(
            policy_id=policy_id,
            name=data.get("name", policy_id),
            environment=env,
            hard_fail_rules=data.get("hard_fail_rules", {}),
            warn_only_rules=data.get("warn_only_rules", {}),
            environment_overrides=data.get("environment_overrides", {}),
            approval_escalation=data.get("approval_escalation", {}),
            freeze_windows=data.get("freeze_windows", []),
            emergency_bypass_allowed=bool(data.get("emergency_bypass_allowed", False)),
        )

    def _check(self, rules: dict[str, float], result: object, key_map: dict[str, tuple[str, object]]):
        failures: list[str] = []
        warnings: list[str] = []
        for rule_key, threshold in rules.items():
            if rule_key not in key_map:
                warnings.append(f"unknown_rule:{rule_key}")
                continue
            metric_attr, comparator = key_map[rule_key]
            value = getattr(result, metric_attr)
            if not comparator(value, threshold):
                failures.append(f"{rule_key} failed ({value} vs {threshold})")
        return failures, warnings

    def evaluate_offline(
        self, policy: ReleasePolicy, result: OfflineGateResult
    ) -> tuple[bool, list[str], list[str]]:
        failures, warnings = self._check(policy.hard_fail_rules, result, self.OFFLINE_KEY_MAP)
        warn_failures, warn_warnings = self._check(policy.warn_only_rules, result, self.OFFLINE_KEY_MAP)
        warnings += [f"warn:{w}" for w in warn_failures]
        warnings += warn_warnings
        passed = len(failures) == 0 and result.passed
        return passed, failures + result.blocking_reasons, warnings + result.warnings

    def evaluate_online(
        self, policy: ReleasePolicy, result: OnlineGateResult
    ) -> tuple[bool, list[str], list[str]]:
        failures, warnings = self._check(policy.hard_fail_rules, result, self.ONLINE_KEY_MAP)
        warn_failures, warn_warnings = self._check(policy.warn_only_rules, result, self.ONLINE_KEY_MAP)
        warnings += [f"warn:{w}" for w in warn_failures]
        warnings += warn_warnings
        passed = len(failures) == 0 and result.passed
        return passed, failures + result.blocking_reasons, warnings + result.warnings

    @staticmethod
    def in_freeze_window(policy: ReleasePolicy, current_iso_ts: str | None = None) -> bool:
        if not policy.freeze_windows:
            return False
        ts = current_iso_ts or datetime.utcnow().isoformat()
        return any(window in ts for window in policy.freeze_windows)
