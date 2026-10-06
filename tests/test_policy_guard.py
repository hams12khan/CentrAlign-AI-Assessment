"""
Unit tests for Policy Guard and Human-in-the-Loop Governance Engine.

Validates:
- Auto-approval of read-only queries (db_query, file_read, etc.)
- Auto-approval of safe state mutations (< $1,000 threshold)
- Pause and emission of AWAITING_HUMAN_APPROVAL for high-risk actions (> $1,000, wire transfer, destructive drops)
- Cryptographic signature generation and verification on human sign-off
- Revocation of approval
"""

import pytest
from runtime.planner import TaskStep
from runtime.policy_guard import PolicyDecision, PolicyGuard


def test_read_only_tools_auto_approved(test_policy_guard: PolicyGuard):
    """Verify that read-only actions are auto-approved without human delay."""
    read_tools = ["db_query", "analytics_query", "file_read", "browser_inspect", "list_directory"]

    for tool in read_tools:
        step = TaskStep(id="step_read", tool=tool, params={"query": "test"})
        decision = test_policy_guard.evaluate_step(step, {"query": "test"})
        assert decision.verdict == "APPROVED"
        assert decision.risk_level == "LOW"


def test_safe_mutations_auto_approved(test_policy_guard: PolicyGuard):
    """Verify that updates below the $1,000 threshold are auto-approved."""
    step = TaskStep(
        id="step_safe_update",
        tool="db_update",
        params={"sql": "UPDATE purchase_orders SET status = 'RECONCILED' WHERE po_id = 'PO-1'", "amount": 250.00},
    )
    decision = test_policy_guard.evaluate_step(step, {"amount": 250.00})
    assert decision.verdict == "APPROVED"
    assert decision.risk_level == "MEDIUM"


def test_high_value_mutation_triggers_awaiting_approval(test_policy_guard: PolicyGuard):
    """Verify that operations >= $1,000 threshold trigger AWAITING_HUMAN_APPROVAL."""
    step = TaskStep(
        id="step_high_val",
        tool="db_update",
        params={"amount": 4500.00},
    )
    decision = test_policy_guard.evaluate_step(step, {"amount": 4500.00})
    assert decision.verdict == "AWAITING_HUMAN_APPROVAL"
    assert decision.risk_level == "HIGH"
    assert decision.required_role == "finance_manager"
    assert "exceeds autonomous threshold" in decision.reason


def test_destructive_sql_triggers_approval(test_policy_guard: PolicyGuard):
    """Verify that destructive SQL queries (DROP, DELETE) trigger approval halt."""
    step = TaskStep(
        id="step_destructive",
        tool="db_update",
        params={"sql": "DROP TABLE ledger_transactions"},
    )
    decision = test_policy_guard.evaluate_step(step, {"sql": "DROP TABLE ledger_transactions"})
    assert decision.verdict == "AWAITING_HUMAN_APPROVAL"
    assert decision.risk_level == "CRITICAL"


def test_grant_approval_and_cryptographic_signature(test_policy_guard: PolicyGuard):
    """Verify human signature issuance and subsequent approval verification."""
    step = TaskStep(id="step_wire", tool="wire_transfer", params={"amount": 50000.00})

    # Initial evaluation should halt
    decision1 = test_policy_guard.evaluate_step(step, {"amount": 50000.00})
    assert decision1.verdict == "AWAITING_HUMAN_APPROVAL"

    # Grant human approval
    record = test_policy_guard.grant_approval(
        step_id="step_wire",
        approver_id="VP_Finance_Officer",
        approver_role="finance_manager",
        comments="Approved as part of scheduled capital equipment purchase.",
    )
    assert record.signature_hash != ""
    assert test_policy_guard.is_approved("step_wire")

    # Second evaluation with approval recorded must be APPROVED
    decision2 = test_policy_guard.evaluate_step(step, {"amount": 50000.00})
    assert decision2.verdict == "APPROVED"
    assert "Approved by authorized human" in decision2.reason

    # Revoke approval
    test_policy_guard.revoke_approval("step_wire", "VP_Finance_Officer", "Duplicate invoice alert")
    assert not test_policy_guard.is_approved("step_wire")


def test_sql_amount_parsing_triggers_halt(test_policy_guard: PolicyGuard):
    """Verify that SQL containing UPDATE with amount >= 1000 halts."""
    step = TaskStep(
        id="step_sql_amt",
        tool="db_update",
        params={"sql": "UPDATE purchase_orders SET amount = 4500.00 WHERE po_id = 'PO-1'"},
    )
    decision = test_policy_guard.evaluate_step(step, step.params)
    assert decision.verdict == "AWAITING_HUMAN_APPROVAL"
    assert decision.risk_level == "HIGH"


def test_delete_action_triggers_critical_halt(test_policy_guard: PolicyGuard):
    """Verify that record deletion tool halts under critical risk."""
    step = TaskStep(
        id="step_del",
        tool="delete_customer_record",
        params={"customer_id": "C-101"},
    )
    decision = test_policy_guard.evaluate_step(step, step.params)
    assert decision.verdict == "AWAITING_HUMAN_APPROVAL"
    assert decision.risk_level == "CRITICAL"
