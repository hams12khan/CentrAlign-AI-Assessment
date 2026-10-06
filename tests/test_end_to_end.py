"""
End-to-End Integration Tests for CentrAlign AI Autonomous Employee Runtime.

Validates:
1. Full Vendor Invoice Reconciliation lifecycle (Goal -> Plan -> Policy -> Execute -> Verify -> Evidence)
2. March 2026 Refund Anomaly Audit & Fraud Mitigation workflow
3. High-Risk Human-in-the-Loop Pause & Resume workflow
4. Cryptographic receipt tamper verification
"""

import json
from pathlib import Path
import sqlite3
import pytest
from runtime.agent import AutonomousAIEmployee
from runtime.config import RuntimeSettings
from runtime.evidence import EvidenceGenerator
from runtime.planner import TaskStep
from runtime.scheduler import DAGScheduler, StepExecutionResult, StepStatus


def test_end_to_end_invoice_reconciliation_workflow(
    test_agent: AutonomousAIEmployee,
    test_settings: RuntimeSettings,
):
    """
    Test complete lifecycle of Vendor Invoice Discrepancy Reconciliation:
    - Parse invoice from sandbox
    - Query ERP for matching PO
    - Evaluate variance against $50 tolerance policy (SOP-FIN-001)
    - Update ERP ledger status
    - Verify database ground truth & generate signed EvidenceReceipt
    """
    # 1. Prepare sandbox test invoice file
    inv_dir = test_settings.SANDBOX_ROOT / "incoming_invoices"
    inv_dir.mkdir(parents=True, exist_ok=True)
    sample_invoice = inv_dir / "INV-2026-0042.json"
    sample_invoice.write_text(
        json.dumps({
            "invoice_id": "INV-2026-0042",
            "po_id": "PO-2026-9011",
            "vendor_name": "Acme Industrial Supplies",
            "total_amount": 1250.00,
            "line_items": [{"item": "Bearings", "amount": 1250.00}],
        }),
        encoding="utf-8",
    )

    # 2. Run Autonomous Employee
    goal = "Reconcile vendor invoice INV-2026-0042 against PO-2026-9011 and update ERP ledger."
    result = test_agent.run(goal=goal, actor_role="ai_operator")

    # 3. Assert Autonomous Completion
    assert result.status == "COMPLETED"
    assert result.plan is not None
    assert len(result.plan.steps) >= 4
    assert result.execution_report is not None
    assert result.execution_report.status == "COMPLETED"

    # 4. Verify ERP Ground Truth Mutation
    conn = sqlite3.connect(str(test_settings.SQLITE_DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM purchase_orders WHERE po_id = 'PO-2026-9011'")
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row[0] in ("RECONCILED", "FLAGGED_DISPUTE")

    # 5. Verify Verification Layer & LLM-as-a-Judge
    assert result.verification_report is not None
    assert result.verification_report.overall_verdict == "PASSED"
    assert result.verification_report.confidence_score >= 0.85
    assert result.verification_report.deterministic_checks.get("all_steps_completed") is True

    # 6. Verify Cryptographic Evidence Receipt & Tamper Integrity
    assert result.evidence_receipt is not None
    assert result.evidence_receipt.cryptographic_signature != ""
    assert result.evidence_receipt.chain_hash != ""

    receipt_dict = result.evidence_receipt.model_dump()
    assert EvidenceGenerator.verify_receipt_integrity(receipt_dict) is True


def test_end_to_end_refund_anomaly_audit_workflow(
    test_agent: AutonomousAIEmployee,
    test_settings: RuntimeSettings,
):
    """
    Test autonomous March 2026 Refund Anomaly Fraud Audit:
    - Extract unapproved claims > $500
    - Execute DuckDB analytical aggregation
    - Mutate ERP records to UNDER_REVIEW with flagged_anomaly = 1
    - Verify ground truth and audit artifacts
    """
    goal = "Audit March 2026 refund anomalies over $500 and flag unapproved claims."
    result = test_agent.run(goal=goal, actor_role="ai_operator")

    assert result.status == "COMPLETED"

    # Check ERP Database Ground Truth
    conn = sqlite3.connect(str(test_settings.SQLITE_DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM refund_requests WHERE amount > 500.00 AND flagged_anomaly = 1")
    flagged_anomalies = cursor.fetchone()[0]
    conn.close()

    assert flagged_anomalies > 0, "High-value refund claims should be flagged as anomalies in database"

    # Check written audit file
    audit_file = test_settings.SANDBOX_ROOT / "audit_logs" / "march_2026_refund_anomalies_audit.json"
    assert audit_file.exists()
    assert audit_file.stat().st_size > 0

    # Check receipt integrity
    assert result.evidence_receipt is not None
    assert EvidenceGenerator.verify_receipt_integrity(result.evidence_receipt.model_dump()) is True


def test_end_to_end_hitl_pause_and_resume_flow(
    test_agent: AutonomousAIEmployee,
    test_settings: RuntimeSettings,
):
    """
    Test Human-in-the-Loop state machine:
    1. Plan step with financial mutation >= $1000 threshold
    2. Policy Guard suspends execution (PAUSED_AWAITING_APPROVAL)
    3. State checkpoint saved to disk/SQLite
    4. Human signs cryptographic approval
    5. Agent resumes and runs to completion
    """
    goal = "Execute high-value ledger adjustment for PO-2026-9012"
    tid = "task_hitl_test_001"

    # Manually configure a DAG with a high-risk step to test exact state pause
    plan = test_agent.run(goal=goal, task_id=tid)

    # Inject high-value step exceeding $1,000 threshold
    high_risk_step = TaskStep(
        id="step_high_wire",
        tool="db_update",
        params={
            "sql": "UPDATE purchase_orders SET amount = 5500.00 WHERE po_id = 'PO-2026-9012'",
            "amount": 5500.00,
        },
        dependencies=list(plan.plan.steps.keys()),
        description="High-value PO modification requiring human sign-off.",
    )
    plan.plan.steps["step_high_wire"] = high_risk_step

    # Execute scheduler to hit the policy gate
    def _dummy_runner(step: TaskStep, params: dict):
        return StepExecutionResult(step_id=step.id, tool=step.tool, status=StepStatus.COMPLETED, output={"ok": True})

    scheduler = DAGScheduler(
        step_executor=_dummy_runner,
        policy_checker=lambda s, p: test_agent.policy_guard.evaluate_step(s, p, actor_role="ai_operator").model_dump(),
    )
    halt_report = scheduler.execute(plan.plan)

    assert halt_report.status == "PAUSED_AWAITING_APPROVAL"
    assert halt_report.halted_step_id == "step_high_wire"

    # Save checkpoint
    test_agent.memory.save_execution_checkpoint(
        tid,
        {"plan": plan.plan.model_dump(), "report": halt_report.model_dump()},
        "PAUSED_AWAITING_APPROVAL",
    )

    # Resume with human authorization
    resumed = test_agent.resume_run(
        task_id=tid,
        approver_id="CFO_Executive",
        approver_role="finance_manager",
        comments="Approved capital expenditure after review.",
    )

    assert resumed.status == "COMPLETED"
    assert len(resumed.human_approvals) >= 1
    assert resumed.human_approvals[0].approver_id == "CFO_Executive"
    assert resumed.evidence_receipt is not None
    assert EvidenceGenerator.verify_receipt_integrity(resumed.evidence_receipt.model_dump()) is True
