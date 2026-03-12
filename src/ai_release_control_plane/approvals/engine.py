from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ai_release_control_plane.schemas.models import ApprovalRecord, RiskClassification


class ApprovalEngine:
    def __init__(self, rules: dict) -> None:
        self.rules = rules

    def required_roles(self, risk: RiskClassification | str, environment: str) -> list[str]:
        by_risk = self.rules.get("required_by_risk", {})
        risk_key = risk.value if isinstance(risk, RiskClassification) else str(risk)
        roles = list(by_risk.get(risk_key, []))
        if environment == "prod":
            roles.extend(self.rules.get("additional_prod_roles", []))
        return sorted(set(roles))

    def auto_approved(self, risk: RiskClassification | str, environment: str, mode: str) -> bool:
        risk_enum = risk if isinstance(risk, RiskClassification) else RiskClassification(str(risk))
        if mode == "auto":
            return True
        if risk_enum == RiskClassification.low and environment != "prod":
            return True
        return False

    def record(self, candidate_id: str, approver: str, approved: bool, role: str, reason: str) -> ApprovalRecord:
        return ApprovalRecord(
            approval_id=f"apr_{uuid4().hex[:10]}",
            candidate_id=candidate_id,
            approver=approver,
            approved=approved,
            role=role,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
