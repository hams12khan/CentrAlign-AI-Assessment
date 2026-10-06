"""
Abstract Tool Interface and Schema Registry for CentrAlign AI.

Defines the standard contract for enterprise tools, parameter validation,
risk categorization, and execution outcome structures.
"""

import abc
import time
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Normalized result returned by any enterprise tool execution."""

    success: bool
    output: Any = None
    error: Optional[str] = None
    artifacts: List[str] = Field(default_factory=list, description="File paths or visual screenshots created")
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(abc.ABC):
    """Abstract base class for all autonomous employee tools."""

    name: str
    description: str
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    is_read_only: bool = True

    @abc.abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute tool action with provided keyword arguments.

        :return: Standardized ToolResult instance.
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema descriptor for tool parameters."""
        return {
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level,
            "is_read_only": self.is_read_only,
        }


class ToolRegistry:
    """Central registry of executable enterprise tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name.lower()] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Lookup tool by name (case-insensitive)."""
        return self._tools.get(name.lower())

    def has(self, name: str) -> bool:
        """Check if tool name is registered."""
        return name.lower() in self._tools

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return metadata for all registered tools."""
        return [tool.get_schema() for tool in self._tools.values()]

    def execute(self, name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with automatic timing."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' is not registered in the tool registry.",
                execution_time_ms=0.0,
            )

        t_start = time.time()
        try:
            result = tool.execute(**params)
            result.execution_time_ms = (time.time() - t_start) * 1000.0
            return result
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - t_start) * 1000.0,
            )
