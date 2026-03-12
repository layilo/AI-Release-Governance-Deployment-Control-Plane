from __future__ import annotations

from datetime import datetime

from ai_release_control_plane.schemas.models import (
    OfflineGateResult,
    OnlineGateResult,
    ReleaseHealthSnapshot,
)


class ReleaseHealthEngine:
    def aggregate(
        self,
        candidate_id: str,
        bundle_id: str,
        offline: OfflineGateResult,
        online: OnlineGateResult,
    ) -> ReleaseHealthSnapshot:
        quality = offline.quality_score
        reliability = online.success_rate
        latency = max(0.0, 1.0 - (online.p95_latency_ms / 3000))
        cost = max(0.0, 1.0 - ((online.cost_spike_ratio - 1.0) / 1.0))
        safety = offline.safety_score
        structure = offline.structured_output_validity
        business = online.custom_metrics.get("acceptance_rate", online.success_rate - 0.03)
        overall = (quality + reliability + latency + cost + safety + structure + business) / 7
        confidence = min(0.99, overall + 0.03)
        rollback = overall < 0.75 or online.error_rate > 0.08
        summary = "healthy" if not rollback else "degraded"
        return ReleaseHealthSnapshot(
            candidate_id=candidate_id,
            release_bundle_id=bundle_id,
            quality=round(quality, 4),
            reliability=round(reliability, 4),
            latency=round(latency, 4),
            cost=round(cost, 4),
            safety=round(safety, 4),
            structured_output_correctness=round(structure, 4),
            business_proxy=round(business, 4),
            overall_score=round(overall, 4),
            confidence=round(confidence, 4),
            rollback_recommended=rollback,
            summary=summary,
            created_at=datetime.utcnow(),
        )
