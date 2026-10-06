"""
CentrAlign AI - Autonomous AI Employee Runtime.

This package provides a production-grade autonomous digital worker engine
featuring Kahn's DAG topological scheduling, pre-execution RBAC policy guardrails,
hybrid enterprise tool orchestration (SQLite, DuckDB, Playwright, Sandboxed Files),
deterministic outcome verification, and cryptographic execution evidence receipts.
"""

from runtime.config import RuntimeSettings, get_settings
from runtime.llm_provider import UnifiedLLMProvider, get_llm_provider
from runtime.memory import EnterpriseMemory, SOPDocument, PolicyRule
from runtime.planner import DAGPlanner, DAGPlan, TaskStep
from runtime.scheduler import DAGScheduler, StepExecutionResult, DAGExecutionReport
from runtime.policy_guard import PolicyGuard, PolicyDecision, ApprovalRecord
from runtime.verifier import OutcomeVerifier, VerificationReport
from runtime.evidence import EvidenceGenerator, EvidenceReceipt
from runtime.agent import AutonomousAIEmployee, AgentRunResult

__all__ = [
    "RuntimeSettings",
    "get_settings",
    "UnifiedLLMProvider",
    "get_llm_provider",
    "EnterpriseMemory",
    "SOPDocument",
    "PolicyRule",
    "DAGPlanner",
    "DAGPlan",
    "TaskStep",
    "DAGScheduler",
    "StepExecutionResult",
    "DAGExecutionReport",
    "PolicyGuard",
    "PolicyDecision",
    "ApprovalRecord",
    "OutcomeVerifier",
    "VerificationReport",
    "EvidenceGenerator",
    "EvidenceReceipt",
    "AutonomousAIEmployee",
    "AgentRunResult",
]
