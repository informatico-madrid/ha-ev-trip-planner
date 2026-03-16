# Code and Documentation Quality Review

## User Scenarios
- As a developer, I need to ensure all documentation reflects the current codebase before adding new features.
- As a maintainer, I need to identify outdated documentation to prevent user confusion and support issues.
- As a new contributor, I need clear, accurate documentation to understand the project structure and conventions.

## Functional Requirements
- **Documentation Audit**: Review all .md files in the repository for accuracy against current codebase.
- **Outdated Content Identification**: Flag sections that no longer match the code (e.g., deprecated features, incorrect paths).
- **Missing Documentation**: Identify missing documentation for new features added since last documentation update.
- **Style Compliance Check**: Verify all documentation follows the AGENTS.md style guide and constitution principles.

## Success Criteria
- 100% of documentation files reviewed and updated to reflect current codebase
- All outdated references corrected (e.g., file paths, feature names, configuration options)
- Missing documentation added for new features introduced in milestone 3.2
- All documentation conforms to AGENTS.md style guide (Google docstrings, 88-char line length, etc.)
- No discrepancies between code comments and documentation found

## Key Entities
- `DocumentationFiles`: All .md files in repository (docs/, .github/, root)
- `Codebase`: Current state of custom_components/ev_trip_planner
- `AGENTS.md`: Project's coding standards reference

## Assumptions
- All documentation in `docs/` directory is considered part of the main project documentation
- `AGENTS.md` and `.specify/memory/constitution.md` represent the current authoritative standards
- Recent changes in milestone-3.2-ux-improvements include new features requiring documentation updates

## Compliance Notes
- All documentation must use Conventional Commits format for updates
- No technical implementation details should appear in documentation (e.g., "use async/await" instead of "use Python 3.11 async")
- All examples must match current codebase structure and naming conventions