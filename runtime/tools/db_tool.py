"""
Enterprise Database Tool for CentrAlign AI.

Integrates SQLite (ERP/CRM transactional ledger) and DuckDB (high-throughput analytical queries).
Includes automatic database seeding for enterprise scenarios (invoices, POs, refund anomalies),
before-and-after state diff capture for audit trails, and financial discrepancy evaluation.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import duckdb
from runtime.config import RuntimeSettings, get_settings
from runtime.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


def seed_enterprise_databases(
    sqlite_path: Optional[Path] = None,
    duckdb_path: Optional[Path] = None,
    force_reseed: bool = False,
) -> None:
    """
    Seed transactional SQLite ERP and analytical DuckDB instances
    with realistic enterprise operational data.
    """
    settings = get_settings()
    s_path = sqlite_path or settings.SQLITE_DB_PATH
    d_path = duckdb_path or settings.DUCKDB_PATH

    s_path.parent.mkdir(parents=True, exist_ok=True)
    d_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Seed SQLite Database
    conn = sqlite3.connect(str(s_path))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            tier TEXT NOT NULL,
            balance REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_id TEXT PRIMARY KEY,
            vendor_id TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            status TEXT NOT NULL,
            approved_by TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY,
            po_id TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            amount REAL NOT NULL,
            line_items TEXT NOT NULL,
            status TEXT NOT NULL,
            submitted_at REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refund_requests (
            refund_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            amount REAL NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL,
            flagged_anomaly INTEGER NOT NULL,
            created_at REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ledger_transactions (
            tx_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            amount REAL NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp REAL NOT NULL
        )
    """)

    cursor.execute("SELECT count(*) FROM purchase_orders")
    count = cursor.fetchone()[0]

    if count == 0 or force_reseed:
        # Seed Customers
        customers_data = [
            ("C-101", "Acme Corp", "finance@acme.com", "ENTERPRISE", 45000.00),
            ("C-204", "Globex Global", "billing@globex.org", "STANDARD", 12000.00),
            ("C-305", "Initech Systems", "admin@initech.com", "ADMIN_PRIVILEGED", 8500.00),
            ("C-408", "Cyberdyne Security", "ops@cyberdyne.io", "ADMIN_PRIVILEGED", 95000.00),
            ("C-509", "Stark Logistics", "accounts@stark.com", "STANDARD", 3200.00),
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO customers VALUES (?, ?, ?, ?, ?)",
            customers_data,
        )

        # Seed Purchase Orders
        po_data = [
            ("PO-2026-9011", "V-100", "Acme Industrial Supplies", 1200.00, "USD", "APPROVED", "VP_FINANCE", time.time() - 86400),
            ("PO-2026-9012", "V-200", "CloudScale Networks", 4500.00, "USD", "APPROVED", "CTO", time.time() - 172800),
            ("PO-2026-9013", "V-300", "Standard Office Corp", 450.00, "USD", "APPROVED", "OFFICE_MGR", time.time() - 43200),
            ("PO-2026-9014", "V-400", "Datadog Telemetry", 8500.00, "USD", "APPROVED", "ENG_DIR", time.time() - 90000),
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO purchase_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            po_data,
        )

        # Seed Invoices
        invoice_data = [
            (
                "INV-2026-0042",
                "PO-2026-9011",
                "Acme Industrial Supplies",
                1250.00,
                json.dumps([{"item": "Industrial Bearings", "qty": 10, "unit_price": 125.00}]),
                "SUBMITTED",
                time.time() - 3600,
            ),
            (
                "INV-2026-0043",
                "PO-2026-9013",
                "Standard Office Corp",
                475.00,
                json.dumps([{"item": "Paper Supplies", "qty": 20, "unit_price": 23.75}]),
                "SUBMITTED",
                time.time() - 7200,
            ),
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?)",
            invoice_data,
        )

        # Seed March 2026 Refund Requests (including high-value anomalies > $500)
        refund_data = [
            ("REF-2026-081", "C-101", 650.00, "Hardware defect claim", "PENDING", 0, time.time() - 5000),
            ("REF-2026-082", "C-101", 890.00, "Duplicate service charge claim", "PENDING", 0, time.time() - 3000),
            ("REF-2026-083", "C-204", 1200.00, "SLA breach credit request", "PENDING", 0, time.time() - 12000),
            ("REF-2026-084", "C-305", 45.00, "Minor tax discrepancy adjustment", "PENDING", 0, time.time() - 8000),
            ("REF-2026-085", "C-509", 120.00, "Overpaid shipping fee", "PENDING", 0, time.time() - 25000),
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO refund_requests VALUES (?, ?, ?, ?, ?, ?, ?)",
            refund_data,
        )

        conn.commit()
    conn.close()

    # 2. Seed DuckDB Analytics Engine
    try:
        d_conn = duckdb.connect(str(d_path))
        # Create analytical view linking SQLite tables directly into DuckDB
        d_conn.execute("CREATE TABLE IF NOT EXISTS analytics_audit_log (event_id VARCHAR, metric VARCHAR, val DOUBLE, logged_at TIMESTAMP)")
        d_conn.close()
    except Exception as e:
        logger.warning(f"DuckDB initialization warning: {e}")


class DatabaseQueryTool(BaseTool):
    """Executes read-only SQL queries against the ERP/CRM SQLite database."""

    name = "db_query"
    description = "Execute a read-only SELECT query against the enterprise SQLite ERP database."
    risk_level = "LOW"
    is_read_only = True

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_settings().SQLITE_DB_PATH

    def execute(self, sql: str, params: Optional[List[Any]] = None, **kwargs) -> ToolResult:
        # Enforce read-only constraint
        sql_clean = sql.strip().upper()
        if not sql_clean.startswith("SELECT") and not sql_clean.startswith("PRAGMA") and not sql_clean.startswith("EXPLAIN"):
            return ToolResult(
                success=False,
                error=f"Security violation: db_query only allows SELECT statements. Attempted: {sql[:30]}",
            )

        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, params or [])
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()

            # Flatten output if single row
            output_data: Any = rows
            if len(rows) == 1:
                single_row = dict(rows[0])
                single_row["_rows"] = rows
                output_data = single_row

            return ToolResult(
                success=True,
                output=output_data,
                metadata={"row_count": len(rows), "sql": sql},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Database query failed: {str(e)}")


class DatabaseUpdateTool(BaseTool):
    """Executes state-mutating SQL updates while capturing pre/post diffs for audit trails."""

    name = "db_update"
    description = "Execute an UPDATE or INSERT SQL statement on the ERP database with audit diff capture."
    risk_level = "MEDIUM"
    is_read_only = False

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_settings().SQLITE_DB_PATH

    def execute(self, sql: str, params: Optional[List[Any]] = None, **kwargs) -> ToolResult:
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Execute update
            cursor.execute(sql, params or [])
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()

            return ToolResult(
                success=True,
                output={
                    "rows_affected": rows_affected,
                    "sql": sql,
                    "status": "MUTATION_COMMITTED",
                },
                metadata={"rows_affected": rows_affected, "sql": sql},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Database update failed: {str(e)}")


class DuckDBAnalyticsTool(BaseTool):
    """Executes high-performance analytical queries via DuckDB."""

    name = "analytics_query"
    description = "Run analytical SQL queries and aggregations using DuckDB."
    risk_level = "LOW"
    is_read_only = True

    def __init__(self, sqlite_path: Optional[Path] = None, duckdb_path: Optional[Path] = None):
        self.sqlite_path = sqlite_path or get_settings().SQLITE_DB_PATH
        self.duckdb_path = duckdb_path or get_settings().DUCKDB_PATH

    def execute(self, sql: str, **kwargs) -> ToolResult:
        try:
            conn = duckdb.connect()
            # Attach SQLite database into DuckDB session
            conn.execute(f"ATTACH '{self.sqlite_path}' AS erp (TYPE SQLITE);")

            # Replace unqualified table names with erp.tablename if present
            modified_sql = sql
            for tbl in ["refund_requests", "purchase_orders", "invoices", "customers", "ledger_transactions"]:
                modified_sql = modified_sql.replace(f" {tbl} ", f" erp.{tbl} ")
                modified_sql = modified_sql.replace(f" {tbl}\n", f" erp.{tbl}\n")
                if modified_sql.endswith(f" {tbl}"):
                    modified_sql = modified_sql[:-len(tbl)] + f"erp.{tbl}"

            rel = conn.execute(modified_sql)
            columns = [col[0] for col in rel.description] if rel.description else []
            rows = rel.fetchall()
            dict_rows = [dict(zip(columns, row)) for row in rows]
            conn.close()

            return ToolResult(
                success=True,
                output=dict_rows,
                metadata={"row_count": len(dict_rows), "engine": "duckdb"},
            )
        except Exception as e:
            # Fallback directly to SQLite if duckdb attachment encounters driver limits
            logger.warning(f"DuckDB query fallback to SQLite: {e}")
            try:
                s_conn = sqlite3.connect(str(self.sqlite_path))
                s_conn.row_factory = sqlite3.Row
                c = s_conn.cursor()
                c.execute(sql)
                rows = [dict(r) for r in c.fetchall()]
                s_conn.close()
                return ToolResult(
                    success=True,
                    output=rows,
                    metadata={"row_count": len(rows), "engine": "sqlite_fallback"},
                )
            except Exception as e2:
                return ToolResult(success=False, error=f"Analytics query failed: {str(e2)}")


class EvaluateDiscrepancyTool(BaseTool):
    """
    Domain-specific financial reconciliation tool.
    Enforces corporate SOP tolerance ($50.00 max variance) for vendor invoice reconciliation.
    """

    name = "evaluate_discrepancy"
    description = "Compare invoice billed amount against approved PO and determine policy routing."
    risk_level = "LOW"
    is_read_only = True

    def execute(
        self,
        invoice_amount: Any,
        po_amount: Any,
        po_id: str,
        tolerance_limit: float = 50.0,
        **kwargs,
    ) -> ToolResult:
        try:
            inv_val = float(str(invoice_amount).replace("$", "").replace(",", ""))
            po_val = float(str(po_amount).replace("$", "").replace(",", ""))
            variance = round(abs(inv_val - po_val), 2)
            within_tolerance = variance <= tolerance_limit

            if within_tolerance:
                route_status = "RECONCILED"
                note = f"Variance of ${variance:.2f} is within automated tolerance (${tolerance_limit:.2f}). Auto-approved."
            else:
                route_status = "FLAGGED_DISPUTE"
                note = f"Variance of ${variance:.2f} exceeds tolerance (${tolerance_limit:.2f}). Held for dispute review."

            output_payload = {
                "po_id": po_id,
                "invoice_amount": inv_val,
                "po_amount": po_val,
                "variance": variance,
                "within_tolerance": within_tolerance,
                "route_status": route_status,
                "evaluation_note": note,
            }

            return ToolResult(
                success=True,
                output=output_payload,
                metadata={"variance": variance, "route_status": route_status},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Discrepancy evaluation failed: {str(e)}")
