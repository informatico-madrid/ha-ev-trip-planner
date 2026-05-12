# E2E Diagnosis — Methodical Debugging Workflow

## Goal

Fix all E2E test failures to the state before spec/3-solid-refactor began (all tests passing).
This is the **control gate**: if E2E tests fail at the end, the spec is NOT complete.

## Directory Layout

```
e2e-diagnosis/
  results/          # Persistent test result snapshots (never auto-deleted)
  errors.md         # Active error registry (updated as errors are fixed/cascaded)
  done.md           # Archive of fixed errors with before/after evidence
```

## Pipeline

Each phase runs **after** all higher-priority errors are resolved.

### Phase 1: Baseline & Discovery

| # | Action |
|---|--------|
| 1 | Archive all existing test-results dirs: `cp -r test-results/ test-results1/ test-results2/ e2e-diagnosis/results/ 2>/dev/null` |
| 2 | Run `make e2e` (full suite) |
| 3 | Copy results to persistent archive: `cp -r test-results/ e2e-diagnosis/results/e2e-run-N/` |
| 4 | Run `make e2e-soc` (full suite) |
| 5 | Copy results to persistent archive: `cp -r test-results/ e2e-diagnosis/results/e2e-soc-run-N/` |
| 6 | Parse all `e2e-diagnosis/results/` into `errors.md` with unique error signatures |

### Phase 2: Fix Cascade (Iterative)

Repeat until no errors remain:

1. **Pick highest-priority error** from `errors.md` (priority = affects most other tests)
2. **Read saved results** from `e2e-diagnosis/results/` — never from live `test-results/` (gets wiped)
3. **Reproduce in staging** (`:8124` Docker):
   - Delete existing vehicle in HA UI
   - Create new one with exact test data from saved screenshots
   - Read Docker logs in real-time
4. **Fix the bug** in source code
5. **Verify in staging**: recreate, check logs are clean
6. **Verify with tests**: run affected full suite (`make e2e` or `make e2e-soc`)
7. **Move error to done.md** with before/after evidence
8. **Re-parse remaining errors**: fixes cascade — earlier fix may eliminate multiple listed errors
9. **Update `errors.md`** with deduped remaining errors

### Phase 3: Final Verification

1. Archive: `cp -r test-results/ e2e-diagnosis/results/final-e2e/ 2>/dev/null`
2. Run `make e2e` — all 30 tests must pass
3. Archive: `cp -r test-results/ e2e-diagnosis/results/final-e2e-soc/ 2>/dev/null`
4. Run `make e2e-soc` — all 10 tests must pass

## Error Registry Schema

Each entry in `e2e-diagnosis/errors.md`:

```markdown
### ERR-NNN: Short description
- **Test**: spec-file.spec.ts — test name
- **Error**: Log message + line reference
- **Source**: file.py:line — root cause file
- **Severity**: Critical (blocks N tests) / High / Medium / Low
- **Status**: Open | Fixing | Fixed | Cascaded (resolved by other fix)
- **Evidence**: `e2e-diagnosis/results/...` paths + screenshots + staging logs
- **Fix**: What changed and how to verify
```

## Rules

1. **NEVER** run `make e2e` and `make e2e-soc` in parallel — shared Docker HA state collides
2. **NEVER delete** `e2e-diagnosis/results/` — this is debugging gold
3. **Always reproduce in staging first** — Docker logs at `:8124` are faster than full E2E reruns
4. **One fix at a time** — run full suite after each fix to detect cascade improvements
5. **Track cascades explicitly** — a fix may resolve errors you haven't investigated yet
6. **Document every error** — even "Cascaded" ones go in done.md with explanation

## Priority Heuristic

Fix in this order:

1. **Critical**: Index exhaustion / resource leaks — blocks all multi-trip scenarios
2. **High**: Trip publish failures (deadline errors, missing data)
3. **Medium**: Sensor creation failures / duplicate entities — functional but noisy
4. **Low**: Cosmetic / timing issues — rare, environment-dependent

## Completion Criteria

- [ ] `make e2e` passes all tests (same count as pre-spec state)
- [ ] `make e2e-soc` passes all tests (same count as pre-spec state)
- [ ] All errors in `errors.md` moved to `done.md` or marked Cascaded
- [ ] No new errors introduced by refactoring
