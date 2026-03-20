# Task Execution Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make task execution reliable and observable by introducing task run records, a correct task state machine, and consistent result persistence for the collection backend.

**Architecture:** Keep the existing FastAPI + SQLAlchemy structure, but add a dedicated task run model and move execution outcome handling into the service layer. Preserve the current API shape where possible while making `/run` create a tracked execution record and finish in `completed` or `failed` based on actual scrape results.

**Tech Stack:** Python 3.10, FastAPI, SQLAlchemy 2.x, Pydantic 2, pytest

---

### File Map

**Create:**
- `tests/test_task_execution.py`

**Modify:**
- `src/bis/models/models.py`
- `src/bis/models/schemas.py`
- `src/bis/repositories/repositories.py`
- `src/bis/services/task_service.py`
- `src/bis/services/scraper_service.py`
- `src/bis/api/tasks.py`
- `src/bis/api/intelligence.py`
- `src/bis/core/database.py`

### Task 1: Add failing tests for tracked task execution

**Files:**
- Create: `tests/test_task_execution.py`
- Modify: `src/bis/core/database.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert:
- a task run record is created when execution starts
- failed scraping marks the task as `failed`
- successful scraping stores a deduplication key and a task run summary

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_task_execution.py -q`
Expected: FAIL because task run models and APIs do not exist yet

### Task 2: Add task run persistence and richer task statuses

**Files:**
- Modify: `src/bis/models/models.py`
- Modify: `src/bis/models/schemas.py`
- Modify: `src/bis/repositories/repositories.py`

- [ ] **Step 1: Add model/schema coverage required by failing tests**

Implement:
- `TaskStatus.FAILED`
- `TaskStatus.QUEUED`
- `TaskRunStatus` enum
- `CollectionTaskRunModel`
- response schemas for task runs

- [ ] **Step 2: Run test to verify it still fails on missing behavior**

Run: `pytest tests/test_task_execution.py -q`
Expected: FAIL in service/API logic, not import/model errors

### Task 3: Rework task execution orchestration

**Files:**
- Modify: `src/bis/services/task_service.py`
- Modify: `src/bis/services/scraper_service.py`
- Modify: `src/bis/api/tasks.py`

- [ ] **Step 1: Implement minimal orchestration**

Implement:
- create a task run before background execution
- mark task `running` when a run starts
- mark `completed` only on success
- mark `failed` with error details on exceptions
- persist run summary fields
- assign deduplication keys on scraped items

- [ ] **Step 2: Run targeted tests**

Run: `pytest tests/test_task_execution.py -q`
Expected: PASS

### Task 4: Expose run history and harden search inputs

**Files:**
- Modify: `src/bis/api/tasks.py`
- Modify: `src/bis/api/intelligence.py`

- [ ] **Step 1: Add minimal read APIs**

Implement:
- `GET /api/v1/tasks/{task_id}/runs`
- safer date parsing in intelligence search with proper 400 responses

- [ ] **Step 2: Add or extend tests if needed**

Add assertions for run history API shape and invalid date handling.

- [ ] **Step 3: Run targeted tests**

Run: `pytest tests/test_task_execution.py -q`
Expected: PASS

### Task 5: Full verification

**Files:**
- Modify as needed from previous tasks

- [ ] **Step 1: Run focused verification**

Run: `pytest tests/test_task_execution.py -q`
Expected: PASS

- [ ] **Step 2: Run broader project verification**

Run: `pytest -q`
Expected: PASS for the available test suite
