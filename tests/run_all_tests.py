"""
Standalone automated test runner for CentrAlign AI Autonomous Runtime.

Executes all test suites across the repository and outputs a structured summary.
Usage:
    python tests/run_all_tests.py
"""

import os
from pathlib import Path
import sys
import pytest

# Ensure project root is in sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Also add workspace root if different
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


def run_tests() -> int:
    """Run full pytest suite programmatically."""
    args = [
        "-v",
        "--tb=short",
        str(CURRENT_DIR),
    ]
    print(f"[*] Running CentrAlign AI Test Suite from: {CURRENT_DIR}")
    exit_code = pytest.main(args)
    return int(exit_code)


if __name__ == "__main__":
    code = run_tests()
    sys.exit(code)
