<!-- Sync Impact Report -->
<!-- Version: 0.1.0 → 1.0.0 -->
<!-- Principles: Added Code Style, Testing, Documentation -->
<!-- Templates updated: .specify/templates/plan-template.md, .specify/templates/spec-template.md, .specify/templates/tasks-template.md -->
<!-- TODO: Update .specify/templates/commands/*.md for agent-specific terms -->

# ha-ev-trip-planner Constitution

**Version**: 1.0.0
**Ratification Date**: 2026-03-13
**Last Amended**: 2026-03-13

## Principles

### Code Style
MUST adhere to the following coding standards:
- Line length: 88 characters
- Type hints: Required for all public functions
- Docstrings: Google style, required for all public functions
- Imports: Standard lib → Third party → HA → Local (use isort)
- Async: Always use `async`/`await`, no blocking calls

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
