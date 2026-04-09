# Task Review Log

<!-- reviewer-config
principles: [SOLID, DRY, FAIL_FAST, TDD, ASYNC_FIRST, LOGGING, TYPING, STYLE, COMMITS, COVERAGE]
codebase-conventions:
  - Pragmas: `# pragma: no cover` para código estructuralmente unreachable
  - Tests: pytest con fixtures, async/await patterns, mock/AsyncMock
  - Coordinator pattern: entities heredan CoordinatorEntity y leen de coordinator.data
  - Device IDs: Usar vehicle_id (nombre amigable) en identifiers, no entry_id (UUID)
  - SOLID: Separación de responsabilidades - coordinator, trip_manager, emhass_adapter, sensor
  - TDD: Red-Green-Refactor workflow (test que falla primero, luego fix)
  - 100% coverage: fail_under = 100 en pyproject.toml
  - Async-first: Usar async/await, no operaciones bloqueantes ni I/O sin aiohttp/async libs
  - Logging: Usar _LOGGER, no print() statements
  - Typing: Type hints obligatorios, mypy con disallow_any_generics
  - Style: black/isort/pylint configurados en pyproject.toml
  - Commits: Formato específico exigido en .github/copilot-instructions.md
-->

<!-- 
Workflow: External reviewer agent writes review entries to this file after completing tasks.
Status values: FAIL, WARNING, PASS, PENDING
- FAIL: Task failed reviewer's criteria - requires fix
- WARNING: Task passed but with concerns - note in .progress.md
- PASS: Task passed external review - mark complete
- PENDING: reviewer is working on it, spec-executor should not re-mark this task until status changes. spec-executor: skip this task and move to the next unchecked one.
-->

## Reviews

<!-- 
Review entry template:
- status: FAIL | WARNING | PASS | PENDING
- severity: critical | major | minor (optional)
- reviewed_at: ISO timestamp
- criterion_failed: Which requirement/criterion failed (for FAIL status)
- evidence: Brief description of what was observed
- fix_hint: Suggested fix or direction (for FAIL/WARNING)
- resolved_at: ISO timestamp (only for resolved entries)
-->

| status | severity | reviewed_at | task_id | criterion_failed | evidence | fix_hint | resolved_at |
|--------|----------|-------------|---------|------------------|----------|----------|-------------|
| [STATUS] | [severity] | [ISO timestamp] | [task_id] | [criterion] | [evidence] | [hint] | [ISO timestamp or empty] |
