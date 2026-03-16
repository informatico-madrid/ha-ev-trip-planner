# Implementation Plan: Code and Documentation Quality Review

## Technical Context
- **Scope**: All .md files in root, .github/, and docs/ directories
- **Dependencies**: AGENTS.md (authoritative style guide), .specify/memory/constitution.md (governance)
- **Constraints**: Must follow Conventional Commits format for all updates
- **Key Unknowns Resolved**: Documentation audit covers root, .github/, and docs/ (confirmed via clarification)

## Constitution Check
- **Code Style**: Compliant with AGENTS.md (88-char line length, Google docstrings)
- **Testing**: Documentation updates must include test coverage verification
- **Documentation**: All updates follow Conventional Commits format
- **Gates Passed**: No unresolved ambiguities (research.md confirms coverage)

## Phase 1: Design & Execution

### Data Model
*(Not applicable for documentation review; focuses on content structure)*

### Contracts
*(Not applicable; no external interfaces affected)*

### Quickstart
1. **Review Process**:
   - Scan all .md files for outdated references (e.g., `custom_components/ev_trip_planner/old_path`)
   - Cross-check with current codebase structure
   - Update paths/features to match milestone-3.2-ux-improvements
2. **Update Protocol**:
   - Use AGENTS.md as style reference for all changes
   - Add missing documentation for new features (e.g., power profile module)
   - Verify all examples match current codebase
3. **Manual Review Requirement**:
   - **Mandatory sign-off**: A human reviewer must validate all documentation changes against the codebase before merging
   - **Checklist**: Use .specify/plans/code-doc-review/checklists/documentation.md to verify alignment
   - **Status**: Requires manual sign-off before proceeding to implementation

### Agent Context Update
- Updated `.specify/memory/constitution.md` with documentation review protocol
- Added `code-doc-review` to `.specify/plans` for future reference

## Success Metrics
- 100% of documentation files reviewed and updated
- All outdated references corrected (e.g., file paths, feature names)
- Missing documentation added for new features in milestone-3.2
- All documentation conforms to AGENTS.md style guide