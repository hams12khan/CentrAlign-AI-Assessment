"""
Sandboxed File Tool for CentrAlign AI.

Enforces strict path containment within the sandbox directory to prevent directory traversal.
Generates structured audit logs, computes cryptographic SHA-256 hashes, and handles
JSON, Markdown, and tabular text manipulation.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from runtime.config import RuntimeSettings, get_settings
from runtime.tools.base import BaseTool, ToolResult


class SandboxSecurityViolation(Exception):
    """Raised when an operation attempts to break out of the designated sandbox."""
    pass


class FileSandboxHelper:
    """Utility for path canonicalization and sandbox containment validation."""

    def __init__(self, sandbox_root: Optional[Path] = None):
        self.sandbox_root = (sandbox_root or get_settings().SANDBOX_ROOT).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def resolve_safe_path(self, relative_or_abs_path: str) -> Path:
        """
        Resolve path and ensure it remains strictly contained within sandbox_root.
        Raises SandboxSecurityViolation if path traversal is detected.
        """
        # Strip leading slashes to prevent absolute root escapes if treated as relative
        clean_path = relative_or_abs_path.strip().lstrip("/\\")
        candidate = (self.sandbox_root / clean_path).resolve()

        try:
            candidate.relative_to(self.sandbox_root)
        except ValueError:
            raise SandboxSecurityViolation(
                f"Path traversal detected! Path '{relative_or_abs_path}' resolves outside sandbox '{self.sandbox_root}'."
            )

        return candidate

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Calculate SHA-256 digest of a file for tamper evidence."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


class FileReadTool(BaseTool):
    """Safely reads files from the isolated sandbox environment."""

    name = "file_read"
    description = "Read file contents (JSON, Markdown, CSV, plain text) from the sandbox."
    risk_level = "LOW"
    is_read_only = True

    def __init__(self, sandbox_root: Optional[Path] = None):
        self.helper = FileSandboxHelper(sandbox_root)

    def execute(self, file_path: str, **kwargs) -> ToolResult:
        try:
            target = self.helper.resolve_safe_path(file_path)
            if not target.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found in sandbox: '{file_path}'",
                )

            content = target.read_text(encoding="utf-8")
            sha256 = self.helper.compute_sha256(target)

            # Try parsing as JSON if possible
            parsed_data = None
            if target.suffix.lower() == ".json":
                try:
                    parsed_data = json.loads(content)
                except json.JSONDecodeError:
                    pass

            output_payload = parsed_data if parsed_data is not None else content

            # Flatten output dictionary with file content fields if parsed
            if isinstance(parsed_data, dict):
                output_dict = dict(parsed_data)
                output_dict["_raw_content"] = content
                output_dict["_sha256"] = sha256
                output_payload = output_dict

            return ToolResult(
                success=True,
                output=output_payload,
                artifacts=[str(target)],
                metadata={"sha256": sha256, "size_bytes": target.stat().st_size},
            )
        except SandboxSecurityViolation as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"File read error: {str(e)}")


class FileWriteTool(BaseTool):
    """Safely writes documents and audit reports into the isolated sandbox."""

    name = "file_write"
    description = "Write text, JSON, or markdown documents into the isolated sandbox."
    risk_level = "LOW"
    is_read_only = False

    def __init__(self, sandbox_root: Optional[Path] = None):
        self.helper = FileSandboxHelper(sandbox_root)

    def execute(self, file_path: str, content: Any, **kwargs) -> ToolResult:
        try:
            target = self.helper.resolve_safe_path(file_path)
            target.parent.mkdir(parents=True, exist_ok=True)

            text_content = content
            if isinstance(content, (dict, list)):
                text_content = json.dumps(content, indent=2)

            target.write_text(str(text_content), encoding="utf-8")
            sha256 = self.helper.compute_sha256(target)

            return ToolResult(
                success=True,
                output={
                    "written_path": str(target),
                    "size_bytes": target.stat().st_size,
                    "sha256": sha256,
                },
                artifacts=[str(target)],
                metadata={"sha256": sha256, "path": str(target)},
            )
        except SandboxSecurityViolation as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"File write error: {str(e)}")


class ListDirectoryTool(BaseTool):
    """Enumerates directory contents inside the sandbox."""

    name = "list_directory"
    description = "List all files and subdirectories located within a sandbox folder."
    risk_level = "LOW"
    is_read_only = True

    def __init__(self, sandbox_root: Optional[Path] = None):
        self.helper = FileSandboxHelper(sandbox_root)

    def execute(self, dir_path: str = "", **kwargs) -> ToolResult:
        try:
            target = self.helper.resolve_safe_path(dir_path)
            if not target.exists():
                return ToolResult(success=False, error=f"Directory '{dir_path}' does not exist.")

            entries = []
            for item in target.iterdir():
                entries.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size_bytes": item.stat().st_size if item.is_file() else 0,
                })

            return ToolResult(success=True, output=entries)
        except SandboxSecurityViolation as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"List directory error: {str(e)}")
