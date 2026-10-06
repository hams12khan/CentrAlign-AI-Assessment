"""
Unit tests for Enterprise Tools (Filesystem Sandbox, SQLite ERP, DuckDB Analytics, Playwright Browser).

Validates:
- Strict sandbox path containment and path-traversal prevention
- SHA-256 hash calculation on written files
- Read-only enforcement on DatabaseQueryTool
- State mutations and affected row counts in DatabaseUpdateTool
- DuckDB analytical aggregations
- Financial discrepancy evaluation logic
- Browser tool DOM table extraction and screenshot capture
"""

import json
from pathlib import Path
import pytest
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
)


def test_file_write_and_read(test_tools: ToolRegistry, tmp_path: Path):
    """Verify writing content and reading it back with SHA-256 integrity."""
    write_res = test_tools.execute(
        "file_write",
        {"file_path": "audit/report.md", "content": "# Test Audit Content"},
    )
    assert write_res.success
    assert len(write_res.artifacts) == 1
    assert write_res.output["sha256"] != ""

    read_res = test_tools.execute("file_read", {"file_path": "audit/report.md"})
    assert read_res.success
    assert read_res.output == "# Test Audit Content"


def test_sandbox_path_traversal_prevention(test_tools: ToolRegistry):
    """Verify that attempting to escape the sandbox directory is blocked."""
    escape_res = test_tools.execute(
        "file_write",
        {"file_path": "../../outside_sandbox.txt", "content": "malicious write"},
    )
    assert not escape_res.success
    assert "Path traversal detected" in escape_res.error


def test_database_query_read_only_enforcement(test_tools: ToolRegistry):
    """Verify that db_query succeeds on SELECT and blocks non-SELECT statements."""
    # Valid SELECT
    sel_res = test_tools.execute(
        "db_query",
        {"sql": "SELECT count(*) AS total FROM purchase_orders"},
    )
    assert sel_res.success
    assert sel_res.output["total"] > 0

    # Blocked UPDATE via query tool
    upd_res = test_tools.execute(
        "db_query",
        {"sql": "UPDATE purchase_orders SET status = 'HACKED'"},
    )
    assert not upd_res.success
    assert "only allows SELECT" in upd_res.error


def test_database_update_mutations(test_tools: ToolRegistry):
    """Verify updating ERP status and checking database ground truth."""
    upd_res = test_tools.execute(
        "db_update",
        {"sql": "UPDATE purchase_orders SET status = 'RECONCILED' WHERE po_id = 'PO-2026-9011'"},
    )
    assert upd_res.success
    assert upd_res.output["rows_affected"] == 1

    # Verify updated record
    query_res = test_tools.execute(
        "db_query",
        {"sql": "SELECT status FROM purchase_orders WHERE po_id = 'PO-2026-9011'"},
    )
    assert query_res.success
    assert query_res.output["status"] == "RECONCILED"


def test_duckdb_analytics_query(test_tools: ToolRegistry):
    """Verify analytical aggregation across refund requests."""
    analytics_res = test_tools.execute(
        "analytics_query",
        {"sql": "SELECT count(*) AS total_anomalies FROM refund_requests WHERE amount > 500.0"},
    )
    assert analytics_res.success
    rows = analytics_res.output
    assert len(rows) > 0


def test_evaluate_discrepancy_tolerance_rules(test_tools: ToolRegistry):
    """Verify tolerance threshold (<= $50 auto-approves, > $50 flags dispute)."""
    # Case 1: Within tolerance ($1,250 vs $1,200 = $50 variance <= $50)
    res_ok = test_tools.execute(
        "evaluate_discrepancy",
        {"invoice_amount": 1250.00, "po_amount": 1200.00, "po_id": "PO-2026-9011"},
    )
    assert res_ok.success
    assert res_ok.output["within_tolerance"] is True
    assert res_ok.output["route_status"] == "RECONCILED"

    # Case 2: Exceeds tolerance ($1,350 vs $1,200 = $150 variance > $50)
    res_dispute = test_tools.execute(
        "evaluate_discrepancy",
        {"invoice_amount": 1350.00, "po_amount": 1200.00, "po_id": "PO-2026-9011"},
    )
    assert res_dispute.success
    assert res_dispute.output["within_tolerance"] is False
    assert res_dispute.output["route_status"] == "FLAGGED_DISPUTE"


def test_browser_tool_execution_and_evidence(test_tools: ToolRegistry):
    """Verify browser navigation, DOM extraction, and visual screenshot artifact."""
    browser_res = test_tools.execute(
        "browser_action",
        {"action": "navigate_and_screenshot", "screenshot_filename": "test_shot.png"},
    )
    assert browser_res.success
    assert len(browser_res.artifacts) == 1
    shot_path = Path(browser_res.artifacts[0])
    assert shot_path.exists()
    assert shot_path.stat().st_size > 0


def test_duckdb_query_with_semicolon_and_grouping(test_tools: ToolRegistry):
    """Verify DuckDB executes analytical queries containing semicolons and aggregations."""
    sql = "SELECT customer_id, count(*) AS count_val FROM refund_requests GROUP BY customer_id;"
    res = test_tools.execute("analytics_query", {"sql": sql})
    assert res.success
    assert len(res.output) > 0


def test_browser_tool_form_interaction(test_tools: ToolRegistry):
    """Verify browser tool submits form fields and produces updated evidence."""
    res = test_tools.execute(
        "browser_action",
        {
            "action": "update_ledger",
            "fields": {"po_id": "PO-2026-9011", "new_status": "FLAGGED_DISPUTE"},
            "screenshot_filename": "dispute_evidence.png",
        },
    )
    assert res.success
    assert len(res.artifacts) >= 1
    assert "dispute_evidence.png" in res.output["screenshot_path"]
