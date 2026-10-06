"""
Persistent Enterprise SOP Memory & Policy Store for CentrAlign AI.

Provides persistent organizational context:
- Standard Operating Procedures (SOPs)
- Corporate governance policies & RBAC rules
- Execution state checkpoints for suspend/resume workflows
- Zero-dependency local semantic search engine (BM25/TF-IDF vector ranking)
"""

import json
import math
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from runtime.config import RuntimeSettings, get_settings


class SOPDocument(BaseModel):
    """Enterprise Standard Operating Procedure (SOP) specification."""

    id: str = Field(..., description="Unique SOP code, e.g. SOP-FIN-001")
    title: str = Field(..., description="Descriptive procedure title")
    category: str = Field(..., description="Business domain (Finance, Security, Compliance)")
    content: str = Field(..., description="Full text instructions, thresholds, and guardrails")
    tags: List[str] = Field(default_factory=list, description="Keywords for retrieval")
    rules: Dict[str, Any] = Field(default_factory=dict, description="Structured numerical thresholds and triggers")
    created_at: float = Field(default_factory=time.time)


class PolicyRule(BaseModel):
    """Enforceable corporate governance rule."""

    rule_id: str = Field(..., description="Unique rule code, e.g. POL-FIN-1000")
    name: str = Field(..., description="Human-readable rule name")
    action_pattern: str = Field(..., description="Regex or pattern for matching tool actions")
    condition_type: str = Field(..., description="Condition category (THRESHOLD, ROLE, ACTION_TYPE)")
    threshold: Optional[float] = Field(None, description="Numeric trigger value in USD")
    risk_level: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    requires_human_approval: bool = Field(default=False, description="Whether execution triggers HITL halt")
    description: str = Field(..., description="Detailed explanation of the governance requirement")


class EnterpriseMemory:
    """
    Persistent SQLite-backed organizational knowledge and policy store.
    Features embedded vector-like term frequency scoring for offline semantic RAG.
    """

    def __init__(self, db_path: Optional[Path] = None, settings: Optional[RuntimeSettings] = None):
        self.settings = settings or get_settings()
        self.db_path = db_path or (self.settings.DATABASE_DIR / "enterprise_memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
        self._seed_default_data_if_empty()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS enterprise_sops (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    rules_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS enterprise_policies (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    action_pattern TEXT NOT NULL,
                    condition_type TEXT NOT NULL,
                    threshold REAL,
                    risk_level TEXT NOT NULL,
                    requires_human_approval INTEGER NOT NULL,
                    description TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_checkpoints (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()

    def _seed_default_data_if_empty(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM enterprise_sops")
            count = cursor.fetchone()[0]
            if count > 0:
                return

        # Seed initial SOPs
        sops = [
            SOPDocument(
                id="SOP-FIN-001",
                title="Vendor Invoice Discrepancy & PO Reconciliation SOP",
                category="Finance",
                content=(
                    "When reconciling an incoming vendor invoice against an approved purchase order (PO):\n"
                    "1. Match line items and PO identifier in the ERP ledger.\n"
                    "2. If billed amount exceeds PO amount by <= $50.00, autonomous auto-adjustment and ledger update is permitted.\n"
                    "3. If billed amount exceeds PO amount by > $50.00, the invoice must be held in FLAGGED_DISPUTE status, "
                    "an itemized dispute notice must be generated in the sandbox, and payment must NOT be dispatched without Human review."
                ),
                tags=["invoice", "purchase_order", "reconciliation", "erp", "discrepancy", "vendor"],
                rules={"tolerance_amount": 50.00, "auto_approve_max_variance": 50.00},
            ),
            SOPDocument(
                id="SOP-FIN-002",
                title="March 2026 Customer Refund Anomaly & Fraud Audit SOP",
                category="Finance",
                content=(
                    "Procedures for auditing customer refund anomalies:\n"
                    "1. Query refund requests from the ERP database.\n"
                    "2. Identify single claims exceeding $500.00 or repeat claims from the same customer profile.\n"
                    "3. All claims exceeding $500.00 are classified as anomalies and must be marked UNDER_REVIEW with flagged_anomaly=1.\n"
                    "4. Generate a consolidated cryptographic audit trail and compliance report before submitting claims."
                ),
                tags=["refund", "anomaly", "fraud", "customer", "audit", "march 2026", "claims"],
                rules={"anomaly_refund_threshold": 500.00},
            ),
            SOPDocument(
                id="SOP-SEC-003",
                title="Privileged Access Review & RBAC Governance SOP",
                category="Security",
                content=(
                    "Procedures for reviewing elevated access credentials:\n"
                    "1. Cross-reference database user tiers against active HR employee rosters.\n"
                    "2. Flag dormant accounts or unauthorized ADMIN_PRIVILEGED roles.\n"
                    "3. Modifications to administrative roles must be logged and require explicit policy gate verification."
                ),
                tags=["access", "rbac", "security", "privilege", "admin", "compliance"],
                rules={"require_dual_signoff_for_admin_revoke": True},
            ),
            SOPDocument(
                id="SOP-GOV-004",
                title="Corporate Financial State Mutation Threshold SOP",
                category="Governance",
                content=(
                    "Policy on autonomous execution of financial actions:\n"
                    "Any state-mutating action, disbursement, or ledger write involving a dollar amount >= $1,000.00 "
                    "is classified as HIGH RISK and strictly requires Human-in-the-Loop (HITL) authorization before completion."
                ),
                tags=["governance", "threshold", "authorization", "hitl", "wire", "payment"],
                rules={"financial_halt_threshold": 1000.00},
            ),
        ]
        for sop in sops:
            self.add_sop(sop)

        # Seed corporate policies
        policies = [
            PolicyRule(
                rule_id="POL-READ-001",
                name="Read-Only Autonomous Clearance",
                action_pattern=r"^(db_query|analytics_query|file_read|browser_inspect|list_directory)",
                condition_type="ACTION_TYPE",
                threshold=None,
                risk_level="LOW",
                requires_human_approval=False,
                description="All read-only data extraction queries are auto-approved without human delay.",
            ),
            PolicyRule(
                rule_id="POL-FIN-1000",
                name="Financial Transaction Authorization Threshold",
                action_pattern=r".*",
                condition_type="THRESHOLD",
                threshold=1000.00,
                risk_level="HIGH",
                requires_human_approval=True,
                description="Any operation involving $1,000.00 or higher requires explicit human sign-off.",
            ),
            PolicyRule(
                rule_id="POL-MUT-DESTRUCT",
                name="Destructive Record Deletion Guard",
                action_pattern=r"^(delete_.*|drop_.*)",
                condition_type="ACTION_TYPE",
                threshold=None,
                risk_level="CRITICAL",
                requires_human_approval=True,
                description="Destructive record deletions or database drops require Human-in-the-Loop approval.",
            ),
            PolicyRule(
                rule_id="POL-DISP-050",
                name="Discrepancy Dispute Enforcement",
                action_pattern=r"^(evaluate_discrepancy|update_ledger_portal)",
                condition_type="DISCREPANCY",
                threshold=50.00,
                risk_level="MEDIUM",
                requires_human_approval=False,
                description="Variance above $50.00 routes to dispute hold rather than auto-approval.",
            ),
        ]
        for pol in policies:
            self.add_policy(pol)

    def add_sop(self, sop: SOPDocument) -> None:
        """Store an enterprise SOP into persistent memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO enterprise_sops
                (id, title, category, content, tags_json, rules_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sop.id,
                    sop.title,
                    sop.category,
                    sop.content,
                    json.dumps(sop.tags),
                    json.dumps(sop.rules),
                    sop.created_at,
                ),
            )
            conn.commit()

    def add_policy(self, policy: PolicyRule) -> None:
        """Store an enforceable policy into persistent memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO enterprise_policies
                (rule_id, name, action_pattern, condition_type, threshold, risk_level, requires_human_approval, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    policy.rule_id,
                    policy.name,
                    policy.action_pattern,
                    policy.condition_type,
                    policy.threshold,
                    policy.risk_level,
                    1 if policy.requires_human_approval else 0,
                    policy.description,
                ),
            )
            conn.commit()

    def get_all_sops(self) -> List[SOPDocument]:
        """Fetch all SOPs from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM enterprise_sops")
            rows = cursor.fetchall()
            return [
                SOPDocument(
                    id=row["id"],
                    title=row["title"],
                    category=row["category"],
                    content=row["content"],
                    tags=json.loads(row["tags_json"]),
                    rules=json.loads(row["rules_json"]),
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def get_all_policies(self) -> List[PolicyRule]:
        """Fetch all registered corporate policies."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM enterprise_policies")
            rows = cursor.fetchall()
            return [
                PolicyRule(
                    rule_id=row["rule_id"],
                    name=row["name"],
                    action_pattern=row["action_pattern"],
                    condition_type=row["condition_type"],
                    threshold=row["threshold"],
                    risk_level=row["risk_level"],
                    requires_human_approval=bool(row["requires_human_approval"]),
                    description=row["description"],
                )
                for row in rows
            ]

    def query_sops(self, query: str, limit: int = 3) -> List[SOPDocument]:
        """
        Retrieve relevant SOPs using offline term frequency and keyword matching.
        """
        all_sops = self.get_all_sops()
        if not all_sops:
            return []

        tokens = re.findall(r"\w+", query.lower())
        if not tokens:
            return all_sops[:limit]

        scored_sops = []
        for sop in all_sops:
            corpus = f"{sop.title} {sop.category} {sop.content} {' '.join(sop.tags)}".lower()
            corpus_tokens = re.findall(r"\w+", corpus)
            score = 0.0
            for t in tokens:
                count = corpus_tokens.count(t)
                if count > 0:
                    score += 1.0 + math.log(1 + count)
            # Bonus points for tag exact match
            for tag in sop.tags:
                if tag.lower() in tokens or tag.lower() in query.lower():
                    score += 2.5
            scored_sops.append((score, sop))

        scored_sops.sort(key=lambda x: x[0], reverse=True)
        return [sop for score, sop in scored_sops if score > 0][:limit] or all_sops[:limit]

    def get_relevant_policies(self, action_name: str, params: Dict[str, Any]) -> List[PolicyRule]:
        """Match policies applicable to a given tool action and parameter context."""
        policies = self.get_all_policies()
        matched: List[PolicyRule] = []

        for pol in policies:
            # Check action pattern
            if pol.action_pattern != ".*" and not re.search(pol.action_pattern, action_name, re.IGNORECASE):
                continue

            # Check threshold condition
            if pol.condition_type == "THRESHOLD" and pol.threshold is not None:
                amount = None
                for key in ["amount", "total_amount", "invoice_amount", "po_amount", "refund_amount"]:
                    if key in params and isinstance(params[key], (int, float)):
                        amount = float(params[key])
                        break
                if amount is not None and amount >= pol.threshold:
                    matched.append(pol)
                continue

            # Check discrepancy condition
            if pol.condition_type == "DISCREPANCY" and pol.threshold is not None:
                variance = None
                if "variance" in params and isinstance(params["variance"], (int, float)):
                    variance = float(params["variance"])
                elif "invoice_amount" in params and "po_amount" in params:
                    variance = abs(float(params["invoice_amount"]) - float(params["po_amount"]))
                if variance is not None and variance > pol.threshold:
                    matched.append(pol)
                continue

            matched.append(pol)

        return matched

    def save_execution_checkpoint(self, task_id: str, state: Dict[str, Any], status: str) -> None:
        """Persist an execution checkpoint to survive halts, restarts, and approval delays."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO execution_checkpoints
                (task_id, status, state_json, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, status, json.dumps(state), time.time()),
            )
            conn.commit()

    def load_execution_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve execution checkpoint for a task ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT state_json FROM execution_checkpoints WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["state_json"])
            return None

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all saved execution checkpoints with metadata."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT task_id, status, updated_at FROM execution_checkpoints ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
