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


## 📝 COMMIT MESSAGES
When asked to generate a commit message, strictly use Conventional Commits format:
`feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`

## TOOL USAGE FOR MAKING CHANGES

- Read the entire file before attempting to make changes
- Ensure the text to replace exactly matches the file content
- Use read_file to verify content before making changes
- If you are implmenting tasks, always read docs/IMPLEMENTATION_REVIEW.md for any important notes left by the reviewer that may help you in your task.

## Stuck State Protocol

<mandatory>

Los tests e2e se ejecutan con make e2e. tiene un script de lipmieza de carpetas y procesos antes de cada ejecución. 
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