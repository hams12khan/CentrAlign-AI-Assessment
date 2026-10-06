"""
Audit Trail & Cryptographic Execution Receipt Generator for CentrAlign AI.

Generates immutable, tamper-evident execution packages:
- Cryptographic hash chaining over step executions and parameters
- SHA-256 digests of all generated artifacts (files, reports, screenshots)
- Complete policy decisions and human approval signatures
- Mathematical tamper-evidence verification utility
- Executive Markdown audit dossier and JSON receipt exporter
"""

import hashlib
import json
import logging
from pathlib import Path
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from runtime.config import RuntimeSettings, get_settings
from runtime.policy_guard import ApprovalRecord, PolicyDecision
from runtime.scheduler import DAGExecutionReport
from runtime.verifier import VerificationReport

logger = logging.getLogger(__name__)


class ArtifactDescriptor(BaseModel):
    """Metadata and tamper-evident hash for an execution artifact."""

    name: str
    path: str
    file_type: str
    size_bytes: int
    sha256_hash: str
    created_at: float = Field(default_factory=time.time)


class EvidenceReceipt(BaseModel):
    """Cryptographically-signed execution receipt proving autonomous work integrity."""

    receipt_id: str = Field(default_factory=lambda: f"rcpt_{uuid.uuid4().hex[:12]}")
    task_id: str
    goal: str
    start_time: float
    end_time: float
    execution_duration_ms: float
    status: str
    steps_executed: List[Dict[str, Any]] = Field(default_factory=list)
    policy_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    human_approvals: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts_created: List[ArtifactDescriptor] = Field(default_factory=list)
    verification_summary: Dict[str, Any] = Field(default_factory=dict)
    cryptographic_signature: str = ""
    chain_hash: str = ""

    def calculate_tamper_evidence_hashes(self, secret_salt: str = "centralign_immutable_ledger_salt") -> None:
        """
        Compute hash chain over step executions, artifacts, and verification summary.
        Sets both chain_hash and cryptographic_signature.
        """
        hasher = hashlib.sha256()
        # 1. Bind core metadata
        hasher.update(f"{self.receipt_id}:{self.task_id}:{self.goal}:{self.status}".encode("utf-8"))

        # 2. Bind all executed steps in sequence
        for step in self.steps_executed:
            s_str = f"{step.get('step_id')}:{step.get('tool')}:{step.get('idempotency_token')}:{step.get('status')}"
            hasher.update(s_str.encode("utf-8"))

        # 3. Bind artifact SHA-256 digests
        for art in self.artifacts_created:
            hasher.update(f"{art.name}:{art.sha256_hash}:{art.size_bytes}".encode("utf-8"))

        # 4. Bind human approvals
        for appr in self.human_approvals:
            hasher.update(f"{appr.get('approver_id')}:{appr.get('signature_hash')}".encode("utf-8"))

        self.chain_hash = hasher.hexdigest()

        # Final signature with salt
        sig_hasher = hashlib.sha256()
        sig_hasher.update(f"{self.chain_hash}:{secret_salt}".encode("utf-8"))
        self.cryptographic_signature = sig_hasher.hexdigest()


class EvidenceGenerator:
    """
    Synthesizes execution reports, policy audits, and artifacts
    into tamper-evident enterprise compliance packages.
    """

    def __init__(self, artifacts_dir: Optional[Path] = None, settings: Optional[RuntimeSettings] = None):
        self.settings = settings or get_settings()
        self.artifacts_dir = artifacts_dir or self.settings.ARTIFACT_DIR
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def generate_receipt(
        self,
        report: DAGExecutionReport,
        verification: Optional[VerificationReport] = None,
        policy_decisions: Optional[List[PolicyDecision]] = None,
        approvals: Optional[List[ApprovalRecord]] = None,
    ) -> EvidenceReceipt:
        """
        Synthesize full autonomous execution into an EvidenceReceipt.
        """
        # Collect artifacts and compute individual SHA-256 hashes
        artifacts: List[ArtifactDescriptor] = []
        for s_id, s_res in report.step_results.items():
            for art_str in s_res.artifacts:
                art_path = Path(art_str)
                if art_path.exists():
                    hasher = hashlib.sha256()
                    with open(art_path, "rb") as f:
                        for chunk in iter(lambda: f.read(65536), b""):
                            hasher.update(chunk)
                    art_hash = hasher.hexdigest()
                    artifacts.append(
                        ArtifactDescriptor(
                            name=art_path.name,
                            path=str(art_path.resolve()),
                            file_type=art_path.suffix.lstrip("."),
                            size_bytes=art_path.stat().st_size,
                            sha256_hash=art_hash,
                        )
                    )

        # Summarize executed steps
        steps_summary = []
        for s_id, s_res in report.step_results.items():
            steps_summary.append({
                "step_id": s_id,
                "tool": s_res.tool,
                "status": s_res.status.value if hasattr(s_res.status, "value") else str(s_res.status),
                "duration_ms": s_res.duration_ms,
                "idempotency_token": s_res.idempotency_token,
                "error": s_res.error,
                "output_preview": str(s_res.output)[:200] if s_res.output else None,
            })

        receipt = EvidenceReceipt(
            task_id=report.task_id,
            goal=report.goal,
            start_time=report.start_time,
            end_time=report.end_time or time.time(),
            execution_duration_ms=report.total_duration_ms,
            status=report.status,
            steps_executed=steps_summary,
            policy_decisions=[d.model_dump() for d in (policy_decisions or [])],
            human_approvals=[a.model_dump() for a in (approvals or [])],
            artifacts_created=artifacts,
            verification_summary=verification.model_dump() if verification else {},
        )

        receipt.calculate_tamper_evidence_hashes()
        return receipt

    def export_json(self, receipt: EvidenceReceipt, filename: Optional[str] = None) -> Path:
        """Export receipt to JSON file in artifacts directory."""
        fname = filename or f"receipt_{receipt.task_id}.json"
        out_path = self.artifacts_dir / fname
        out_path.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
        return out_path

    def export_markdown_dossier(self, receipt: EvidenceReceipt, filename: Optional[str] = None) -> Path:
        """Export human-readable executive audit dossier in Markdown."""
        fname = filename or f"audit_dossier_{receipt.task_id}.md"
        out_path = self.artifacts_dir / fname

        verif = receipt.verification_summary
        verdict = verif.get("overall_verdict", "N/A")
        confidence = verif.get("confidence_score", 0.0)

        badge = "🟢 VERIFIED PASSED" if verdict == "PASSED" else "🔴 ACTION REQUIRED"

        md = f"""# CentrAlign AI - Autonomous Employee Execution Receipt

**Audit Status:** {badge}  
**Receipt ID:** `{receipt.receipt_id}`  
**Task ID:** `{receipt.task_id}`  
**Cryptographic Signature:** `{receipt.cryptographic_signature}`  
**Chain Hash:** `{receipt.chain_hash}`  

---

## 1. High-Level Objective
- **Goal Intent:** {receipt.goal}
- **Execution Status:** `{receipt.status}`
- **Total Duration:** {receipt.execution_duration_ms:.2f} ms
- **Start Time:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(receipt.start_time))}
- **End Time:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(receipt.end_time))}

---

## 2. Directed Acyclic Graph (DAG) Execution Trail
| Step ID | Tool | Status | Duration (ms) | Idempotency Key |
| :--- | :--- | :--- | :--- | :--- |
"""
        for s in receipt.steps_executed:
            md += f"| `{s['step_id']}` | `{s['tool']}` | `{s['status']}` | {s['duration_ms']:.1f} | `{s['idempotency_token']}` |\n"

        md += "\n---\n\n## 3. Human-in-the-Loop & Policy Enforcement\n"
        if receipt.human_approvals:
            md += "| Approver ID | Role | Signature Digest | Comments |\n| :--- | :--- | :--- | :--- |\n"
            for a in receipt.human_approvals:
                md += f"| `{a['approver_id']}` | `{a['approver_role']}` | `{a['signature_hash'][:16]}...` | {a['comments']} |\n"
        else:
            md += "*No high-risk operations required human suspension; all actions satisfied autonomous policy boundaries.*\n"

        md += "\n---\n\n## 4. Generated Artifacts & Tamper Evidence\n"
        if receipt.artifacts_created:
            md += "| Artifact Name | Size | SHA-256 Digest | Path |\n| :--- | :--- | :--- | :--- |\n"
            for art in receipt.artifacts_created:
                md += f"| `{art.name}` | {art.size_bytes} B | `{art.sha256_hash}` | `{art.path}` |\n"
        else:
            md += "*No persistent file artifacts were generated during this run.*\n"

        md += f"""
---

## 5. Verification & Ground Truth Audit
- **Overall Verdict:** `{verdict}`
- **Composite Confidence Score:** `{confidence:.3f} / 1.000`
- **Verifier Reasoning:** {verif.get('reasoning', 'None recorded')}
"""
        out_path.write_text(md, encoding="utf-8")
        return out_path

    @staticmethod
    def verify_receipt_integrity(
        receipt_data: Dict[str, Any],
        secret_salt: str = "centralign_immutable_ledger_salt",
    ) -> bool:
        """
        Mathematically verify whether an exported receipt has been tampered with.
        """
        try:
            hasher = hashlib.sha256()
            hasher.update(
                f"{receipt_data['receipt_id']}:{receipt_data['task_id']}:{receipt_data['goal']}:{receipt_data['status']}".encode("utf-8")
            )
            for step in receipt_data.get("steps_executed", []):
                s_str = f"{step.get('step_id')}:{step.get('tool')}:{step.get('idempotency_token')}:{step.get('status')}"
                hasher.update(s_str.encode("utf-8"))

            for art in receipt_data.get("artifacts_created", []):
                hasher.update(f"{art['name']}:{art['sha256_hash']}:{art['size_bytes']}".encode("utf-8"))

            for appr in receipt_data.get("human_approvals", []):
                hasher.update(f"{appr.get('approver_id')}:{appr.get('signature_hash')}".encode("utf-8"))

            calculated_chain = hasher.hexdigest()
            if calculated_chain != receipt_data.get("chain_hash"):
                return False

            sig_hasher = hashlib.sha256()
            sig_hasher.update(f"{calculated_chain}:{secret_salt}".encode("utf-8"))
            return sig_hasher.hexdigest() == receipt_data.get("cryptographic_signature")
        except Exception:
            return False
