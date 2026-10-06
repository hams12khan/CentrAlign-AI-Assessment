"""
Enterprise Tool Registry and Tools for CentrAlign AI.
"""

from runtime.tools.base import BaseTool, ToolRegistry, ToolResult
from runtime.tools.browser_tool import BrowserTool
from runtime.tools.db_tool import (
    DatabaseQueryTool,
    DatabaseUpdateTool,
    DuckDBAnalyticsTool,
    EvaluateDiscrepancyTool,
    seed_enterprise_databases,
)
from runtime.tools.file_tool import (
    FileReadTool,
    FileWriteTool,
    ListDirectoryTool,
    SandboxSecurityViolation,
)


def create_default_tool_registry() -> ToolRegistry:
    """Create and return a fully wired enterprise tool registry."""
    # Ensure databases are seeded
    seed_enterprise_databases()

    registry = ToolRegistry()
    registry.register(DatabaseQueryTool())
    registry.register(DatabaseUpdateTool())
    registry.register(DuckDBAnalyticsTool())
    registry.register(EvaluateDiscrepancyTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(ListDirectoryTool())
    registry.register(BrowserTool())
    return registry


__all__ = [
    "BaseTool",
    "ToolRegistry",
    "ToolResult",
    "DatabaseQueryTool",
    "DatabaseUpdateTool",
    "DuckDBAnalyticsTool",
    "EvaluateDiscrepancyTool",
    "FileReadTool",
    "FileWriteTool",
    "ListDirectoryTool",
    "BrowserTool",
    "SandboxSecurityViolation",
    "seed_enterprise_databases",
    "create_default_tool_registry",
]
