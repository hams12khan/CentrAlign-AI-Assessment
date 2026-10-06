"""
DAG Topological Scheduler & Concurrent Executor for CentrAlign AI.

Implements Kahn's algorithm for deterministic dependency resolution, cycle detection,
parallel wave execution, dynamic parameter passing, and Human-in-the-Loop pause/resume.
"""

import concurrent.futures
from enum import Enum
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set
from pydantic import BaseModel, Field
from runtime.planner import DAGPlan, TaskStep

logger = logging.getLogger(__name__)


class CyclicDependencyError(Exception):
    """Raised when Kahn's topological sort detects a cycle in the task graph."""
    pass


class StepStatus(str, Enum):
    """Status enumeration for an individual DAG step."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class StepExecutionResult(BaseModel):
    """Result of executing an individual task step."""

    step_id: str
    tool: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    artifacts: List[str] = Field(default_factory=list)
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    idempotency_token: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DAGExecutionReport(BaseModel):
    """Overall execution summary for a DAG run."""

    task_id: str
    goal: str
    status: str = "COMPLETED"  # COMPLETED, PAUSED_AWAITING_APPROVAL, FAILED
    step_results: Dict[str, StepExecutionResult] = Field(default_factory=dict)
    execution_order: List[str] = Field(default_factory=list)
    halted_step_id: Optional[str] = None
    halt_reason: Optional[str] = None
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    total_duration_ms: float = 0.0


class DAGScheduler:
    """
    Pure Python Kahn's Topological Sort Scheduler and Executor.
    Features parallel dispatch of independent steps and dynamic parameter interpolation.
    """

    def __init__(
        self,
        max_workers: int = 4,
        step_executor: Optional[Callable[[TaskStep, Dict[str, Any]], StepExecutionResult]] = None,
        policy_checker: Optional[Callable[[TaskStep, Dict[str, Any]], Dict[str, Any]]] = None,
    ):
        """
        :param max_workers: Maximum threads for concurrent independent steps.
        :param step_executor: Callable invoked to run a step: fn(step, resolved_params) -> StepExecutionResult.
        :param policy_checker: Optional pre-execution gate: fn(step, resolved_params) -> {approved: bool, reason: str}.
        """
        self.max_workers = max_workers
        self.step_executor = step_executor
        self.policy_checker = policy_checker
        self.listeners: List[Callable[[str, Dict[str, Any]], None]] = []

    def add_listener(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register observer callback for real-time progress events."""
        self.listeners.append(callback)

    def _notify(self, event_name: str, payload: Dict[str, Any]) -> None:
        for callback in self.listeners:
            try:
                callback(event_name, payload)
            except Exception as e:
                logger.error(f"Scheduler event listener error: {e}")

    def compute_topological_order(self, plan: DAGPlan) -> List[List[str]]:
        """
        Computes Kahn's topological sort organized into parallel execution waves.
        Each wave contains steps that can be run concurrently.
        Raises CyclicDependencyError if circular dependencies are detected.
        """
        steps = plan.steps
        step_ids = set(steps.keys())

        # In-degree calculation
        in_degree: Dict[str, int] = {s_id: len(step.dependencies) for s_id, step in steps.items()}
        # Adjacency: dependency -> list of children
        dependents: Dict[str, List[str]] = {s_id: [] for s_id in step_ids}

        for s_id, step in steps.items():
            for dep in step.dependencies:
                if dep not in step_ids:
                    raise ValueError(f"Step '{s_id}' depends on missing step '{dep}'.")
                dependents[dep].append(s_id)

        waves: List[List[str]] = []
        zero_in_degree = [s_id for s_id, deg in in_degree.items() if deg == 0]
        processed_count = 0

        while zero_in_degree:
            # All steps currently with in_degree == 0 form an independent wave
            current_wave = sorted(zero_in_degree)
            waves.append(current_wave)
            next_zero_in_degree: List[str] = []

            for node in current_wave:
                processed_count += 1
                for child in dependents[node]:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        next_zero_in_degree.append(child)

            zero_in_degree = next_zero_in_degree

        if processed_count != len(steps):
            cycle_nodes = [s_id for s_id, deg in in_degree.items() if deg > 0]
            raise CyclicDependencyError(
                f"Kahn's algorithm detected a cycle involving steps: {cycle_nodes}"
            )

        return waves

    def resolve_dynamic_params(
        self,
        raw_params: Dict[str, Any],
        completed_results: Dict[str, StepExecutionResult],
    ) -> Dict[str, Any]:
        """
        Resolves dynamic references like '$step_1.po_number' or '$step_1.data.ledger.tx_id'
        using outputs from previously completed steps.
        """
        resolved: Dict[str, Any] = {}

        def _extract_nested(src_step: str, path_segments: List[str]) -> Any:
            if src_step not in completed_results:
                return None
            step_res = completed_results[src_step]
            if not path_segments:
                return step_res.output

            first_seg = path_segments[0]
            curr: Any = None
            remaining = path_segments[1:]

            out = step_res.output
            meta = step_res.metadata

            if isinstance(out, dict) and first_seg in out:
                curr = out[first_seg]
            elif isinstance(meta, dict) and first_seg in meta:
                curr = meta[first_seg]
            elif first_seg == "output":
                curr = out
            elif first_seg == "metadata":
                curr = meta
            elif hasattr(step_res, first_seg):
                curr = getattr(step_res, first_seg)
            else:
                curr = out

            for seg in remaining:
                if curr is None:
                    break
                if isinstance(curr, dict) and seg in curr:
                    curr = curr[seg]
                elif isinstance(curr, (list, tuple)) and seg.isdigit():
                    idx = int(seg)
                    curr = curr[idx] if 0 <= idx < len(curr) else None
                elif hasattr(curr, seg):
                    curr = getattr(curr, seg)
                else:
                    return None
            return curr

        def _resolve_val(val: Any) -> Any:
            if isinstance(val, dict):
                return {k: _resolve_val(v) for k, v in val.items()}
            if isinstance(val, list):
                return [_resolve_val(item) for item in val]
            if isinstance(val, str) and "$" in val:
                # Direct exact reference, e.g. "$step_1.amount" or "$step_1.data.ledger.tx_id"
                exact_match = re.fullmatch(r"\$([a-zA-Z0-9_]+)((?:\.[a-zA-Z0-9_]+)+)", val.strip())
                if exact_match:
                    src_step = exact_match.group(1)
                    path = [p for p in exact_match.group(2).split(".") if p]
                    extracted = _extract_nested(src_step, path)
                    if extracted is not None:
                        return extracted
                    return val

                # Substring interpolation, e.g. "Order id: $step_1.po_id"
                def _repl(m: re.Match) -> str:
                    s_id = m.group(1)
                    path = [p for p in m.group(2).split(".") if p]
                    extracted = _extract_nested(s_id, path)
                    if extracted is not None:
                        return str(extracted)
                    return m.group(0)

                return re.sub(r"\$([a-zA-Z0-9_]+)((?:\.[a-zA-Z0-9_]+)+)", _repl, val)

            return val

        for k, v in raw_params.items():
            resolved[k] = _resolve_val(v)

        return resolved

    def execute(
        self,
        plan: DAGPlan,
        initial_results: Optional[Dict[str, StepExecutionResult]] = None,
    ) -> DAGExecutionReport:
        """
        Executes the plan using Kahn's topological sort and wave-based concurrency.
        Supports resume if initial_results are provided.
        """
        start_time = time.time()
        waves = self.compute_topological_order(plan)

        step_results: Dict[str, StepExecutionResult] = dict(initial_results or {})
        execution_order: List[str] = [s_id for s_id, res in step_results.items() if res.status == StepStatus.COMPLETED]

        self._notify("execution_started", {"task_id": plan.task_id, "waves": waves})

        for wave_idx, wave in enumerate(waves):
            # Filter steps in wave that are not yet completed
            pending_steps = [s_id for s_id in wave if s_id not in step_results or step_results[s_id].status != StepStatus.COMPLETED]
            if not pending_steps:
                continue

            self._notify("wave_started", {"wave_index": wave_idx, "steps": pending_steps})

            # Check policy guard for pending steps before execution
            for s_id in pending_steps:
                step = plan.steps[s_id]
                resolved_params = self.resolve_dynamic_params(step.params, step_results)

                if self.policy_checker:
                    policy_verdict = self.policy_checker(step, resolved_params)
                    if policy_verdict.get("verdict") == "AWAITING_HUMAN_APPROVAL":
                        halt_res = StepExecutionResult(
                            step_id=s_id,
                            tool=step.tool,
                            status=StepStatus.WAITING_FOR_APPROVAL,
                            error=policy_verdict.get("reason", "Awaiting human authorization."),
                            idempotency_token=step.idempotency_token,
                            metadata={"policy_decision": policy_verdict},
                        )
                        step_results[s_id] = halt_res
                        self._notify("step_halted_for_approval", {"step_id": s_id, "reason": policy_verdict.get("reason")})

                        return DAGExecutionReport(
                            task_id=plan.task_id,
                            goal=plan.goal,
                            status="PAUSED_AWAITING_APPROVAL",
                            step_results=step_results,
                            execution_order=execution_order,
                            halted_step_id=s_id,
                            halt_reason=policy_verdict.get("reason"),
                            start_time=start_time,
                            end_time=time.time(),
                            total_duration_ms=(time.time() - start_time) * 1000.0,
                        )

            # Execute wave steps (concurrently if multiple independent steps exist)
            if len(pending_steps) == 1:
                s_id = pending_steps[0]
                res = self._execute_single_step(plan.steps[s_id], step_results)
                step_results[s_id] = res
                execution_order.append(s_id)
                if res.status == StepStatus.FAILED:
                    return self._build_failed_report(plan, step_results, execution_order, start_time, s_id, res.error)
            else:
                # Parallel dispatch
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_workers, len(pending_steps))) as executor:
                    future_to_step = {
                        executor.submit(self._execute_single_step, plan.steps[s_id], step_results): s_id
                        for s_id in pending_steps
                    }
                    for future in concurrent.futures.as_completed(future_to_step):
                        s_id = future_to_step[future]
                        res = future.result()
                        step_results[s_id] = res
                        execution_order.append(s_id)
                        if res.status == StepStatus.FAILED:
                            return self._build_failed_report(plan, step_results, execution_order, start_time, s_id, res.error)

        end_time = time.time()
        self._notify("execution_completed", {"task_id": plan.task_id})
        return DAGExecutionReport(
            task_id=plan.task_id,
            goal=plan.goal,
            status="COMPLETED",
            step_results=step_results,
            execution_order=execution_order,
            start_time=start_time,
            end_time=end_time,
            total_duration_ms=(end_time - start_time) * 1000.0,
        )

    def _execute_single_step(
        self,
        step: TaskStep,
        step_results: Dict[str, StepExecutionResult],
    ) -> StepExecutionResult:
        """Execute a single step with retry handling and dynamic parameter resolution."""
        t_start = time.time()
        resolved_params = self.resolve_dynamic_params(step.params, step_results)
        self._notify("step_started", {"step_id": step.id, "tool": step.tool, "params": resolved_params})

        if not self.step_executor:
            # Fallback dummy execution
            return StepExecutionResult(
                step_id=step.id,
                tool=step.tool,
                status=StepStatus.COMPLETED,
                output={"executed": True, "params": resolved_params},
                start_time=t_start,
                end_time=time.time(),
                duration_ms=(time.time() - t_start) * 1000.0,
                idempotency_token=step.idempotency_token,
            )

        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                res = self.step_executor(step, resolved_params)
                res.retry_count = attempt
                res.idempotency_token = step.idempotency_token
                if res.status == StepStatus.FAILED:
                    last_error = res.error or "Step returned FAILED status"
                    if attempt < max_retries:
                        logger.warning(f"Step {step.id} attempt {attempt + 1} returned FAILED, retrying: {last_error}")
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    else:
                        self._notify("step_failed", {"step_id": step.id, "error": last_error})
                        return res
                self._notify("step_completed", {"step_id": step.id, "result": res.model_dump()})
                return res
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Step {step.id} attempt {attempt + 1} failed: {e}")
                time.sleep(0.05 * (attempt + 1))

        t_end = time.time()
        fail_res = StepExecutionResult(
            step_id=step.id,
            tool=step.tool,
            status=StepStatus.FAILED,
            error=last_error,
            start_time=t_start,
            end_time=t_end,
            duration_ms=(t_end - t_start) * 1000.0,
            retry_count=max_retries,
            idempotency_token=step.idempotency_token,
        )
        self._notify("step_failed", {"step_id": step.id, "error": last_error})
        return fail_res

    def _build_failed_report(
        self,
        plan: DAGPlan,
        step_results: Dict[str, StepExecutionResult],
        execution_order: List[str],
        start_time: float,
        failed_step_id: str,
        error_msg: Optional[str],
    ) -> DAGExecutionReport:
        end_time = time.time()
        return DAGExecutionReport(
            task_id=plan.task_id,
            goal=plan.goal,
            status="FAILED",
            step_results=step_results,
            execution_order=execution_order,
            halted_step_id=failed_step_id,
            halt_reason=f"Step failed with error: {error_msg}",
            start_time=start_time,
            end_time=end_time,
            total_duration_ms=(end_time - start_time) * 1000.0,
        )
