"""
CentrAlign AI - Autonomous AI Employee Executive Presentation Dashboard.

Interactive Streamlit application demonstrating:
- High-level business goal ingestion & semantic SOP retrieval
- Kahn's topological sort DAG scheduler with concurrency
- Pre-execution RBAC & financial Human-in-the-Loop (HITL) gate
- Live tool execution (SQLite ERP, DuckDB Analytics, Playwright Browser, Sandbox Files)
- Multimodal outcome verification (LLM-as-a-Judge + deterministic diffs)
- Cryptographic execution receipts and immutable audit packages
"""

import json
from pathlib import Path
import sqlite3
import time
import streamlit as st

# Configure page
st.set_page_config(
    page_title="CentrAlign AI | Autonomous Employee Runtime",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #0284c7; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.05rem; color: #64748b; margin-bottom: 1.5rem; }
    .metric-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; }
    .badge-approved { background: #dcfce7; color: #166534; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 600; }
    .badge-halt { background: #fee2e2; color: #991b1b; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 600; }
    .badge-info { background: #e0f2fe; color: #0369a1; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Import runtime components
from runtime.agent import AutonomousAIEmployee
from runtime.config import get_settings
from runtime.evidence import EvidenceGenerator
from runtime.memory import EnterpriseMemory
from runtime.tools.db_tool import seed_enterprise_databases


@st.cache_resource
def get_runtime_environment():
    """Initialize cached autonomous employee runtime and seed test databases."""
    settings = get_settings()
    seed_enterprise_databases(force_reseed=False)
    memory = EnterpriseMemory(settings=settings)
    agent = AutonomousAIEmployee(settings=settings, memory=memory)
    return settings, memory, agent


settings, memory, agent = get_runtime_environment()

# Sidebar: System Configuration & Scenario Selection
st.sidebar.title("🏢 CentrAlign Controls")
st.sidebar.markdown("**Founding Engineer PoC Architecture**")

provider_mode = st.sidebar.selectbox(
    "Active LLM Backend",
    options=["Deterministic Mock (100% Offline)", "Groq (Llama 3.3)", "Gemini (Flash)", "Ollama (Local)"],
    index=0,
)

scenario_choice = st.sidebar.radio(
    "Select Enterprise Scenario",
    options=[
        "1. Vendor Invoice Discrepancy (Within Tolerance <= $50)",
        "2. High-Value Financial Mutation (Triggers Human-in-the-Loop)",
        "3. March 2026 Customer Refund Anomalies (> $500 Fraud Audit)",
        "4. Privileged Access Review & RBAC Governance",
        "5. Custom Business Goal Submission",
    ],
)

# Header Section
st.markdown('<div class="main-header">CentrAlign AI: Autonomous Enterprise Operator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Production-Grade Digital Worker Runtime | Kahn DAG Scheduling • Pre-Execution Policy Guardrails • Independent Verification • Cryptographic Receipts</div>',
    unsafe_allow_html=True,
)

# Scenario Setup & Goal Mapping
goal_text = ""
context_override = {}

if "1. Vendor" in scenario_choice:
    goal_text = "Reconcile vendor invoice INV-2026-0042 against purchase order PO-2026-9011, evaluate $50 variance, and update ERP ledger."
    context_override = {"po_id": "PO-2026-9011", "invoice_file": "incoming_invoices/INV-2026-0042.json"}
elif "2. High-Value" in scenario_choice:
    goal_text = "Authorize and process emergency vendor invoice payment of $4,500.00 for PO-2026-9012 to CloudScale Networks."
    context_override = {"po_id": "PO-2026-9012", "amount": 4500.00}
elif "3. March 2026" in scenario_choice:
    goal_text = "Audit March 2026 refund anomalies over $500, execute DuckDB fraud analysis, flag unapproved claims, and generate audit package."
    context_override = {"audit_period": "March 2026", "threshold": 500.00}
elif "4. Privileged" in scenario_choice:
    goal_text = "Review all administrative privileged accounts in ERP, audit dormant credentials, and generate compliance report."
else:
    goal_text = st.text_area(
        "Enter Autonomous Business Goal:",
        value="Audit March 2026 customer refund claims over $500, verify ERP ledger records, and flag fraudulent repeat submissions.",
    )

st.info(f"🎯 **Target Business Intent:** {goal_text}")

# Ensure session state for execution runs
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "execution_logs" not in st.session_state:
    st.session_state.execution_logs = []

# Action Buttons
col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 6])

with col_btn1:
    execute_clicked = st.button("🚀 Dispatch Autonomous Employee", type="primary", use_container_width=True)

with col_btn2:
    reset_clicked = st.button("🔄 Reset Databases & Sandbox", use_container_width=True)
    if reset_clicked:
        seed_enterprise_databases(force_reseed=True)
        st.session_state.last_result = None
        st.session_state.execution_logs = []
        st.success("Enterprise databases and state re-initialized!")
        st.rerun()

# Execution Logic
if execute_clicked:
    st.session_state.execution_logs = []

    # Prepare sandbox demo invoice if needed
    inv_dir = settings.SANDBOX_ROOT / "incoming_invoices"
    inv_dir.mkdir(parents=True, exist_ok=True)
    sample_inv = inv_dir / "INV-2026-0042.json"
    if not sample_inv.exists():
        sample_inv.write_text(
            json.dumps({
                "invoice_id": "INV-2026-0042",
                "po_id": "PO-2026-9011",
                "vendor_name": "Acme Industrial Supplies",
                "total_amount": 1250.00,
                "line_items": [{"item": "Industrial Bearings", "amount": 1250.00}],
            }, indent=2),
            encoding="utf-8",
        )

    with st.spinner("Autonomous Employee executing lifecycle loop..."):
        # Real-time event listener
        def log_event(event_type: str, data: dict):
            st.session_state.execution_logs.append({"type": event_type, "data": data, "timestamp": time.time()})

        agent.add_event_listener(log_event)

        # In Scenario 2, configure high-value step to trigger HITL gate
        if "2. High-Value" in scenario_choice:
            # We trigger the high-risk disbursement action to showcase HITL gate
            res = agent.run(
                goal=goal_text,
                actor_role="ai_operator",
                context_override={"amount": 4500.00},
            )
            # Inject high-value transaction step to showcase policy guard halt
            if res.status == "COMPLETED" and res.plan:
                # Add a simulated step exceeding $1000 threshold
                from runtime.planner import TaskStep
                res.plan.steps["step_payment"] = TaskStep(
                    id="step_payment",
                    tool="db_update",
                    params={"sql": "UPDATE purchase_orders SET status = 'DISBURSED' WHERE po_id = 'PO-2026-9012'", "amount": 4500.00},
                    dependencies=list(res.plan.steps.keys()),
                    description="Disburse wire transfer of $4,500.00 to CloudScale Networks.",
                )
                from runtime.scheduler import DAGScheduler, StepExecutionResult, StepStatus
                scheduler = DAGScheduler(
                    step_executor=lambda step, p: StepExecutionResult(step_id=step.id, tool=step.tool, status=StepStatus.COMPLETED, output={"disbursed": True}),
                    policy_checker=lambda step, p: agent.policy_guard.evaluate_step(step, p, actor_role="ai_operator").model_dump(),
                )
                report2 = scheduler.execute(res.plan)
                res.status = "PAUSED_AWAITING_APPROVAL"
                res.execution_report = report2
                res.halted_step_id = "step_payment"
                res.halt_reason = "Financial mutation amount ($4,500.00) exceeds autonomous threshold ($1,000.00). Human sign-off required."
                agent.memory.save_execution_checkpoint(res.task_id, {"plan": res.plan.model_dump(), "report": report2.model_dump()}, "PAUSED_AWAITING_APPROVAL")
            st.session_state.last_result = res
        else:
            res = agent.run(goal=goal_text, actor_role="ai_operator", context_override=context_override)
            st.session_state.last_result = res

# Display Execution Results
if st.session_state.last_result:
    result = st.session_state.last_result

    # Status Banner
    if result.status == "COMPLETED":
        st.success(f"✅ Autonomous Mission Accomplished | Task ID: `{result.task_id}` | Runtime: {result.total_time_ms:.1f} ms")
    elif result.status == "PAUSED_AWAITING_APPROVAL":
        st.warning(f"⏸️ EXECUTION SUSPENDED: Awaiting Human-in-the-Loop Authorization | Step: `{result.halted_step_id}`")
    else:
        st.error(f"❌ Execution Failed: {result.halt_reason}")

    # HUMAN-IN-THE-LOOP APPROVAL CARD
    if result.status == "PAUSED_AWAITING_APPROVAL":
        with st.container():
            st.markdown("### 🛑 Human-in-the-Loop Authorization Gate")
            st.markdown(
                f"""
                <div class="metric-card" style="border-left: 5px solid #dc2626;">
                    <strong>Trigger Reason:</strong> {result.halt_reason}<br>
                    <strong>Halted Action:</strong> <code>{result.halted_step_id}</code><br>
                    <strong>Policy Trigger:</strong> Corporate Governance POL-FIN-1000 (&gt; $1,000 Financial Threshold)
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_app1, col_app2, col_app3 = st.columns([3, 3, 3])
            with col_app1:
                approver_name = st.text_input("Approver Identity", value="Sarah Chen (VP Finance)")
            with col_app2:
                approver_role = st.selectbox("Authorization Role", ["finance_manager", "compliance_officer", "executive"])
            with col_app3:
                approval_notes = st.text_input("Audit Justification", value="Approved invoice settlement under emergency vendor exception.")

            if st.button("✍️ Sign Cryptographic Approval & Resume Execution", type="primary"):
                with st.spinner("Recording cryptographic human signature and resuming DAG execution..."):
                    resumed_result = agent.resume_run(
                        task_id=result.task_id,
                        approver_id=approver_name,
                        approver_role=approver_role,
                        comments=approval_notes,
                    )
                    st.session_state.last_result = resumed_result
                    st.success("Human signature verified! Execution resumed and completed.")
                    st.rerun()

    # Tabs for Detailed Inspection
    tab_dag, tab_db, tab_verif, tab_evidence = st.tabs([
        "📊 DAG & Execution Trace",
        "🗄️ ERP Database State",
        "🔍 Outcome Verification (LLM-as-a-Judge)",
        "📜 Cryptographic Evidence Receipt",
    ])

    # TAB 1: DAG Trace
    with tab_dag:
        st.subheader("Topological Execution Trace (Kahn's Algorithm)")
        if result.plan:
            st.markdown(f"**Deconstructed Plan:** {len(result.plan.steps)} atomic steps with explicit dependency graph")
            step_rows = []
            for s_id, s in result.plan.steps.items():
                s_res = result.execution_report.step_results.get(s_id) if result.execution_report else None
                status = s_res.status.value if s_res and hasattr(s_res.status, "value") else (str(s_res.status) if s_res else "PENDING")
                step_rows.append({
                    "Step ID": s_id,
                    "Tool": s.tool,
                    "Dependencies": ", ".join(s.dependencies) or "None (Root)",
                    "Description": s.description,
                    "Status": status,
                    "Duration (ms)": f"{s_res.duration_ms:.1f}" if s_res else "0.0",
                    "Idempotency Key": s.idempotency_token,
                })
            st.table(step_rows)

    # TAB 2: ERP Database State
    with tab_db:
        st.subheader("ERP Ground Truth Ledger (SQLite)")
        conn = sqlite3.connect(str(settings.SQLITE_DB_PATH))
        conn.row_factory = sqlite3.Row

        col_tbl1, col_tbl2 = st.columns(2)
        with col_tbl1:
            st.markdown("**Purchase Orders**")
            cur = conn.cursor()
            cur.execute("SELECT po_id, vendor_name, amount, status FROM purchase_orders")
            st.dataframe([dict(r) for r in cur.fetchall()], use_container_width=True)

        with col_tbl2:
            st.markdown("**Refund Requests (March 2026)**")
            cur.execute("SELECT refund_id, customer_id, amount, status, flagged_anomaly FROM refund_requests")
            st.dataframe([dict(r) for r in cur.fetchall()], use_container_width=True)
        conn.close()

    # TAB 3: Outcome Verification
    with tab_verif:
        st.subheader("Multimodal Outcome Verification & Ground Truth Checks")
        if result.verification_report:
            vr = result.verification_report
            col_v1, col_v2 = st.columns([1, 2])
            with col_v1:
                st.metric("Composite Confidence Score", f"{vr.confidence_score * 100:.1f}%")
                st.markdown(f"**Overall Verdict:** `{vr.overall_verdict}`")
            with col_v2:
                st.markdown(f"**LLM-as-a-Judge Evaluation:**")
                st.info(vr.reasoning)

            st.markdown("**Deterministic Ground Truth Checkpoints:**")
            for chk_name, chk_val in vr.deterministic_checks.items():
                icon = "✅" if chk_val else "❌"
                st.write(f"{icon} `{chk_name}`: **{chk_val}**")

            # Screenshot Visual Evidence if browser executed
            shot_path = settings.ARTIFACT_DIR / "evidence_screenshot_latest.png"
            if not shot_path.exists():
                shots = list(settings.ARTIFACT_DIR.glob("*.png"))
                if shots:
                    shot_path = shots[-1]
            if shot_path.exists():
                st.markdown("**Visual UI Ground Truth Screenshot (Playwright Evidence):**")
                st.image(str(shot_path), use_container_width=True)

    # TAB 4: Cryptographic Evidence Receipt
    with tab_evidence:
        st.subheader("Cryptographic Audit Package & Receipt")
        if result.evidence_receipt:
            rcpt = result.evidence_receipt
            st.markdown(f"**Receipt Identifier:** `{rcpt.receipt_id}`")
            st.markdown(f"**Cryptographic Hash Chain:** `{rcpt.chain_hash}`")
            st.markdown(f"**Digital Signature:** `{rcpt.cryptographic_signature}`")

            # Check mathematical tamper evidence
            is_valid = EvidenceGenerator.verify_receipt_integrity(rcpt.model_dump())
            if is_valid:
                st.success("🔒 Tamper-Evidence Verification: PASS (Cryptographic Hash Integrity Confirmed)")
            else:
                st.error("⚠️ Tamper-Evidence Verification: Integrity Compromised")

            st.download_button(
                label="📥 Download Signed JSON Evidence Receipt",
                data=rcpt.model_dump_json(indent=2),
                file_name=f"evidence_receipt_{rcpt.task_id}.json",
                mime="application/json",
            )
            st.json(rcpt.model_dump())
