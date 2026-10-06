"""
Runtime Configuration and Settings Management for CentrAlign AI.

Utilizes Pydantic v2 BaseSettings with automatic environment variable loading,
sensible defaults for offline deterministic testing, and sandbox directory isolation.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """
    Enterprise runtime configuration.

    Supports zero-cost offline mock operation out-of-the-box, as well as live
    free-tier integrations with Groq and Google Gemini Flash.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Configuration
    LLM_PROVIDER: Literal["mock", "groq", "gemini", "ollama"] = Field(
        default="mock",
        description="Active LLM backend. Defaults to 'mock' for 100% offline deterministic execution.",
    )
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        description="Free-tier Groq API key for Llama 3 models.",
    )
    GROQ_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq primary model identifier.",
    )
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Free-tier Google Generative AI key for Gemini Flash models.",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-1.5-flash",
        description="Gemini primary model identifier.",
    )
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Local Ollama daemon endpoint.",
    )
    OLLAMA_MODEL: str = Field(
        default="llama3",
        description="Local Ollama model identifier.",
    )

    # Directory Paths & Sandbox Isolation
    BASE_DIR: Path = Field(
        default_factory=lambda: Path(os.getcwd()).resolve(),
        description="Base project root directory.",
    )
    STORAGE_DIR: Path = Field(
        default_factory=lambda: Path(os.getcwd()).resolve() / "storage",
        description="Root directory for local state persistence and artifacts.",
    )
    SANDBOX_ROOT: Path = Field(
        default_factory=lambda: Path(os.getcwd()).resolve() / "storage" / "sandbox",
        description="Strictly isolated directory for file manipulation by tools.",
    )
    ARTIFACT_DIR: Path = Field(
        default_factory=lambda: Path(os.getcwd()).resolve() / "storage" / "artifacts",
        description="Directory for execution receipts, visual screenshots, and audit trails.",
    )
    DATABASE_DIR: Path = Field(
        default_factory=lambda: Path(os.getcwd()).resolve() / "storage" / "data",
        description="Directory for SQLite ERP and DuckDB analytics databases.",
    )
    SQLITE_DB_PATH: Path = Field(
        default_factory=lambda: Path(os.getcwd()).resolve() / "storage" / "data" / "enterprise_erp.db",
        description="SQLite database path for transactional ERP/CRM records.",
    )
    DUCKDB_PATH: Path = Field(
        default_factory=lambda: Path(os.getcwd()).resolve() / "storage" / "data" / "analytics.duckdb",
        description="DuckDB database path for high-throughput analytical ledger queries.",
    )

    # Enterprise Policy & HITL Governance Thresholds
    APPROVAL_THRESHOLD_AMOUNT: float = Field(
        default=1000.0,
        description="Dollar threshold above which state mutations require Human-in-the-Loop authorization.",
    )
    DISCREPANCY_TOLERANCE: float = Field(
        default=50.0,
        description="Threshold in dollars for autonomous reconciliation before human flagging.",
    )
    MAX_RETRIES_PER_STEP: int = Field(
        default=2,
        description="Maximum automatic retries allowed for an individual failed DAG step.",
    )
    MAX_PARALLEL_WORKERS: int = Field(
        default=4,
        description="Max concurrency level for independent DAG steps in topological executor.",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Runtime logging verbosity level.",
    )
    DEFAULT_ROLE: str = Field(
        default="ai_operator",
        description="Default role assigned to the autonomous worker agent.",
    )
    PORTAL_PORT: int = Field(
        default=8765,
        description="Port for mock enterprise portal HTTP server.",
    )

    def ensure_directories(self) -> None:
        """Create storage, sandbox, artifact, and database directories if they do not exist."""
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
        self.ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        self.DATABASE_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> RuntimeSettings:
    """
    Retrieve cached runtime settings instance.
    Automatically initializes storage folders.
    """
    settings = RuntimeSettings()
    settings.ensure_directories()
    return settings
