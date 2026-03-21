---
description: Execute the implementation planning workflow using the plan template to generate design artifacts.
handoffs: 
  - label: Create Tasks
    agent: speckit.tasks
    prompt: Break the plan into tasks
    send: true
  - label: Create Checklist
    agent: speckit.checklist
    prompt: Create a checklist for the following domain...
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Setup**: Run `.specify/scripts/bash/setup-plan.sh --json` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load context**: Read FEATURE_SPEC and `.specify/memory/constitution.md`. Load IMPL_PLAN template (already copied).

3. **Execute plan workflow**: Follow the structure in IMPL_PLAN template to:
   - Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
   - Fill Constitution Check section from constitution
   - Evaluate gates (ERROR if violations unjustified)
   - Phase 0: Generate research.md (resolve all NEEDS CLARIFICATION)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md
   - Phase 1: Update agent context by running the agent script
   - Re-evaluate Constitution Check post-design

## State Verification Plan

### ⚠️ IMPORTANT: Only 3 Verification Types (CLOSED set)

| Verification Type | When to Use | Example Command (not a new type!) |
|------------------|-------------|-----------------------------------|
| `[VERIFY:TEST]` | Unit/integration tests (pytest) | `pytest tests/ -v --cov` |
| `[VERIFY:API]` | REST API verification (curl/MCP to HA) | `curl http://HA/api/states/sensor.xxx` |
| `[VERIFY:BROWSER]` | Playwright/Selenium UI automation | `npx playwright test` |

**RULES:**
- ✅ ONLY these 3 types are valid in tasks
- ✅ Details of HOW to verify (services, logs, dashboard, etc.) are decided per-task in the task description
- ❌ DO NOT add more verification types like `[VERIFY:SERVICES]`, `[VERIFY:LOGS]`, `[VERIFY:LOVELACE]`
- ❌ The "Example Command" column shows HOW to use each type - it's NOT a new verification type

4. **Tool Requirements Check** *(REQUIRED before generating tasks)*:
   - Analyze the generated plan.md for required technologies
   - **SEARCH AND INSTALL** skills/MCPs from official libraries
   - Allow the agent to DECIDE which tools are needed based on the specific task context
   
   **Technology Discovery Process**:
   a. Identify required technologies from plan.md (Python, Home Assistant, Docker, etc.)
   b. Search available skills/MCPs that match these technologies
   c. Use available skill registry to find matching tools
   d. Let the agent DECIDE the best mapping based on task requirements
   e. Install the selected skills/MCPs
   
   **SUGGESTED Skill Mappings** (NOT hardcoded - agent decides):
   | Technology | Possible Skill/MCP |
   |------------|---------------------|
   | Home Assistant | homeassistant-skill, homeassistant-ops, homeassistant-config, homeassistant-dashboard-designer |
   | REST API | homeassistant-ops, http-tools |
   | Python Tests | python-testing-patterns |
   | E2E/Playwright | e2e-testing-patterns |
   | Docker | docker-essentials |
   | Linux Admin | linux-administration |
   | GIS/Geolocation | gis |
   | Python Security | python-security-scanner |
   | Python Performance | python-performance-optimization |
   
   **REQUIRED ACTIONS**:
   a. Search official skill registries (npm, pip, GitHub, skill stores)
   b. Let agent decide which skills match the task best
   c. Install selected skills/MCPs
   d. **LIST available skills in plan output** (agent decides which to use)
   
   **Output**: 
   - List all available skills/MCPs found
   - Agent will select appropriate tools per task in speckit.tasks phase

5. **Stop and report**: Command ends after Phase 2 planning. Report branch, IMPL_PLAN path, and generated artifacts.

## Phases

### Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:

   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Define interface contracts** (if project has external interfaces) → `/contracts/`:
   - Identify what interfaces the project exposes to users or other systems
   - Document the contract format appropriate for the project type
   - Examples: public APIs for libraries, command schemas for CLI tools, endpoints for web services, grammars for parsers, UI contracts for applications
   - Skip if project is purely internal (build scripts, one-off tools, etc.)

3. **Agent context update**:
   - Run `.specify/scripts/bash/update-agent-context.sh copilot`
   - These scripts detect which AI agent is in use
   - Update the appropriate agent-specific context file
   - Add only new technology from current plan
   - Preserve manual additions between markers

4. **State Verification Plan** *(if feature involves HA)*:
   - Define in plan.md the section ## State Verification Plan with Existence Check and Effect Check
   - This plan is required by speckit.implement before marking tasks [x]

**Output**: data-model.md, /contracts/*, quickstart.md, agent-specific file, state-verification-plan

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications
