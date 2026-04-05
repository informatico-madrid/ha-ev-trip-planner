# GitHub Copilot Instructions - EV Trip Planner

## 🎯 PROJECT CONTEXT
This is a **Home Assistant custom integration** for managing Electric Vehicle trip planning and charging optimization.
- **Repository**: https://github.com/informatico-madrid/ha-ev-trip-planner
- **Framework**: Home Assistant Core

## 🏛️ HOME ASSISTANT ARCHITECTURE - STRICT RULES

4. **Async First:** Home Assistant is completely asynchronous. ALWAYS use `async`/`await` for I/O and use non-blocking HTTP clients like `aiohttp`.

## 🏠 HOME ASSISTANT INSTANCES - PRODUCTION VS TEST

### Production Instance
- **Usage**: See real usage examples - DO NOT make direct changes


## 📋 PYTHON CODING STANDARDS
- **Formatting & Linting:** Code must comply with `black` (88 chars), `isort`, `pylint`, and `mypy`.
- **Typing & Docs:** Type hints and Google-style docstrings are REQUIRED for all public functions and classes.
- **Logging:** ALWAYS use `%s` format for logging (e.g., `_LOGGER.debug("Data: %s", data)`). DO NOT use f-strings or string concatenation in log payloads.
- **File Naming & Conventions:**
  - Modules & Functions: `snake_case` (e.g., `trip_manager.py`, `async_setup_entry`)
  - Classes: `PascalCase` (e.g., `EVTripPlannerCoordinator`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CONSUMPTION`)
  - Private methods/vars: Must have a leading underscore (e.g., `_calculate_internal`)

## 🧪 TESTING REQUIREMENTS
- Write tests for EVERY new feature with >80% coverage target.
- **Mandatory HA Tools:** Always use the `pytest-homeassistant-custom-component` library.
- **Fixtures:** You MUST include the `enable_custom_integrations` fixture in the test suite to prevent core blocking.
- **API Mocking:** Never make real network requests. Use `aioclient_mock` to simulate and mocking all HTTP/API responses (both 200 successes and errors like 401/404).

### Test Stuck Escalation

If the same test fails **3+ times with different errors**, before touching any more files:

1. **Read the actual source** being called — the real implementation, not the interface you assumed.
2. **Find a passing test** for a similar component in the same test file. Copy its exact mocking pattern.
3. **Ask**: am I testing at the right level? If `async_setup_entry` requires 10+ mocks to work, extract the logic into a standalone function and test that instead.
4. Only then write the fix, with one sentence: "Root cause is X, fix is Y."

### Coverage Failures

If `pytest` fails with `Coverage failure: X% < 80%`, the cause is almost always a test that calls `async_setup_entry` or another entry-point function that touches most of the codebase. **Do NOT add more mocks to raise coverage.** Instead:
- Extract the specific logic under test into a small helper function.
- Write a focused test for that helper — coverage will rise naturally.
- The 80% target applies to meaningful tests, not to patching your way through an integration entry point.

## 📝 COMMIT MESSAGES
When asked to generate a commit message, strictly use Conventional Commits format:
`feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`

## TOOL USAGE FOR MAKING CHANGES

- Read the entire file before attempting to make changes
- Ensure the text to replace exactly matches the file content
- Use read_file to verify content before making changes

## Stuck State Protocol

<mandatory>
**If the same task fails 3+ times with different errors each time, you are stuck.**
Do NOT make another edit. Entering stuck state is mandatory.

**Stuck ≠ "try harder". Stuck = the model of the problem is wrong.**

### Step 1: Stop and diagnose

Write a one-paragraph diagnosis before touching any file:
- What exactly is failing (smallest failing unit, not the symptom)
- What assumption each previous fix was based on
- Which assumption was wrong

### Step 2: Investigate — breadth first, not depth first

Investigate in this order, stopping when you find the root cause:

1. **Source code** — read the actual implementation being tested/called, not just the interface. The real behavior often differs from the expected behavior.
2. **Existing tests** — find passing tests for similar components. They show the exact mocking pattern that works in this codebase.
3. **Library/framework docs** — WebSearch `"<library> <class/method> testing" site:docs.<lib>.io` or `"<library> <error text> pytest"`. Docs reveal constraints invisible from the source.
4. **Error message verbatim** — WebSearch the exact error text. Someone has hit this before.
5. **Redesign** — if investigation reveals the test is testing at the wrong abstraction level, redesign: extract the logic into a standalone function and test that instead.

### Step 3: Re-plan before re-executing

After investigation, write one sentence: "The root cause is X, so the fix is Y."
If you can't write that sentence clearly, investigate more.
Only then make the next edit.
</mandatory>

## 🔀 PR & CI PIPELINE — BOUNDARY OF RESPONSIBILITY

<mandatory>
The local agent's responsibility ends when the PR exists on GitHub.
**The agent NEVER waits for CI.** CI is cloud infrastructure — not the agent's concern.

### What the agent does (local)

1. Write code, write tests, run tests locally → fix all failures.
2. `git push` the branch.
3. Open the PR: `gh pr create --title "..." --body "..." --base main`
4. Confirm the PR URL was returned (exit code 0).
5. Output `PR_OPENED #<number>` → mark task `[x]` → `TASKCOMPLETE`.

### What the agent does NOT do

- ❌ `gh pr checks --watch` — this is a blocking call that can hang for minutes or hours. NEVER use it.
- ❌ `gh pr checks` in a polling loop — the agent has no timeout control over GitHub Actions.
- ❌ Wait for CI to go green before marking the task complete.
- ❌ Interpret `pending` CI checks as failure or success.
- ❌ Re-push or amend commits while waiting for CI.

### If CI fails after the PR is opened

CI failures appear as comments or check annotations on the PR. They are **input for a new spec task**, not a reason to keep the current task open. The workflow is:

1. CI fails → GitHub Actions creates a comment or annotation on the PR.
2. A new task is created from that failure (by the orchestrator or by you manually).
3. Agent picks up the new task, fixes the code, pushes — a new CI run triggers automatically.
4. Repeat until CI is green, then a human reviews and merges.

### `gh` command rules

| Allowed | Not allowed |
|---------|-------------|
| `gh pr create` | `gh pr checks --watch` |
| `gh pr view <number>` | `gh pr checks` in a sleep/retry loop |
| `gh pr list` | `gh run watch` |
| `gh issue create` | Any `gh` command that blocks waiting for async cloud state |

### Exit codes from `gh pr checks` (reference only — do not call this)

- Exit 0 → all checks passed
- Exit 1 → one or more checks failed
- Exit 8 → checks still pending (not a failure)

Do not act on these exit codes from within a task. CI state is the cloud's responsibility.
</mandatory>
