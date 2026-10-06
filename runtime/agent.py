"""
Core Autonomous AI Employee Runtime Loop for CentrAlign AI.

Coordinates the complete end-to-end execution lifecycle:
Goal -> Understand (SOPs) -> Plan (DAG) -> Policy Gate (RBAC) -> Execute (Tools) ->
Observe -> Adapt (Self-Healing) -> Verify (Eyes) -> Complete (Evidence Receipt).

Supports immediate Pause on High-Risk actions, state persistence in SQLite,
and seamless Resume upon cryptographic human authorization.
"""

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from runtime.config import RuntimeSettings, get_settings
from runtime.evidence import EvidenceGenerator, EvidenceReceipt
from runtime.llm_provider import BaseLLMProvider, get_llm_provider
from runtime.memory import EnterpriseMemory
from runtime.planner import DAGPlan, DAGPlanner, TaskStep
from runtime.policy_guard import ApprovalRecord, PolicyDecision, PolicyGuard
from runtime.scheduler import (
    DAGExecutionReport,
    DAGScheduler,
    StepExecutionResult,
    StepStatus,
)
from runtime.tools import ToolRegistry, create_default_tool_registry
from runtime.verifier import OutcomeVerifier, VerificationReport

logger = logging.getLogger(__name__)


class AgentRunResult(BaseModel):
    """Encapsulates the full execution state and deliverables of an autonomous run."""

    task_id: str
    goal: str
    status: Literal["COMPLETED", "PAUSED_AWAITING_APPROVAL", "FAILED"]
    plan: Optional[DAGPlan] = None
    execution_report: Optional[DAGExecutionReport] = None
    policy_decisions: List[PolicyDecision] = Field(default_factory=list)
    human_approvals: List[ApprovalRecord] = Field(default_factory=list)
    verification_report: Optional[VerificationReport] = None
    evidence_receipt: Optional[EvidenceReceipt] = None
    halted_step_id: Optional[str] = None
    halt_reason: Optional[str] = None
    total_time_ms: float = 0.0


class AutonomousAIEmployee:
    """
    Principal Enterprise Autonomous Operator Runtime.
    Translates high-level business goals into verified enterprise mutations with audit proof.
    """

    def __init__(
        self,
        settings: Optional[RuntimeSettings] = None,
        llm: Optional[BaseLLMProvider] = None,
        memory: Optional[EnterpriseMemory] = None,
        tools: Optional[ToolRegistry] = None,
        policy_guard: Optional[PolicyGuard] = None,
        verifier: Optional[OutcomeVerifier] = None,
        evidence_gen: Optional[EvidenceGenerator] = None,
    ):
        self.settings = settings or get_settings()
        self.llm = llm or get_llm_provider(self.settings)
        self.memory = memory or EnterpriseMemory(settings=self.settings)
        self.tools = tools or create_default_tool_registry()
        self.policy_guard = policy_guard or PolicyGuard(memory=self.memory, settings=self.settings)
        self.verifier = verifier or OutcomeVerifier(
            sqlite_path=self.settings.SQLITE_DB_PATH,
            llm_client=self.llm,
            settings=self.settings,
        )
        self.evidence_gen = evidence_gen or EvidenceGenerator(
            artifacts_dir=self.settings.ARTIFACT_DIR,
            settings=self.settings,
        )
        self.listeners: List[Callable[[str, Dict[str, Any]], None]] = []

    def add_event_listener(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Add event listener for real-time dashboard visualization."""
        self.listeners.append(callback)

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        for listener in self.listeners:
            try:
                listener(event_type, data)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    def run(
        self,
        goal: str,
        task_id: Optional[str] = None,
        actor_role: str = "ai_operator",
        context_override: Optional[Dict[str, Any]] = None,
    ) -> AgentRunResult:
        """
        Execute full autonomous agent lifecycle for a given business goal.
        """
        t_start = time.time()
        tid = task_id or f"task_{uuid.uuid4().hex[:8]}"

        self._emit("run_started", {"task_id": tid, "goal": goal, "role": actor_role})

        # 1. UNDERSTAND & PLAN: Retrieve SOPs and Compile DAG
        self._emit("planning_started", {"task_id": tid, "goal": goal})
        planner = DAGPlanner(llm_client=self.llm, memory=self.memory)
        available_tool_names = [t["name"] for t in self.tools.list_tools()]
        plan = planner.generate_plan(
            goal=goal,
            task_id=tid,
            available_tools=available_tool_names,
            context_override=context_override,
        )
        self._emit("planning_completed", {"task_id": tid, "steps_count": len(plan.steps)})

        # Save initial checkpoint
        self.memory.save_execution_checkpoint(tid, {"plan": plan.model_dump(), "stage": "PLANNED"}, "PLANNED")

        # 2. Wire Scheduler with Tools & Policy Gate
        def _step_runner(step: TaskStep, params: Dict[str, Any]) -> StepExecutionResult:
            t0 = time.time()
            tool_res = self.tools.execute(step.tool, params)
            t1 = time.time()
            return StepExecutionResult(
                step_id=step.id,
                tool=step.tool,
                status=StepStatus.COMPLETED if tool_res.success else StepStatus.FAILED,
                output=tool_res.output,
                error=tool_res.error,
                artifacts=tool_res.artifacts,
                start_time=t0,
                end_time=t1,
                duration_ms=(t1 - t0) * 1000.0,
                idempotency_token=step.idempotency_token,
                metadata=tool_res.metadata,
            )

        def _policy_checker(step: TaskStep, params: Dict[str, Any]) -> Dict[str, Any]:
            decision = self.policy_guard.evaluate_step(step, params, actor_role=actor_role)
            return decision.model_dump()

        scheduler = DAGScheduler(
            max_workers=self.settings.MAX_PARALLEL_WORKERS,
            step_executor=_step_runner,
            policy_checker=_policy_checker,
        )

        for l in self.listeners:
            scheduler.add_listener(l)

        # 3. EXECUTE: Kahn's topological sort execution
        exec_report = scheduler.execute(plan)

        # If halted for human authorization
        if exec_report.status == "PAUSED_AWAITING_APPROVAL":
            self.memory.save_execution_checkpoint(
                tid,
                {
                    "plan": plan.model_dump(),
                    "report": exec_report.model_dump(),
                    "stage": "PAUSED_AWAITING_APPROVAL",
                },
                "PAUSED_AWAITING_APPROVAL",
            )
            self._emit("run_paused", {"task_id": tid, "step_id": exec_report.halted_step_id, "reason": exec_report.halt_reason})
            return AgentRunResult(
                task_id=tid,
                goal=goal,
                status="PAUSED_AWAITING_APPROVAL",
                plan=plan,
                execution_report=exec_report,
                policy_decisions=self.policy_guard.audit_decisions,
                human_approvals=self.policy_guard.get_approval_history(),
                halted_step_id=exec_report.halted_step_id,
                halt_reason=exec_report.halt_reason,
                total_time_ms=(time.time() - t_start) * 1000.0,
            )

        # If failed
        if exec_report.status == "FAILED":
            self.memory.save_execution_checkpoint(
                tid,
                {"plan": plan.model_dump(), "report": exec_report.model_dump(), "stage": "FAILED"},
                "FAILED",
            )
            self._emit("run_failed", {"task_id": tid, "reason": exec_report.halt_reason})
            return AgentRunResult(
                task_id=tid,
                goal=goal,
                status="FAILED",
                plan=plan,
                execution_report=exec_report,
                policy_decisions=self.policy_guard.audit_decisions,
                human_approvals=self.policy_guard.get_approval_history(),
                halted_step_id=exec_report.halted_step_id,
                halt_reason=exec_report.halt_reason,
                total_time_ms=(time.time() - t_start) * 1000.0,
            )

        # 4. VERIFY: Double-check ground truth & LLM-as-a-judge
        self._emit("verification_started", {"task_id": tid})
        verif_report = self.verifier.verify(exec_report)
        self._emit("verification_completed", {"task_id": tid, "verdict": verif_report.overall_verdict, "score": verif_report.confidence_score})

        # 5. COMPLETE: Generate Cryptographic Evidence Receipt
        self._emit("evidence_started", {"task_id": tid})
        receipt = self.evidence_gen.generate_receipt(
            report=exec_report,
            verification=verif_report,
            policy_decisions=self.policy_guard.audit_decisions,
            approvals=self.policy_guard.get_approval_history(),
        )
        # Export artifact receipt files
        self.evidence_gen.export_json(receipt)
        self.evidence_gen.export_markdown_dossier(receipt)
        self._emit("evidence_completed", {"task_id": tid, "signature": receipt.cryptographic_signature})

        # Save completed checkpoint
        self.memory.save_execution_checkpoint(
            tid,
            {
                "plan": plan.model_dump(),
                "report": exec_report.model_dump(),
                "verification": verif_report.model_dump(),
                "receipt": receipt.model_dump(),
                "stage": "COMPLETED",
            },
            "COMPLETED",
        )

        total_duration = (time.time() - t_start) * 1000.0
        self._emit("run_completed", {"task_id": tid, "total_time_ms": total_duration})

        return AgentRunResult(
            task_id=tid,
            goal=goal,
            status="COMPLETED",
            plan=plan,
            execution_report=exec_report,
            policy_decisions=self.policy_guard.audit_decisions,
            human_approvals=self.policy_guard.get_approval_history(),
            verification_report=verif_report,
            evidence_receipt=receipt,
            total_time_ms=total_duration,
        )

    def resume_run(
        self,
        task_id: str,
        approver_id: str = "VP_Finance_Human",
        approver_role: str = "finance_manager",
        comments: str = "Authorized after reviewing PO discrepancy.",
    ) -> AgentRunResult:
        """
        Resume execution of a halted task after recording human authorization.
        """
        t_start = time.time()
        checkpoint = self.memory.load_execution_checkpoint(task_id)
        if not checkpoint:
            raise ValueError(f"No execution checkpoint found for task ID '{task_id}'.")

        plan_data = checkpoint.get("plan")
        report_data = checkpoint.get("report")
        if not plan_data or not report_data:
            raise ValueError(f"Corrupted checkpoint for task ID '{task_id}'.")

        plan = DAGPlan.model_validate(plan_data)
        prev_report = DAGExecutionReport.model_validate(report_data)

        halted_step_id = prev_report.halted_step_id
        if not halted_step_id:
            raise ValueError("No halted step found to authorize.")

        # Grant human signature
        approval_record = self.policy_guard.grant_approval(
            step_id=halted_step_id,
            approver_id=approver_id,
            approver_role=approver_role,
            comments=comments,
        )
        self._emit("approval_granted", {"step_id": halted_step_id, "approver_id": approver_id})

        # Convert previous results, resetting the halted step to PENDING so it executes with approval
        restored_results: Dict[str, StepExecutionResult] = {}
        for s_id, s_res in prev_report.step_results.items():
            if s_id != halted_step_id and s_res.status == StepStatus.COMPLETED:
                restored_results[s_id] = s_res

        # Re-wire scheduler
        def _step_runner(step: TaskStep, params: Dict[str, Any]) -> StepExecutionResult:
            t0 = time.time()
            tool_res = self.tools.execute(step.tool, params)
            t1 = time.time()
            return StepExecutionResult(
                step_id=step.id,
                tool=step.tool,
                status=StepStatus.COMPLETED if tool_res.success else StepStatus.FAILED,
                output=tool_res.output,
                error=tool_res.error,
                artifacts=tool_res.artifacts,
                start_time=t0,
                end_time=t1,
                duration_ms=(t1 - t0) * 1000.0,
                idempotency_token=step.idempotency_token,
                metadata=tool_res.metadata,
            )

        def _policy_checker(step: TaskStep, params: Dict[str, Any]) -> Dict[str, Any]:
            decision = self.policy_guard.evaluate_step(step, params, actor_role=approver_role)
            return decision.model_dump()

        scheduler = DAGScheduler(
            max_workers=self.settings.MAX_PARALLEL_WORKERS,
            step_executor=_step_runner,
            policy_checker=_policy_checker,
        )
        for l in self.listeners:
            scheduler.add_listener(l)

        exec_report = scheduler.execute(plan, initial_results=restored_results)

        if exec_report.status == "PAUSED_AWAITING_APPROVAL":
            return AgentRunResult(
                task_id=task_id,
                goal=plan.goal,
                status="PAUSED_AWAITING_APPROVAL",
                plan=plan,
                execution_report=exec_report,
                policy_decisions=self.policy_guard.audit_decisions,
                human_approvals=self.policy_guard.get_approval_history(),
                halted_step_id=exec_report.halted_step_id,
                halt_reason=exec_report.halt_reason,
                total_time_ms=(time.time() - t_start) * 1000.0,
            )

        # Verify
        verif_report = self.verifier.verify(exec_report)
        # Evidence
        receipt = self.evidence_gen.generate_receipt(
            report=exec_report,
            verification=verif_report,
            policy_decisions=self.policy_guard.audit_decisions,
            approvals=self.policy_guard.get_approval_history(),
        )
        self.evidence_gen.export_json(receipt)
        self.evidence_gen.export_markdown_dossier(receipt)

        self.memory.save_execution_checkpoint(
            task_id,
            {
                "plan": plan.model_dump(),
                "report": exec_report.model_dump(),
                "verification": verif_report.model_dump(),
                "receipt": receipt.model_dump(),
                "stage": "COMPLETED",
            },
            "COMPLETED",
        )

        return AgentRunResult(
            task_id=task_id,
            goal=plan.goal,
            status="COMPLETED",
            plan=plan,
            execution_report=exec_report,
            policy_decisions=self.policy_guard.audit_decisions,
            human_approvals=self.policy_guard.get_approval_history(),
            verification_report=verif_report,
            evidence_receipt=receipt,
            total_time_ms=(time.time() - t_start) * 1000.0,
        )
