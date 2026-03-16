---
description: "Task list for Code and Documentation Quality Review"
---

# Tasks: Code and Documentation Quality Review

**Input**: Design documents from `.specify/plans/code-doc-review/` (`impl-plan.md`, `research.md`)
**Prerequisites**: `impl-plan.md` present in the same directory

## Phase 1: Setup (Shared Infrastructure)

Purpose: Create reusable artifacts and tools to support the documentation audit.

- [ ] T001 [P] Create checklist file `.specify/plans/code-doc-review/checklists/documentation.md` containing the audit checklist and sign-off fields (follow `AGENTS.md` style rules)
- [ ] T002 [P] Add audit script `.specify/tools/doc_audit.py` that: scans the repository for `*.md`, extracts path-like references (e.g. `custom_components/ev_trip_planner/...`), and reports occurrences as JSON to `.specify/plans/code-doc-review/reports/audit-report.json`
- [ ] T003 [P] Create reports directory `.specify/plans/code-doc-review/reports/` and add an empty `README.md` explaining report files

---

## Phase 2: Foundational (Blocking prerequisites)

Purpose: Generate data and human-readable summaries that drive the manual edits below.

- [ ] T004 Run the audit script and write results to `.specify/plans/code-doc-review/reports/audit-report.json`
- [ ] T005 Summarize the audit into `.specify/plans/code-doc-review/reports/audit-summary.md` with actionable items grouped by target file

---

## Phase 3: User Story 1 - Root & GitHub docs audit (Priority: P1)

Goal: Ensure root-level documentation and `.github/` guidance are accurate and reference existing code.

Independent Test: All file-path references in `CHANGELOG.md`, `README.md`, and `ROADMAP.md` resolve to existing files or modules.

- [ ] T006 [US1] Use the audit report to update `CHANGELOG.md` at repository root: fix outdated file paths and feature names so every path points to an existing file
- [ ] T007 [P] [US1] Update `README.md` to reflect current installation and example configuration; ensure examples reference `custom_components/ev_trip_planner` paths that exist
- [ ] T008 [P] [US1] Update `ROADMAP.md` to reflect current milestones and remove or annotate entries that no longer apply to `milestone-3.2-ux-improvements`
- [ ] T009 [US1] Update any `.github/` guidance or CI docs referenced from root (if present), ensuring links and command examples are current

---

## Phase 4: User Story 2 - `docs/` directory audit (Priority: P2)

Goal: Bring `docs/` files in line with the codebase and remove stale statements.

Independent Test: No remaining audit-report entries point at files inside `docs/` that reference non-existing code paths.

- [ ] T010 [US2] Update `docs/IMPROVEMENTS_POST_MILESTONE3.md` to remove or correct outdated references found in the audit
- [ ] T011 [US2] Update `docs/ISSUES_CLOSED.md` and `docs/ISSUES_CLOSED_MILESTONE_3.md` to ensure issue descriptions, code references, and test links are accurate
- [ ] T012 [US2] Update `docs/MILESTONE_3_NEXT_STEPS.md` to reflect the current next steps and owners
- [ ] T013 [P] [US2] Review and update `docs/MILESTONE_4_1_PLANNING.md` and `docs/MILESTONE_4_POWER_PROFILE.md` for consistency with implemented tests and modules

---

## Phase 5: User Story 3 - New feature docs (Priority: P3)

Goal: Add or improve documentation for features introduced in milestone-3.2 (e.g., power profile).

Independent Test: New docs exist and examples reference real modules and tests.

- [ ] T014 [P] [US3] Add `docs/power_profile.md` (or update `docs/MILESTONE_4_POWER_PROFILE.md`) with: overview, configuration examples, relevant entity names (eg. `sensor.<vehicle>_power_profile`), and links to implementation files
- [ ] T015 [P] [US3] Add usage examples in `README.md` or `docs/examples.md` showing how to configure and read the new sensors/services added in milestone-3.2

---

## Phase N: Polish & Sign-off

- [ ] T016 [ ] Manual sign-off: a human reviewer must validate all documentation changes using `.specify/plans/code-doc-review/checklists/documentation.md` and approve the PR
- [ ] T017 [ ] Commit message and changelog: ensure all documentation commits follow Conventional Commits and update `CHANGELOG.md` with a brief summary of doc changes

---

## Dependencies & Execution Order

- **Setup**: T001–T003 can run in parallel
- **Foundational**: T004–T005 must complete before user-story edits begin
- **User Stories**: T006–T015 depend on Foundational completion; stories may proceed in parallel where marked `[P]`
- **Sign-off**: T016–T017 require completion of all user-story tasks

## Notes

- Use the audit report at `.specify/plans/code-doc-review/reports/audit-report.json` as the source of truth for outdated references
- Keep changes small and scoped per file to make review easy
- Follow `AGENTS.md` style rules (88-char lines, Google docstrings for code samples)
