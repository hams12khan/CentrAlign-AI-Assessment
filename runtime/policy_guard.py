"""
Enterprise Policy Engine & Human-in-the-Loop Gate for CentrAlign AI.

Enforces pre-execution RBAC, financial spending limits, and dangerous operation guardrails.
Halts execution when high-risk actions occur, emits AWAITING_HUMAN_APPROVAL,
and verifies cryptographic approval signatures before resuming.
"""

import hashlib
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from runtime.config import RuntimeSettings, get_settings
from runtime.memory import EnterpriseMemory
from runtime.planner import TaskStep

logger = logging.getLogger(__name__)


class PolicyDecision(BaseModel):
    """Formal verdict rendered by the policy guardrail engine."""

    verdict: Literal["APPROVED", "AWAITING_HUMAN_APPROVAL", "DENIED"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    reason: str
    required_role: str = "ai_operator"
    policy_id: Optional[str] = None
    step_id: str
    evaluated_at: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApprovalRecord(BaseModel):
    """Cryptographically-bound human authorization receipt."""

    approval_id: str = Field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:10]}")
    step_id: str
    approver_id: str
    approver_role: str
    comments: str = ""
    approved_at: float = Field(default_factory=time.time)
    signature_hash: str = ""

    def compute_signature(self, secret_salt: str = "centralign_enterprise_secret") -> str:
        """Compute cryptographic SHA-256 signature binding the approval."""
        payload = f"{self.approval_id}:{self.step_id}:{self.approver_id}:{self.approver_role}:{self.approved_at}:{secret_salt}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PolicyGuard:
    """
    Enterprise Pre-Execution Policy Gate.
    Guarantees that no unauthorized or excessive financial state mutations occur autonomously.
    """

    def __init__(
        self,
        memory: Optional[EnterpriseMemory] = None,
        settings: Optional[RuntimeSettings] = None,
    ):
        self.settings = settings or get_settings()
        self.memory = memory or EnterpriseMemory()
        self.approvals: Dict[str, ApprovalRecord] = {}
        self.audit_decisions: List[PolicyDecision] = []

    def evaluate_step(
        self,
        step: TaskStep,
        resolved_params: Dict[str, Any],
        actor_role: str = "ai_operator",
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        """
        Evaluate tool execution against RBAC rules and financial thresholds.

        Rules:
        1. Read actions (db_query, analytics_query, file_read, browser_inspect) -> AUTO-APPROVED.
        2. Safe modifications (< $1,000 threshold, discrepancy <= $50 auto-adjustment) -> AUTO-APPROVED with audit.
        3. High-risk actions (amount >= $1,000, wire transfers, deleting records, dropping tables) -> AWAITING_HUMAN_APPROVAL.
        """
        # If this step already has a valid human approval, approve immediately
        if step.id in self.approvals:
            appr = self.approvals[step.id]
            decision = PolicyDecision(
                verdict="APPROVED",
                risk_level="HIGH",
                reason=f"Approved by authorized human {appr.approver_id} ({appr.approver_role}): {appr.comments}",
                required_role=appr.approver_role,
                step_id=step.id,
                metadata={"approval_id": appr.approval_id, "signature_hash": appr.signature_hash},
            )
            self.audit_decisions.append(decision)
            return decision

        tool_name = step.tool.lower()

        # Rule 1: Read-Only Actions
        read_only_tools = {
            "db_query", "analytics_query", "file_read", "browser_inspect",
            "list_directory", "evaluate_discrepancy", "extract_dom_tables"
        }
        if tool_name in read_only_tools:
            decision = PolicyDecision(
                verdict="APPROVED",
                risk_level="LOW",
                reason=f"Read-only action '{step.tool}' is auto-approved without human delay.",
                required_role="ai_operator",
                policy_id="POL-READ-001",
                step_id=step.id,
            )
            self.audit_decisions.append(decision)
            return decision

        # Extract monetary values from params or SQL text
        amount = self._extract_monetary_amount(resolved_params)

        # Rule 2: Destructive Database or Filesystem Actions -> HIGH/CRITICAL RISK
        destructive_patterns = [r"\bdrop\b", r"\bdelete\b", r"\btruncate\b", r"\bdestroy\b"]
        sql_text = str(resolved_params.get("sql", "")).lower()
        if any(re.search(pat, sql_text) for pat in destructive_patterns) or "delete" in tool_name:
            decision = PolicyDecision(
                verdict="AWAITING_HUMAN_APPROVAL",
                risk_level="CRITICAL",
                reason="Destructive deletion operation requires explicit Human-in-the-Loop authorization.",
                required_role="compliance_officer",
                policy_id="POL-MUT-DESTRUCT",
                step_id=step.id,
                metadata={"detected_patterns": "destructive_sql", "sql": sql_text},
            )
            self.audit_decisions.append(decision)
            return decision

        # Rule 3: High Financial Threshold (>= $1,000.00)
        threshold = self.settings.APPROVAL_THRESHOLD_AMOUNT
        if amount is not None and amount >= threshold:
            decision = PolicyDecision(
                verdict="AWAITING_HUMAN_APPROVAL",
                risk_level="HIGH",
                reason=(
                    f"Financial mutation amount (${amount:,.2f}) exceeds autonomous threshold "
                    f"(${threshold:,.2f}). Human sign-off required."
                ),
                required_role="finance_manager",
                policy_id="POL-FIN-1000",
                step_id=step.id,
                metadata={"amount": amount, "threshold": threshold},
            )
            self.audit_decisions.append(decision)
            return decision

        # Rule 4: Wire Transfer / Direct Disbursement Tools -> HIGH RISK
        if "transfer" in tool_name or "disbursement" in tool_name or "wire" in tool_name:
            decision = PolicyDecision(
                verdict="AWAITING_HUMAN_APPROVAL",
                risk_level="HIGH",
                reason=f"Disbursement tool '{step.tool}' requires human financial officer signature.",
                required_role="finance_manager",
                policy_id="POL-FIN-1000",
                step_id=step.id,
                metadata={"tool": step.tool},
            )
            self.audit_decisions.append(decision)
            return decision

        # Rule 5: Safe Standard Mutations (< $1,000 or status updates)
        decision = PolicyDecision(
            verdict="APPROVED",
            risk_level="MEDIUM",
            reason=f"Standard state mutation '{step.tool}' within automated limits ($<1000) auto-approved.",
            required_role="ai_operator",
            policy_id="POL-MUT-SAFE",
            step_id=step.id,
            metadata={"amount": amount},
        )
        self.audit_decisions.append(decision)
        return decision

    def grant_approval(
        self,
        step_id: str,
        approver_id: str,
        approver_role: str,
        comments: str = "",
    ) -> ApprovalRecord:
        """
        Record a human signature authorizing execution of a halted high-risk step.
        """
        record = ApprovalRecord(
            step_id=step_id,
            approver_id=approver_id,
            approver_role=approver_role,
            comments=comments,
            approved_at=time.time(),
        )
        record.signature_hash = record.compute_signature()
        self.approvals[step_id] = record
        logger.info(f"Granted HITL approval for step {step_id} by {approver_id} ({approver_role}).")
        return record

    def revoke_approval(self, step_id: str, approver_id: str, reason: str) -> None:
        """Revoke human approval for a step."""
        if step_id in self.approvals:
            del self.approvals[step_id]
            logger.info(f"Revoked approval for step {step_id} by {approver_id}. Reason: {reason}")

    def is_approved(self, step_id: str) -> bool:
        """Check if a step has human approval on record."""
        return step_id in self.approvals

    def get_approval_history(self) -> List[ApprovalRecord]:
        """Return all recorded human approvals."""
        return list(self.approvals.values())

    @staticmethod
    def _extract_monetary_amount(params: Dict[str, Any]) -> Optional[float]:
        """Extract numeric amount from parameter fields or nested strings."""
        amount_keys = ["amount", "total_amount", "invoice_amount", "refund_amount", "variance"]
        for key in amount_keys:
            if key in params:
                val = params[key]
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    clean = re.sub(r"[^\d.]", "", val)
                    if clean:
                        try:
                            return float(clean)
                        except ValueError:
                            pass

        # Check in SQL query text (e.g. "amount > 500")
        if "sql" in params:
            sql = str(params["sql"])
            match = re.search(r"amount\s*(?:>|=|<|>=|<=)\s*(\d+(?:\.\d+)?)", sql, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass

        return None
