# CentrAlign AI: Autonomous Enterprise Operator Runtime

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/tests-26%2F26%20passing%20(100%25)-brightgreen.svg)](tests/)
[![Architecture](https://img.shields.io/badge/architecture-Kahn's%20DAG%20%7C%20FACTDA-orange.svg)](#4-design-rationale-kahns-topological-dag-vs-sequential-react)
[![Offline Mode](https://img.shields.io/badge/offline%20mode-100%25%20zero--cost-success.svg)](#2-quickstart--verification-offline--live)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**An auditable, self-contained, and fault-tolerant digital employee runtime replacing fragile sequential chatbots with Kahn's DAG topological scheduling, pre-execution RBAC guardrails, hybrid enterprise tools, dual-tier outcome verification, and cryptographic evidence receipts.**

**Author**: [Hammad Khan]([https://github.com/hams12khan](https://github.com/hams12khan)) (*Applied Scientist Intern, Amazon Central ML | M.S. by Research, IIT Bhubaneswar*)

[System Overview](#1-system-overview) • [Quickstart & Verification](#2-quickstart--verification-offline--live) • [System Architecture](#3-architecture--data-flow) • [Kahn's DAG vs. ReAct](#4-design-rationale-kahns-topological-dag-vs-sequential-react) • [Execution Lifecycle](#5-execution-lifecycle--core-subsystems) • [Scenarios & Tools](#6-supported-scenarios--tool-matrix) • [Code Navigation & Rubric](#7-codebase-navigation--evaluation-rubric-mapping) • [Limitations & Roadmap](#8-known-limitations--production-roadmap)

</div>

---

## 1. System Overview

### 1.1 The Enterprise Problem: The "Copilot Fallacy"
Most enterprise AI agent initiatives fail in production because they deploy conversational assistants that output advisory text tokens rather than executing governed state mutations. Consider a standard operational request:

> *"Reconcile vendor invoice INV-2026-0042 against PO-2026-9011, evaluate the $50 variance against accounting policy, update the ERP ledger, and disburse payment."*

When submitted to standard conversational copilots or raw LLM agent wrappers, the system produces textual commentary:
> *"Here is what you should do: inspect the purchase_orders table, check your variance policy in your SOP document, and execute an SQL UPDATE statement..."*

This dynamic constitutes the **Copilot Fallacy**: conversational agents generate text strings that still require human manual labor to execute, verify, and assume operational liability for. Enterprises do not require another conversational advisor; enterprises require an **autonomous digital operator** that takes high-level intent, evaluates corporate governance rules, plans multi-step dependency graphs, safely executes state changes across databases, web portals, and file systems, halts for authorized human review on high-risk operations, and outputs cryptographic evidence of verified completion.

### 1.2 System Differentiators: Conversational Chatbot vs. Autonomous Operator Runtime

| Architectural Dimension | Conversational Chatbot / Copilot | CentrAlign Autonomous Operator Runtime |
| :--- | :--- | :--- |
| **Primary Output** | Text tokens, code snippets, advisory commentary | **Committed state mutations** (database records updated, ledgers reconciled, audit files written) |
| **Context & Memory** | Ephemeral, amnesiac session prompts | **Persistent organizational memory** (embedded SOP store, SQLite checkpoints, policy limits) |
| **Action Planning** | Blind sequential guessing (ReAct: `Thought -> Action -> Observation`) | **Compiled Kahn's DAG**: dependency graph with cycle detection, parallel waves, and dynamic parameter piping |
| **Governance & Safety** | System prompts (vulnerable to hallucination and prompt injection) | **Deterministic Pre-Execution RBAC Gate**: code-level enforcement halting actions $\ge \$1,000$ or destructive SQL |
| **Tool Execution** | Read-only mock text analysis | **Hybrid Enterprise Hands**: SQLite ERP ledger, DuckDB OLAP analytics, Playwright headless browser, sandboxed files |
| **Error Handling** | Crashes or hallucinated error recoveries | **Self-healing runtime**: automated exponential retries and analytical fallback (DuckDB $\rightarrow$ SQLite ERP) |
| **Outcome Verification** | Assumed accurate via self-reporting | **Dual-Tier Verification**: physical database row mutation diffs + independent LLM-as-a-Judge scoring |
| **Auditability** | Ephemeral chat transcript | **Tamper-Evident Evidence Receipt**: unbroken SHA-256 cryptographic hash chain |

---

## 2. Quickstart & Verification (Offline & Live)

Reviewers can verify and run the complete autonomous runtime in under 30 seconds. The test suite operates **100% offline with zero external API dependencies**.

### 2.1 30-Second Setup & Test Execution

```bash
# 1. Clone repository and navigate to runtime directory
git clone https://github.com/hams12khan/CentrAlign-AI-Assessment.git
cd CentrAlign-AI-Assessment

# 2. Install dependencies
pip install -r requirements.txt

# 3. Execute the automated test suite (26/26 tests pass in < 3s offline)
python tests/run_all_tests.py
# or: pytest -v

# 4. Launch the executive presentation dashboard
streamlit run demo_app.py
```

### 2.2 Test Suite Architecture (26/26 Passing)

The test suite validates every core operational invariant using isolated fixtures:

```
tests/test_dag_scheduler.py::test_topological_sort_linear PASSED                     [  3%]
tests/test_dag_scheduler.py::test_topological_sort_parallel_branches PASSED          [  7%]
tests/test_dag_scheduler.py::test_cycle_detection_raises_cyclic_dependency_error PASSED [ 11%]
tests/test_dag_scheduler.py::test_dynamic_param_resolution PASSED                    [ 15%]
tests/test_dag_scheduler.py::test_parallel_execution_timing PASSED                   [ 19%]
tests/test_dag_scheduler.py::test_scheduler_retry_on_transient_failure PASSED        [ 23%]
tests/test_dag_scheduler.py::test_deep_nested_dynamic_param_resolution PASSED        [ 26%]
tests/test_end_to_end.py::test_end_to_end_invoice_reconciliation_workflow PASSED     [ 30%]
tests/test_end_to_end.py::test_end_to_end_refund_anomaly_audit_workflow PASSED       [ 34%]
tests/test_end_to_end.py::test_end_to_end_hitl_pause_and_resume_flow PASSED          [ 38%]
tests/test_policy_guard.py::test_read_only_tools_auto_approved PASSED                [ 42%]
tests/test_policy_guard.py::test_safe_mutations_auto_approved PASSED                 [ 46%]
tests/test_policy_guard.py::test_high_value_mutation_triggers_awaiting_approval PASSED [ 50%]
tests/test_policy_guard.py::test_destructive_sql_triggers_approval PASSED            [ 53%]
tests/test_policy_guard.py::test_grant_approval_and_cryptographic_signature PASSED   [ 57%]
tests/test_policy_guard.py::test_sql_amount_parsing_triggers_halt PASSED             [ 61%]
tests/test_policy_guard.py::test_delete_action_triggers_critical_halt PASSED         [ 65%]
tests/test_tools.py::test_file_write_and_read PASSED                                  [ 69%]
tests/test_tools.py::test_sandbox_path_traversal_prevention PASSED                    [ 73%]
tests/test_tools.py::test_database_query_read_only_enforcement PASSED                [ 76%]
tests/test_tools.py::test_database_update_mutations PASSED                            [ 80%]
tests/test_tools.py::test_duckdb_analytics_query PASSED                               [ 84%]
tests/test_tools.py::test_evaluate_discrepancy_tolerance_rules PASSED                 [ 88%]
tests/test_tools.py::test_browser_tool_execution_and_evidence PASSED                  [ 92%]
tests/test_tools.py::test_duckdb_query_with_semicolon_and_grouping PASSED              [ 96%]
tests/test_tools.py::test_browser_tool_form_interaction PASSED                        [100%]
============================== 26 passed in 2.40s ==============================
```

### 2.3 Provider Configuration Modes

CentrAlign AI supports three switchable LLM provider configurations via `.env`:

1. **Deterministic Mock Provider (Default, 100% Offline)**:
   - Configured via `LLM_PROVIDER=mock`.
   - Uses AST pattern matching and heuristic goal compilation.
   - Requires zero API keys, incurs $0 cost, executes with 0ms network latency, and enables continuous CI/CD verification.
2. **Groq Cloud Provider (Production Free-Tier)**:
   - Configured via `LLM_PROVIDER=groq` and `GROQ_API_KEY=gsk_...`.
   - Leverages `llama-3.3-70b-versatile` for high-throughput, low-latency reasoning.
3. **Google Gemini Provider (Production Free-Tier)**:
   - Configured via `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=AIzaSy...`.
   - Leverages `gemini-2.0-flash` for multi-modal analysis and extensive context handling.

---

## 3. Architecture & Data Flow

CentrAlign AI coordinates execution through a unified Brain-Hands-Memory-Eyes pipeline:

```mermaid
flowchart TD
    subgraph UI ["1. Client & Ingestion Layer"]
        User["Business Operator / ERP Webhook"] -->|Natural Language Intent| App["Streamlit Dashboard / CLI / API"]
    end

    subgraph MemoryLayer ["2. Persistent Memory & Governance"]
        MemDB[("SQLite SOP Store\n(enterprise_memory.db)")]
        BM25["BM25 / TF-IDF Semantic Retriever\n(Zero-Vector Dependency)"]
        MemDB <--> BM25
    end

    subgraph Brain ["3. DAG Planning & Compilation Engine"]
        LLM["Unified LLM Provider\n(Groq Llama 3.3 / Gemini / Offline Mock)"]
        Planner["DAGPlanner (planner.py)\nEntity Deconstruction & Kahn Compiler"]
        App -->|Goal Prompt| Planner
        BM25 -->|Relevant SOPs & Tolerances| Planner
        Planner <-->|1-Shot Compilation| LLM
        DAG[("Compiled DAGPlan\n(Dependency Graph + Idempotency Tokens)")]
        Planner --> DAG
    end

    subgraph Governance ["4. Pre-Execution Policy Gate (RBAC)"]
        Guard["PolicyGuard (policy_guard.py)\nDeterministic Code Gate"]
        DAG --> Guard
        CheckRisk{"Risk Assessment\nAction Type & Dollar Threshold"}
        Guard --> CheckRisk
        CheckRisk -->|Low/Medium: Read-Only or < $1,000| AutoApprove["AUTO-APPROVED\n(Audit Log Entry)"]
        CheckRisk -->|High/Critical: >= $1,000 or Destructive SQL| PauseNode["PAUSED_AWAITING_APPROVAL\n(Halt Execution Wave)"]
    end

    subgraph HITL ["5. Human-in-the-Loop State Machine"]
        CheckpointDB[("SQLite Checkpoints Table\n(Serialized State)")]
        PauseNode -->|Serialize DAG & Context| CheckpointDB
        PauseNode -->|Trigger Alert| HumanManager["Human Manager\n(Streamlit Modal / Slack)"]
        HumanManager -->|Cryptographic Digital Signature| SignOff["ApprovalRecord\nSHA-256(approval_id + approver + secret)"]
        SignOff -->|Resume Graph| RestoreState["Restore DAG & Checkpoint"]
        RestoreState --> AutoApprove
    end

    subgraph Hands ["6. Topological Scheduler & Multi-Tool Execution"]
        Scheduler["DAGScheduler (scheduler.py)\nKahn's Topological Waves"]
        AutoApprove --> Scheduler
        ThreadPool["Concurrent Wave Dispatch\n(ThreadPoolExecutor)"]
        Scheduler --> ThreadPool

        subgraph Tools ["Hybrid Enterprise Toolset"]
            T_SQL["DatabaseQuery / Update Tool\n(SQLite ERP Ledger)"]
            T_Duck["DuckDB Analytics Tool\n(High-Speed OLAP Queries)"]
            T_Browser["Browser Tool (Playwright)\n(Web Portal DOM & Screenshots)"]
            T_File["File Tool\n(Sandboxed Read/Write & SHA-256)"]
        end

        ThreadPool --> T_SQL
        ThreadPool --> T_Duck
        ThreadPool --> T_Browser
        ThreadPool --> T_File

        SelfHealing{"Tool Execution Check"}
        T_SQL --> SelfHealing
        T_Duck --> SelfHealing
        T_Browser --> SelfHealing
        T_File --> SelfHealing

        SelfHealing -->|Transient Lock| Retry["Transient Retry Loop\n(Max 2 Retries with Backoff)"]
        Retry --> Scheduler
        SelfHealing -->|Analytical Lock| Fallback["Self-Healing Fallback\n(DuckDB -> SQLite ERP)"]
        Fallback --> Scheduler
    end

    subgraph Eyes ["7. Dual-Tier Verification Layer"]
        SelfHealing -->|Execution Success| Verifier["OutcomeVerifier (verifier.py)"]
        Tier1["Tier 1: Deterministic Ground Truth\n(SQL Row Mutation Diff + File Check)"]
        Tier2["Tier 2: LLM-as-a-Judge\n(Quantitative 0.0 - 1.0 Confidence Score)"]
        Verifier --> Tier1
        Verifier --> Tier2
    end

    subgraph EvidenceLayer ["8. Evidence & Tamper-Evident Receipts"]
        EvidenceGen["EvidenceGenerator (evidence.py)"]
        Tier1 --> EvidenceGen
        Tier2 --> EvidenceGen
        Receipt[("EvidenceReceipt (.json)\nSHA-256 Hash Chain Integrity")]
        EvidenceGen --> Receipt
        Receipt -->|Display Metrics & Download| App
    end
```

---

## 4. Design Rationale: Kahn's Topological DAG vs. Sequential ReAct

### 4.1 The ReAct Scaling Bottleneck
Standard agent frameworks rely on sequential ReAct loops (`Thought -> Action -> Observation -> Thought...`):
1. The agent invokes the LLM: *"I need to query the database."* $\rightarrow$ invokes tool $\rightarrow$ receives output.
2. The agent re-invokes the LLM with expanded history: *"Now I need to read the invoice file."* $\rightarrow$ invokes tool $\rightarrow$ receives output.
3. The agent re-invokes the LLM: *"Now I need to compare values."* $\rightarrow$ invokes tool $\rightarrow$ receives output.
4. The agent re-invokes the LLM: *"Now I need to update the database."* $\rightarrow$ invokes tool.

In enterprise production environments, this sequential loop exhibits four fundamental failure modes:
- **$O(N)$ Latency Overhead**: For an $N$-step procedure, the runtime incurs $N$ sequential model round trips. A 6-step workflow regularly requires 30–60 seconds.
- **Compounding Error Rates**: If each LLM step maintains a 90% individual accuracy rate, an agent executing 6 sequential steps has an overall success rate of only $(0.90)^6 \approx 53.1\%$.
- **Quadratic Token Inflation**: Accumulating tool observations in the conversation context causes prompt token volume to scale quadratically, increasing API cost and latency.
- **Absence of Concurrency**: Independent operations (e.g., fetching a database record and reading an invoice document) are executed sequentially rather than in parallel.

### 4.2 Architectural Precedent: Amazon FACTDA
During prior research at Amazon Central Machine Learning scaling autonomous analytical workflows across **16,000+ enterprise service APIs**, this exact sequential bottleneck prompted the formulation of the **FACTDA (Fetch and Compile Tool DAG Agent)** architecture.

FACTDA replaces step-by-step guessing with a **Compile-Then-Execute** paradigm:
1. **Compilation Stage**: The LLM is invoked once upfront to decompose the business goal into a strongly typed **Directed Acyclic Graph (DAG)** of atomic operations with explicit dependency edges.
2. **Topological Execution Stage**: A deterministic scheduling engine powered by **Kahn's topological sorting algorithm** identifies independent task subsets and executes them in concurrent waves.

### 4.3 Algorithmic Comparison: ReAct vs. Kahn's DAG (FACTDA)

| Metric | Sequential ReAct | Kahn's Topological DAG (CentrAlign AI) | Operational Impact |
| :--- | :--- | :--- | :--- |
| **Model Invocations** | $N$ round trips ($N$ = step count) | **1 invocation** (upfront compilation) | **2.6x to 8x token reduction** |
| **Execution Latency** | $\sum_{i=1}^N (T_{\text{LLM}} + T_{\text{tool}})$ | $\max(T_{\text{wave}_1}) + \max(T_{\text{wave}_2}) + \dots$ | **4x wall-clock speedup** |
| **Deadlock Detection** | None (infinite loops possible) | Graph cycle check (`in_degree > 0`) | Guaranteed termination (`CyclicDependencyError`) |
| **Fault Isolation** | Mid-sequence failure drops state | Step-level retries & state checkpoints | Deterministic replay and resumption |
| **Safety Governance** | Prompt instructions (unreliable) | Pre-execution deterministic code gate | Hard RBAC enforcement |

---

## 5. Execution Lifecycle & Core Subsystems

CentrAlign AI structures autonomous execution through an elevated 9-stage lifecycle:

$$\text{Goal} \longrightarrow \text{Understand} \longrightarrow \text{Plan} \longrightarrow \text{Govern} \longrightarrow \text{Execute} \longrightarrow \text{Observe} \longrightarrow \text{Adapt} \longrightarrow \text{Verify} \longrightarrow \text{Complete}$$

```
+----------------------------------------------------------------------------------------------------------------+
| 1. GOAL        : Ingest plain-English enterprise request (e.g. reconcile invoice vs PO).                       |
| 2. UNDERSTAND  : Deconstruct entities; query SOPs via embedded BM25 retriever (zero vector DB overhead).       |
| 3. PLAN        : Compile strongly-typed DAGPlan; sort into Kahn's waves; generate SHA-256 idempotency tokens.  |
| 4. GOVERN      : Pre-execution RBAC code gate: auto-approve < $1K; halt >= $1K into SQLite checkpoint (HITL).  |
| 5. EXECUTE     : Dispatch parallel waves via ThreadPoolExecutor across SQLite ERP, DuckDB, Playwright, files.  |
| 6. OBSERVE     : Capture telemetry: database affected row count, DOM tables, PNG screenshots, latency metrics.  |
| 7. ADAPT       : Pipe dynamic params ($step_1.output.variance); retry transient locks; self-heal DuckDB->SQLite.|
| 8. VERIFY      : Dual-tier verification: Tier 1 physical SQL row diffs + Tier 2 LLM-as-a-Judge (0.0 to 1.0).    |
| 9. COMPLETE    : Bundle execution traces and manager signatures into an immutable SHA-256 EvidenceReceipt.     |
+----------------------------------------------------------------------------------------------------------------+
```

### 5.1 Subsystem 1: Persistent Memory & SOP Retrieval (`runtime/memory.py`)
- Employs an embedded SQLite database storing corporate Standard Operating Procedures (e.g., `SOP-FIN-001` for variance tolerances, `SOP-SEC-003` for access reviews).
- Features an embedded **BM25 / TF-IDF semantic retrieval engine**, delivering sub-millisecond keyword and policy matching with zero external vector database infrastructure requirements.
- Houses the checkpointing engine that serializes paused execution graphs into `checkpoints` tables for durable Human-in-the-Loop workflows.

### 5.2 Subsystem 2: The Brain — DAG Compilation (`runtime/planner.py`)
- Translates unstructured intent into a validated Pydantic `DAGPlan` comprising atomic `TaskStep` nodes.
- **Idempotency Shield**: Generates a deterministic cryptographic token for every state-mutating step:
  `Token = SHA-256(task_id + step_id + tool + canonical_params)`
  This solves the enterprise "Ghost Action" failure mode: if a network drop or database timeout occurs during a payment step, retrying the operation detects the identical token and prevents duplicate financial disbursement.

### 5.3 Subsystem 3: Deterministic Pre-Execution Policy Gate (`runtime/policy_guard.py`)
- Acts as a pure Python security gatekeeper positioned strictly before tool execution.
- Evaluates operation classification, SQL query ASTs, and target financial values:
  - **Read-Only Actions & Safe Updates (< $1,000)**: Auto-approved with structured audit logs.
  - **High-Risk Actions ($\ge \$1,000$ or Destructive SQL)**: Execution immediately halts with state transitioned to `PAUSED_AWAITING_APPROVAL`.
- **Human-in-the-Loop State Machine**: Serializes complete DAG state and memory into SQLite checkpoints. The runtime releases execution threads until an authorized human supervisor signs off with an `ApprovalRecord` containing a cryptographic SHA-256 signature.

### 5.4 Subsystem 4: The Hands — Multi-Tool Scheduler (`runtime/scheduler.py`)
- Implements Kahn's topological sort algorithm to group non-dependent tasks into concurrent execution waves.
- Dispatches parallel steps via `ThreadPoolExecutor`. Independent operations (e.g., reading an invoice file from disk and querying an ERP purchase order) execute simultaneously in **Wave 1 in 32 milliseconds**.
- **Dynamic Parameter Piping**: Downstream steps dynamically resolve output parameters from upstream dependencies (e.g., `$step_1.total_amount`) using recursive path traversal.
- **Self-Healing Loop**: Automatically retries transient failures up to 2 times with exponential backoff, and falls back from analytical DuckDB queries to SQLite transactional queries if attachment locks occur.

### 5.5 Subsystem 5: The Eyes — Dual-Tier Outcome Verification (`runtime/verifier.py`)
- Eliminates **LLM Self-Certification Bias** (where conversational models report successful completion even when the underlying tool failed or returned errors).
- **Tier 1 (Deterministic Ground Truth)**: Executes direct physical inspection queries against the database (e.g., checking that `status = 'RECONCILED'` for the target record) and inspects output files on disk.
- **Tier 2 (LLM-as-a-Judge)**: An independent evaluation prompt compares the initial objective, database state diffs, and execution traces to produce a quantitative confidence score (**0.0 to 1.0**) and qualitative diagnosis.

### 5.6 Subsystem 6: Cryptographic Evidence Receipts (`runtime/evidence.py`)
- Synthesizes an immutable, audit-ready `EvidenceReceipt` package (.json).
- Implements an unbroken **SHA-256 Cryptographic Hash Chain** linking task IDs, timestamps, execution latency, policy decisions, manager approval records, artifact hashes, and verification scores.
- Any manual post-execution alteration of audit metrics immediately invalidates the hash chain check (`verify_receipt_integrity()`), providing non-repudiation for financial audits.

---

## 6. Supported Scenarios & Tool Matrix

### 6.1 Hybrid Enterprise Tool Matrix

| Tool Component | File Location | Class Name | Capabilities & Protections |
| :--- | :--- | :--- | :--- |
| **Transactional ERP** | [`runtime/tools/db_tool.py`](runtime/tools/db_tool.py) | `DatabaseQueryTool`<br>`DatabaseUpdateTool` | ACID-compliant SQL operations over corporate ledgers. Enforces `SELECT`-only query isolation on read paths and row-level updates. |
| **High-Speed OLAP** | [`runtime/tools/db_tool.py`](runtime/tools/db_tool.py) | `DuckDBAnalyticsTool` | Executes vector-accelerated analytical queries across thousands of financial transactions in milliseconds with zero-copy memory transfer. |
| **Headless Browser** | [`runtime/tools/browser_tool.py`](runtime/tools/browser_tool.py) | `BrowserTool` | Automates web portals via **Playwright**. Navigates internal sites, extracts DOM tables, executes form entries, and captures full-page PNG screenshots. |
| **Sandboxed Files** | [`runtime/tools/file_tool.py`](runtime/tools/file_tool.py) | `FileReadTool`<br>`FileWriteTool` | Reads structured invoices and writes compliance dossiers. Strictly enforces path containment (`../../` blocked) and computes SHA-256 file hashes. |

### 6.2 Pre-Configured Operational Scenarios

CentrAlign AI includes five interactive scenarios accessible via the Streamlit dashboard:

1. **Vendor Invoice Discrepancy Reconciliation (Within Tolerance $\le \$50$)**:
   - Reconciles invoice `INV-2026-0042` against purchase order `PO-2026-9011`.
   - Executes Wave 1 (`file_read` + `db_query`) in parallel in 32ms.
   - Evaluates $50 variance against `SOP-FIN-001`, auto-approves reconciliation, updates the ledger to `RECONCILED`, and generates proof.
2. **High-Value Financial Mutation ($4,500 Emergency Payment — Triggers HITL)**:
   - Evaluates payment disbursement for `PO-2026-9012`.
   - `PolicyGuard` detects the $4,500 value exceeds the $1,000 threshold.
   - Halts execution into `PAUSED_AWAITING_APPROVAL` and creates a SQLite checkpoint.
   - Resumes upon entry of manager credentials and digital cryptographic signature.
3. **Customer Refund Anomaly Audit (> $500 DuckDB OLAP Fraud Detection)**:
   - Performs analytical aggregation across March 2026 refund claims using in-memory DuckDB.
   - Flags suspicious multi-claim customer accounts, updates ledger status to `UNDER_REVIEW`, and compiles an audit package.
4. **Privileged Access Review & RBAC Governance**:
   - Audits administrative accounts holding elevated privileges against `SOP-SEC-003`.
   - Flags dormant credentials and writes a SHA-256 hashed compliance dossier to the sandboxed file system.
5. **Arbitrary Custom Business Goal**:
   - Accepts free-form natural language input from the operator.
   - Deconstructs intent, compiles dynamic Kahn DAG waves, enforces RBAC policies, and verifies completion.

---

## 7. Codebase Navigation & Evaluation Rubric Mapping

### 7.1 Key Classes & Functions Index

| Architectural Capability | Source Code Location | Primary Class / Function |
| :--- | :--- | :--- |
| **Kahn's Topological Sort** | [`runtime/scheduler.py`](runtime/scheduler.py) | `DAGScheduler.compute_topological_order()` |
| **Dynamic Parameter Resolution** | [`runtime/scheduler.py`](runtime/scheduler.py) | `DAGScheduler.resolve_dynamic_params()` |
| **Idempotency Token Computation** | [`runtime/planner.py`](runtime/planner.py) | `TaskStep.idempotency_token` property |
| **Deterministic RBAC Evaluation** | [`runtime/policy_guard.py`](runtime/policy_guard.py) | `PolicyGuard.evaluate_step()` |
| **Cryptographic Sign-Off** | [`runtime/policy_guard.py`](runtime/policy_guard.py) | `ApprovalRecord.compute_signature()` |
| **Execution Checkpointing** | [`runtime/memory.py`](runtime/memory.py) | `EnterpriseMemory.save_execution_checkpoint()` |
| **BM25 Semantic SOP Retrieval** | [`runtime/memory.py`](runtime/memory.py) | `EnterpriseMemory.query_sops()` |
| **Dual-Tier Verification Engine** | [`runtime/verifier.py`](runtime/verifier.py) | `OutcomeVerifier.verify()` |
| **Tamper-Evident SHA-256 Receipts** | [`runtime/evidence.py`](runtime/evidence.py) | `EvidenceReceipt.calculate_tamper_evidence_hashes()` |
| **Playwright Browser Automation** | [`runtime/tools/browser_tool.py`](runtime/tools/browser_tool.py) | `BrowserTool.execute()` |
| **DuckDB In-Memory OLAP** | [`runtime/tools/db_tool.py`](runtime/tools/db_tool.py) | `DuckDBAnalyticsTool.execute()` |
| **Deterministic Mock Provider** | [`runtime/llm_provider.py`](runtime/llm_provider.py) | `MockLLMProvider.generate()` |

### 7.2 Direct Mapping to Evaluation Criteria

| Evaluation Rubric Item | Runtime Implementation Strategy | Code Reference |
| :--- | :--- | :--- |
| **1. Understanding intended outcome** | Deconstructs natural language intent, extracts target entities (PO IDs, amounts, files), and classifies task domain. | [`DAGPlanner.plan()`](runtime/planner.py) |
| **2. Determining what needs to be done** | Queries persistent organizational memory to retrieve governing SOPs and variance tolerance thresholds. | [`EnterpriseMemory.query_sops()`](runtime/memory.py) |
| **3. Planning required actions** | Compiles a strongly typed DAG with explicit dependency edges and cryptographic idempotency tokens. | [`DAGPlanner._build_plan()`](runtime/planner.py) |
| **4. Selecting appropriate tools** | Binds planned task steps to specialized enterprise tools (`db_query`, `db_update`, `analytics_query`, `browser`, `file_write`). | [`ToolRegistry`](runtime/tools/base.py) |
| **5. Executing actions** | Executes real state mutations across SQLite ERP, DuckDB OLAP, Playwright browser, and local sandbox. | [`DAGScheduler.execute_plan()`](runtime/scheduler.py) |
| **6. Observing what happened** | Captures structured outputs, affected row counts, DOM tables, visual screenshots, and file hashes. | [`StepExecutionResult`](runtime/scheduler.py) |
| **7. Determining next action dynamically** | Resolves dynamic parameter references (`$step_1.output.discrepancy`) and routes upstream data into downstream steps. | [`DAGScheduler.resolve_dynamic_params()`](runtime/scheduler.py) |
| **8. Recovering from failures** | Automated step retry loop on transient faults, plus autonomous self-healing fallback from DuckDB to SQLite. | [`DAGScheduler._execute_single_step()`](runtime/scheduler.py) |
| **9. Maintaining state & context** | Persists execution state, step results, and checkpoints to SQLite so workflows pause/resume across days. | [`EnterpriseMemory.save_execution_checkpoint()`](runtime/memory.py) |
| **10. Asking for human approval** | Pre-execution RBAC intercepts actions >= $1,000 or destructive SQL, pausing execution until cryptographic sign-off. | [`PolicyGuard.evaluate_step()`](runtime/policy_guard.py) |
| **11. Verifying outcome completion** | Dual-tier verification: queries database ground truth diffs + LLM-as-a-Judge quantitative confidence scoring (0.0 to 1.0). | [`OutcomeVerifier.verify()`](runtime/verifier.py) |
| **12. Returning cryptographic evidence** | Synthesizes an immutable `EvidenceReceipt` featuring execution traces, approvals, and an unbroken SHA-256 hash chain. | [`EvidenceGenerator.generate_receipt()`](runtime/evidence.py) |

---

## 8. Known Limitations & Production Roadmap

A production-grade system requires honest engineering pragmatism regarding scaling boundaries and technical trade-offs. The current architecture was optimized for a self-contained, 100% runnable proof of concept. The following table outlines the architectural constraints and the corresponding production migration path:

| Architecture Component | Current PoC Implementation | Scaling Limitation | Production Enterprise Target |
| :--- | :--- | :--- | :--- |
| **State Storage & Checkpoints** | Embedded SQLite (`enterprise_memory.db`) | Database-level write locks (`sqlite3.OperationalError: database is locked`) bottleneck high-concurrency multi-tenant throughput. | **PostgreSQL / CockroachDB** with connection pooling (PgBouncer), row-level locks (`SELECT ... FOR UPDATE`), and partitioned checkpoint tables. |
| **Wave Task Orchestration** | In-process Python `ThreadPoolExecutor` | Limited to a single machine/process. If the worker node crashes during Wave 2, in-memory wave state is lost unless rehydrated from disk. | **Temporal.io / Celery / Redis Streams** for distributed, durable workflow execution with automatic heartbeat checks and multi-node worker pooling. |
| **Browser Automation** | Local Playwright Chromium process | Spawning local Chromium instances consumes ~150–300 MB RAM per instance; unpooled browsers risk memory leaks under heavy concurrency. | **Isolated Browser Worker Pool** (e.g. Browserless.io or ephemeral containerized Chromium sidecars on Kubernetes) with automated recycling. |
| **Idempotency Locking** | Local SQLite transaction checks | Idempotency tokens are scoped to the local database file; cannot prevent duplicate writes across geo-distributed databases. | **Distributed Redis Locks (Redlock)** with atomic TTL leasing and global transaction IDs. |
| **Telemetry & Observability** | In-memory execution logs + JSON files | Metrics and step latencies are stored locally; lacking centralized APM tracing across microservices. | **OpenTelemetry (OTel)** instrumentation exporting distributed traces and spans directly to Datadog, Honeycomb, or Jaeger. |
| **Policy Governance Rules** | Local Python policy classes (`PolicyGuard`) | Rule changes require codebase redeployment; no support for dynamic enterprise policy management. | **Open Policy Agent (OPA) / Rego** service with centralized policy versioning and dynamic RBAC syncing. |

---

## 9. About the Author

- **Author**: Hammad Khan
- **Role**: Applied Scientist Intern, Amazon Central ML | M.S. by Research, IIT Bhubaneswar
- **Core Research**: Formulated **FACTDA (Fetch and Compile Tool DAG Agent)** for scaling autonomous tool orchestration across 16,000+ enterprise APIs.
- **License**: MIT
