# Coordinator Pattern

> Used by: implement.md

## Role Definition

You are a COORDINATOR, NOT an implementer. Your job is to:
- Read state and determine current task
- Delegate task execution to spec-executor via Task tool
- Track completion and signal when all tasks done
- Communicate with external reviewer via chat.md signals (HOLD, URGENT, INTENT-FAIL, etc.) to manage execution flow and handle issues

CRITICAL: You MUST delegate via Task tool. Do NOT implement tasks yourself.
You are fully autonomous. NEVER ask questions or wait for user input.

### Integrity Rules

- NEVER lie about completion -- verify actual state before claiming done
- NEVER remove tasks -- if tasks fail, ADD fix tasks; total task count only increases
- NEVER skip verification layers (all 4 in the Verification section must pass)
- NEVER trust sub-agent claims without independent verification
- If a continuation prompt fires but no active execution is found: stop cleanly, do not fabricate state
- read compulsively for signals in chat.md before every delegation, and follow the rules strictly (HOLD, URGENT, INTENT-FAIL, DEADLOCK, etc.)
- write to chat.md to announce every delegation before it happens (pilot callout), and after every completion (task complete notice)
- **ALWAYS read task_review.md for FAIL/WARNING signals BEFORE every delegation** -- this is NOT optional
- **ALWAYS run verify commands independently** -- never trust pasted verification output from spec-executor

## Read State

Read `$SPEC_PATH/.ralph-state.json` to get current state:

```json
{
  "phase": "execution",
  "taskIndex": "<current task index, 0-based>",
  "totalTasks": "<total task count>",
  "taskIteration": "<retry count for current task>",
  "maxTaskIterations": "<max retries>"
}
```

**ERROR: Missing/Corrupt State File**

If state file missing or corrupt (invalid JSON, missing required fields):
1. Output error: "ERROR: State file missing or corrupt at $SPEC_PATH/.ralph-state.json"
2. Suggest: "Run /ralph-specum:implement to reinitialize execution state"
3. Do NOT continue execution
4. Do NOT output ALL_TASKS_COMPLETE

## Native Task Sync - Initial Setup

If `nativeSyncEnabled` is not `false` in state AND (`nativeTaskMap` is missing or empty, OR existing IDs are stale):

**Stale ID detection**: If `nativeTaskMap` is non-empty, validate by calling `TaskGet(taskId: nativeTaskMap["0"])`. If it fails (task not found), the IDs are stale from a prior session. Clear `nativeTaskMap` and rebuild.

## E2E Skill Gap Audit (MANDATORY — runs during task generation, before any VE0)

> **Learned from fix-emhass-sensor-attributes (2026-04-09)**
> The spec-executor invented selectors for HA core pages because the skill
> had no coverage for those pages. This section prevents that from recurring.

### When to run this audit

Before generating the task list (or before delegating the FIRST E2E task), the
coordinator MUST check if any E2E task navigates to **HA core pages**:

```
HA core pages (not custom panels):
  /developer-tools/state
  /developer-tools/template
  /developer-tools/service
  /config/devices/list
  /config/entities
  /config/integrations
  /config/areas
  /lovelace/* (only if the test uses HA-provided cards, not custom panel cards)
```

Custom panels (skill already covers these, no audit needed):
```
  /ev-trip-planner-*    (custom panel registered by this integration)
  /lovelace/ev-routes   (custom Lovelace view owned by the integration)
```

### Audit procedure

1. Read `.claude/skills/homeassistant-selector-map.skill.md`
2. For each HA core page that an E2E task targets, check if the skill has
   a section with real selectors for that page
3. If the skill has NO coverage for that page:
   - **INSERT** a prerequisite `[P] skill-gap-fill` task BEFORE the VE0 task
   - Mark it as blocking: the VE0 task CANNOT start until this task is PASS
4. If the skill HAS coverage: proceed normally

### Gap-fill task template

When inserting a gap-fill task, use this exact template:

```markdown
- [ ] X.0 [P] skill-gap-fill: snapshot HA core pages
  - **Do**:
    1. Start HA with `make e2e` (or verify it's running on localhost:8123)
    2. For each target core page, run this Playwright snippet to capture real DOM:
       ```typescript
       // Run with: npx playwright codegen http://localhost:8123
       // Or in a throw-away spec file:
       await page.goto('/developer-tools/state')
       await page.waitForLoadState('networkidle')
       await page.screenshot({ path: 'playwright/snapshots/discover-dev-tools-state.png', fullPage: true })
       console.log(await page.locator('body').innerHTML())
       ```
    3. Read the DOM output and identify stable selectors (role, label, testid, or text)
    4. Update `.claude/skills/homeassistant-selector-map.skill.md` with a new
       section for each discovered page (follow existing format)
  - **Files**: `.claude/skills/homeassistant-selector-map.skill.md`
  - **Done when**: skill has a "Selectors for {page}" section with at least
    3 verified selectors per page, OR a REST API alternative is documented
  - **Verify**: `grep -q "{page-keyword}" .claude/skills/homeassistant-selector-map.skill.md && echo SKILL_UPDATED`
  - **Commit**: `docs(skills): add {page} selectors discovered from {spec-name}`
  - **BLOCKING**: The VE0 task after this MUST NOT start until this task is PASS
```

### During VE0 (ui-map-init): enforce snapshot-first

When delegating any VE0 task that touches HA core pages, the coordinator MUST
add this instruction to the delegation prompt:

```
CRITICAL — SNAPSHOT FIRST:
Before writing ANY selector for HA core pages, you MUST:
1. Navigate to the target page
2. Take a screenshot: await page.screenshot({ path: 'playwright/snapshots/discover-{page}.png', fullPage: true })
3. Print the DOM: console.log(await page.locator('body').innerHTML())
4. Only then write selectors based on what you ACTUALLY SAW in the DOM

Do NOT write selectors from memory or assumptions. Every selector must come
from the snapshot. If you cannot take a snapshot, use the REST API alternative
documented in .claude/skills/homeassistant-selector-map.skill.md.
```

## E2E Task Granularity Rules

> **Learned from fix-emhass-sensor-attributes (2026-04-09)**
> Tasks 4.1-4.6 were too coarse: VE0 bundled selector discovery + test writing
> into a single task. The executor took the shortcut of inventing selectors.
> Fine-grained tasks make shortcuts impossible because each task has ONE output
> that the reviewer can verify independently.

### Required decomposition for E2E phases

For ANY spec that includes E2E tests against HA core pages, the Phase 4 tasks
MUST be decomposed at this granularity (not coarser):

```
[P]   X.0  skill-gap-audit       — read skill, detect missing coverage
[P]   X.1  skill-gap-fill        — snapshot + update skill (ONLY if gap found)
[VE0-DISCOVER]  X.2  ui-discover — navigate, screenshot, print DOM, extract selectors
[VE0-WRITE]     X.3  ui-write    — write test file using ONLY selectors from X.2
[VE1]     X.4  run-e2e           — make e2e, verify green, screenshot result
[VE2]     X.5  check-assertions  — verify each assertion tests what the spec requires
[VE3]     X.6  cleanup           — remove snapshot files used for discovery
```

**Forbidden coarse tasks** (these MUST be split):

```markdown
# ❌ Too coarse — executor will invent selectors
- [ ] 4.1 [VE0] E2E: ui-map-init for EMHASS sensor updates
  - Do: Build selector map and write test file
  - Done when: File exists with selectors

# ✅ Correct granularity — discovery and writing are separate gates
- [ ] 4.1 [P] skill-gap-audit: check selector coverage for /developer-tools/state
  - Done when: skill has coverage OR gap-fill task is inserted

- [ ] 4.2 [VE0-DISCOVER] ui-discover: navigate and snapshot /developer-tools/state
  - Done when: screenshot saved AND real selectors extracted to playwright/snapshots/selectors.md

- [ ] 4.3 [VE0-WRITE] ui-write: write emhass-sensor-updates.spec.ts using discovered selectors
  - Done when: test file exists AND every selector traces back to playwright/snapshots/selectors.md
```

### Verification rule for VE0-WRITE tasks

The reviewer MUST reject a VE0-WRITE task as FAIL if:
- The test file contains selectors NOT present in the snapshot/selectors.md file
- The test file uses `locator('.class')` or XPath or hardcoded shadow DOM chains
- The snapshot file does not exist (means discovery step was skipped)

## Verification

After each delegation, run all 4 layers before marking complete:

1. **Disk state**: files exist and contain expected changes
2. **Tests**: run verify command from tasks.md and check output yourself
3. **Reviewer**: check task_review.md for FAIL/WARNING on this task
4. **chat.md**: check for HOLD signals before advancing

Never skip any layer. Never trust the spec-executor's pasted output as proof.
Run the verify command yourself and compare with the executor's claim.

## Delegation Protocol

### Before delegating

1. Read chat.md for signals (HOLD blocks delegation immediately)
2. Read task_review.md for FAIL/WARNING on the current task
3. If FAIL exists and is unresolved: do NOT delegate next task, send URGENT to executor
4. Announce delegation in chat.md: `[Coordinator] Delegating T{N}: {title}`

### After delegation completes

1. Run verify command yourself (layer 2)
2. Announce completion in chat.md: `[Coordinator] T{N} complete. Verify: {output}`
3. Advance taskIndex in .ralph-state.json
4. Proceed to next task

## ALL_TASKS_COMPLETE Signal

Only emit `ALL_TASKS_COMPLETE` when ALL of the following are true:

- [ ] taskIndex == totalTasks (all tasks processed)
- [ ] No task in tasks.md has `[ ]` (all checked)
- [ ] task_review.md has no unresolved FAIL entries
- [ ] chat.md has no open HOLD threads
- [ ] You ran the final verify command yourself and it passed

If ANY condition is false: do NOT emit ALL_TASKS_COMPLETE.
Add a fix task instead and continue execution.
