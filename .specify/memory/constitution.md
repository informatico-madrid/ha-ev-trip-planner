<!-- Sync Impact Report -->
<!-- Version: 0.1.0 → 1.0.0 -->
<!-- Principles: Added Code Style, Testing, Documentation -->
<!-- Templates updated: .specify/templates/plan-template.md, .specify/templates/spec-template.md, .specify/templates/tasks-template.md -->
<!-- TODO: Update .specify/templates/commands/*.md for agent-specific terms -->

# ha-ev-trip-planner Constitution

**Version**: 1.0.0
**Ratification Date**: 2026-03-13
**Last Amended**: 2026-03-13

## 🔍 Context Detection

### Context A: Ralph Loop (Implementation Mode)

You are in a Ralph loop if:
- Started by `ralph-loop.sh`
- Prompt mentions "implement spec"
- A `.ralph/state.json` exists and is active

**In this mode:**
- Focus on implementation of the CURRENT task (from tasks.md)
- Complete ALL acceptance criteria in the task's **Done when** field
- Run the **Verify** command to confirm completion
- Mark the task as `[x]` in tasks.md
- Append progress to `progress.txt`
- Output `TASK_COMPLETE` when current task is verified
- Output `ALL_TASKS_COMPLETE` when all tasks in tasks.md are done
- NEVER output completion signals unless the task genuinely passes verification

### Context B: Interactive Chat

When not in a Ralph loop:
- Be helpful and conversational
- Create specs with `/speckit.specify`

---

## Core Principles

### Verification Rules
- DO NOT use screenshot verification - verify using text/element selectors only
- DO NOT use mcp-playwright for screenshot capture - use API or text-based verification

### Code Style
MUST adhere to the following coding standards:
- Line length: 88 characters
- Type hints: Required for all public functions
- Docstrings: Google style, required for all public functions
- Imports: Standard lib → Third party → HA → Local (use isort)
- Async: Always use `async`/`await`, no blocking calls
- use skill home assistant and other good practices skills

### Testing
MUST achieve >80% test coverage for production code.
Tests must be written using pytest with the following command:
`pytest tests/ -v --cov=custom_components/ev_trip_planner`

### Documentation
MUST use Conventional Commits for all changes.
Commit messages must follow the format:
`feat: description`, `fix: description`, `docs: description`, etc.

## Governance
- **Amendment Procedure**: Proposals must be submitted via GitHub issue with rationale. Approved by core team consensus.
- **Versioning**: Follow semantic versioning (MAJOR.MINOR.PATCH).
- **Compliance Review**: All PRs must include a compliance check against this constitution.
