"""
Unit tests for Kahn's Algorithm DAG Scheduler and Executor.

Validates:
- Topological sorting correctness
- Cycle detection (CyclicDependencyError)
- Parallel wave execution of independent steps
- Dynamic parameter resolution between dependent steps
- Error handling and retry count tracking
"""

import time
import pytest
from runtime.planner import DAGPlan, TaskStep
from runtime.scheduler import (
    CyclicDependencyError,
    DAGScheduler,
    StepExecutionResult,
    StepStatus,
)


def test_topological_sort_linear():
    """Verify linear dependency chain sorting order."""
    steps = {
        "step_1": TaskStep(id="step_1", tool="dummy", dependencies=[]),
        "step_2": TaskStep(id="step_2", tool="dummy", dependencies=["step_1"]),
        "step_3": TaskStep(id="step_3", tool="dummy", dependencies=["step_2"]),
    }
    plan = DAGPlan(task_id="t1", goal="linear test", steps=steps)
    scheduler = DAGScheduler()
    waves = scheduler.compute_topological_order(plan)

    assert len(waves) == 3
    assert waves[0] == ["step_1"]
    assert waves[1] == ["step_2"]
    assert waves[2] == ["step_3"]


def test_topological_sort_parallel_branches():
    """Verify that independent branches form a single parallel wave."""
    # step_1 -> step_2, step_3 -> step_4
    steps = {
        "step_1": TaskStep(id="step_1", tool="dummy", dependencies=[]),
        "step_2": TaskStep(id="step_2", tool="dummy", dependencies=["step_1"]),
        "step_3": TaskStep(id="step_3", tool="dummy", dependencies=["step_1"]),
        "step_4": TaskStep(id="step_4", tool="dummy", dependencies=["step_2", "step_3"]),
    }
    plan = DAGPlan(task_id="t2", goal="branching test", steps=steps)
    scheduler = DAGScheduler()
    waves = scheduler.compute_topological_order(plan)

    assert len(waves) == 3
    assert waves[0] == ["step_1"]
    assert sorted(waves[1]) == ["step_2", "step_3"]
    assert waves[2] == ["step_4"]


def test_cycle_detection_raises_cyclic_dependency_error():
    """Verify that circular dependencies raise CyclicDependencyError."""
    # step_1 -> step_2 -> step_3 -> step_1
    steps = {
        "step_1": TaskStep(id="step_1", tool="dummy", dependencies=["step_3"]),
        "step_2": TaskStep(id="step_2", tool="dummy", dependencies=["step_1"]),
        "step_3": TaskStep(id="step_3", tool="dummy", dependencies=["step_2"]),
    }
    plan = DAGPlan(task_id="t_cycle", goal="cycle test", steps=steps)
    scheduler = DAGScheduler()

    with pytest.raises(CyclicDependencyError) as exc_info:
        scheduler.compute_topological_order(plan)

    assert "cycle" in str(exc_info.value).lower()


def test_dynamic_param_resolution():
    """Verify resolving $step_1.val into dependent step parameters."""
    scheduler = DAGScheduler()
    completed = {
        "step_1": StepExecutionResult(
            step_id="step_1",
            tool="test_tool",
            status=StepStatus.COMPLETED,
            output={"po_number": "PO-9999", "amount": 1250.50},
        )
    }

    raw_params = {
        "target_po": "$step_1.po_number",
        "value": "$step_1.amount",
        "formatted_msg": "Discrepancy detected for order $step_1.po_number with total $step_1.amount",
        "nested": {"inner_po": "$step_1.po_number"},
    }

    resolved = scheduler.resolve_dynamic_params(raw_params, completed)

    assert resolved["target_po"] == "PO-9999"
    assert resolved["value"] == 1250.50
    assert "Discrepancy detected for order PO-9999 with total 1250.5" in resolved["formatted_msg"]
    assert resolved["nested"]["inner_po"] == "PO-9999"


def test_parallel_execution_timing():
    """Verify that independent wave steps execute concurrently in ThreadPoolExecutor."""
    def _slow_executor(step: TaskStep, params: dict) -> StepExecutionResult:
        time.sleep(0.1)  # 100ms
        return StepExecutionResult(
            step_id=step.id,
            tool=step.tool,
            status=StepStatus.COMPLETED,
            output={"done": True},
        )

    # 3 independent steps
    steps = {
        "step_a": TaskStep(id="step_a", tool="dummy", dependencies=[]),
        "step_b": TaskStep(id="step_b", tool="dummy", dependencies=[]),
        "step_c": TaskStep(id="step_c", tool="dummy", dependencies=[]),
    }
    plan = DAGPlan(task_id="t_parallel", goal="parallel timing test", steps=steps)
    scheduler = DAGScheduler(max_workers=3, step_executor=_slow_executor)

    t0 = time.time()
    report = scheduler.execute(plan)
    elapsed = time.time() - t0

    assert report.status == "COMPLETED"
    # If sequential: 300ms. If concurrent: around 100-200ms.
    assert elapsed < 0.28, f"Expected concurrent execution under 280ms, took {elapsed * 1000:.1f}ms"


def test_scheduler_retry_on_transient_failure():
    """Verify that DAGScheduler retries on StepStatus.FAILED before succeeding."""
    call_counts = {"count": 0}

    def _flaky_executor(step: TaskStep, params: dict) -> StepExecutionResult:
        call_counts["count"] += 1
        if call_counts["count"] == 1:
            return StepExecutionResult(
                step_id=step.id,
                tool=step.tool,
                status=StepStatus.FAILED,
                error="Transient network timeout",
            )
        return StepExecutionResult(
            step_id=step.id,
            tool=step.tool,
            status=StepStatus.COMPLETED,
            output={"recovered": True},
        )

    step = TaskStep(id="step_flaky", tool="dummy", dependencies=[])
    plan = DAGPlan(task_id="t_flaky", goal="retry test", steps={"step_flaky": step})
    scheduler = DAGScheduler(step_executor=_flaky_executor)

    report = scheduler.execute(plan)
    assert report.status == "COMPLETED"
    assert report.step_results["step_flaky"].status == StepStatus.COMPLETED
    assert report.step_results["step_flaky"].retry_count == 1
    assert call_counts["count"] == 2


def test_deep_nested_dynamic_param_resolution():
    """Verify resolving multi-level dot paths and list indexes."""
    scheduler = DAGScheduler()
    completed = {
        "step_1": StepExecutionResult(
            step_id="step_1",
            tool="test_tool",
            status=StepStatus.COMPLETED,
            output={
                "data": {
                    "ledger": {
                        "tx_id": "TX-9988",
                        "items": [{"sku": "A1", "price": 49.99}],
                    }
                }
            },
            metadata={"variance_info": {"gap": 12.50}},
        )
    }

    raw = {
        "tx": "$step_1.data.ledger.tx_id",
        "first_sku": "$step_1.data.ledger.items.0.sku",
        "first_price": "$step_1.data.ledger.items.0.price",
        "gap": "$step_1.variance_info.gap",
    }
    resolved = scheduler.resolve_dynamic_params(raw, completed)

    assert resolved["tx"] == "TX-9988"
    assert resolved["first_sku"] == "A1"
    assert resolved["first_price"] == 49.99
    assert resolved["gap"] == 12.50
