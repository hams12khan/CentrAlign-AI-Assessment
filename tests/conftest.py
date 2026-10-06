"""
Shared pytest fixtures and offline mock environments for CentrAlign AI.

Ensures 100% offline, zero-network, isolated test execution with temporary directories.
"""

from pathlib import Path
import pytest
from runtime.agent import AutonomousAIEmployee
from runtime.config import RuntimeSettings
from runtime.evidence import EvidenceGenerator
from runtime.llm_provider import MockLLMProvider
from runtime.memory import EnterpriseMemory
from runtime.policy_guard import PolicyGuard
from runtime.tools import (
    BrowserTool,
    DatabaseQueryTool,
    DatabaseUpdateTool,
    DuckDBAnalyticsTool,
    EvaluateDiscrepancyTool,
    FileReadTool,
    FileWriteTool,
    ListDirectoryTool,
    ToolRegistry,
    seed_enterprise_databases,
)
from runtime.verifier import OutcomeVerifier


@pytest.fixture
def test_settings(tmp_path: Path) -> RuntimeSettings:
    """Fixture providing isolated temporary directories for all runtime paths."""
    storage_dir = tmp_path / "storage"
    sandbox_dir = storage_dir / "sandbox"
    artifact_dir = storage_dir / "artifacts"
    db_dir = storage_dir / "data"

    sqlite_path = db_dir / "test_enterprise_erp.db"
    duckdb_path = db_dir / "test_analytics.duckdb"

    settings = RuntimeSettings(
        LLM_PROVIDER="mock",
        BASE_DIR=tmp_path,
        STORAGE_DIR=storage_dir,
        SANDBOX_ROOT=sandbox_dir,
        ARTIFACT_DIR=artifact_dir,
        DATABASE_DIR=db_dir,
        SQLITE_DB_PATH=sqlite_path,
        DUCKDB_PATH=duckdb_path,
        APPROVAL_THRESHOLD_AMOUNT=1000.0,
        DISCREPANCY_TOLERANCE=50.0,
        MAX_RETRIES_PER_STEP=2,
        MAX_PARALLEL_WORKERS=4,
    )
    settings.ensure_directories()
    return settings


@pytest.fixture
def mock_llm() -> MockLLMProvider:
    """Fixture providing deterministic offline LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def seeded_test_db(test_settings: RuntimeSettings) -> Path:
    """Fixture initializing temporary SQLite and DuckDB databases."""
    seed_enterprise_databases(
        sqlite_path=test_settings.SQLITE_DB_PATH,
        duckdb_path=test_settings.DUCKDB_PATH,
        force_reseed=True,
    )
    return test_settings.SQLITE_DB_PATH


@pytest.fixture
def test_memory(test_settings: RuntimeSettings, seeded_test_db: Path) -> EnterpriseMemory:
    """Fixture providing isolated EnterpriseMemory instance."""
    mem_path = test_settings.DATABASE_DIR / "test_memory.db"
    return EnterpriseMemory(db_path=mem_path, settings=test_settings)


@pytest.fixture
def test_tools(test_settings: RuntimeSettings, seeded_test_db: Path) -> ToolRegistry:
    """Fixture providing enterprise tool registry bound to temporary test environment."""
    registry = ToolRegistry()
    registry.register(DatabaseQueryTool(db_path=test_settings.SQLITE_DB_PATH))
    registry.register(DatabaseUpdateTool(db_path=test_settings.SQLITE_DB_PATH))
    registry.register(
        DuckDBAnalyticsTool(
            sqlite_path=test_settings.SQLITE_DB_PATH,
            duckdb_path=test_settings.DUCKDB_PATH,
        )
    )
    registry.register(EvaluateDiscrepancyTool())
    registry.register(FileReadTool(sandbox_root=test_settings.SANDBOX_ROOT))
    registry.register(FileWriteTool(sandbox_root=test_settings.SANDBOX_ROOT))
    registry.register(ListDirectoryTool(sandbox_root=test_settings.SANDBOX_ROOT))
    registry.register(BrowserTool(artifacts_dir=test_settings.ARTIFACT_DIR))
    return registry


@pytest.fixture
def test_policy_guard(test_memory: EnterpriseMemory, test_settings: RuntimeSettings) -> PolicyGuard:
    """Fixture providing isolated PolicyGuard instance."""
    return PolicyGuard(memory=test_memory, settings=test_settings)


@pytest.fixture
def test_verifier(test_settings: RuntimeSettings, mock_llm: MockLLMProvider) -> OutcomeVerifier:
    """Fixture providing OutcomeVerifier bound to test database and mock LLM."""
    return OutcomeVerifier(
        sqlite_path=test_settings.SQLITE_DB_PATH,
        llm_client=mock_llm,
        settings=test_settings,
    )


@pytest.fixture
def test_evidence_gen(test_settings: RuntimeSettings) -> EvidenceGenerator:
    """Fixture providing EvidenceGenerator bound to temporary artifacts directory."""
    return EvidenceGenerator(
        artifacts_dir=test_settings.ARTIFACT_DIR,
        settings=test_settings,
    )


@pytest.fixture
def test_agent(
    test_settings: RuntimeSettings,
    mock_llm: MockLLMProvider,
    test_memory: EnterpriseMemory,
    test_tools: ToolRegistry,
    test_policy_guard: PolicyGuard,
    test_verifier: OutcomeVerifier,
    test_evidence_gen: EvidenceGenerator,
) -> AutonomousAIEmployee:
    """Fixture providing fully-wired AutonomousAIEmployee runtime."""
    return AutonomousAIEmployee(
        settings=test_settings,
        llm=mock_llm,
        memory=test_memory,
        tools=test_tools,
        policy_guard=test_policy_guard,
        verifier=test_verifier,
        evidence_gen=test_evidence_gen,
    )
