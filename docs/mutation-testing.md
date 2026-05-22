# Mutation Testing

Mutation testing validates test quality by introducing small bugs ("mutants") into
the source code and checking if the test suite kills them.

## Make Targets

```bash
make mutation        # Run mutation testing (mutmut)
make mutation-gate   # Check per-module kill rate thresholds
make mutation-unregistered-check  # Phase 5 persistence gate: fail if any survivor has no registry entry
```

## Phase 5: Effective-100% MSI

Starting 2026-05-22, the project uses **effective-MSI** (Mutant Score Index) instead of
raw mutation score:

```
effective_MSI = killed / (total_mutants - registered_equivalent)
```

- `killed` = mutants killed by tests
- `total_mutants` = total generated (includes unchanged)
- `registered_equivalent` = mutants in `specs/mutation-score-ramp/equivalent-mutants.md`
  with status `REGISTERED-AUTO` or `HUMAN-APPROVED`

## Equivalent-Mutant Registry

See `specs/mutation-score-ramp/equivalent-mutants.md` for the full registry of genuine
equivalent mutants. Each entry has a dossier justifying why it's unkillable.

### Categories

- **`REGISTERED-AUTO`**: Pre-authorized (idempotent-arithmetic, log/diagnostic-only,
  performance-only, type-infeasible-default). Auto-registered with `# pragma: no mutate`.
- **`HUMAN-APPROVED`**: Framework-absorbed or ambiguous — reviewed and approved by human.
- **`CANDIDATE-PENDING-APPROVAL`**: Parked for human review at task 5.6.
- **`REJECTED`**: Returned to kill queue after human rejection.

## Persistence Gate (Task 5.5)

The persistence gate ensures no new unregistered survivors slip through:

```bash
make mutation-unregistered-check
# Fails if any survived mutant has no corresponding entry in equivalent-mutants.md
```

When adding new code/tests, any new surviving mutant must be either:
1. **Killed** — strengthen existing tests or add new ones
2. **Registered** — add a dossier to `equivalent-mutants.md` with justification

**Never** add `# pragma: no mutate` without a corresponding registry entry and
approval. This prevents the mass-pragma gaming that failed before (153 unapproved
pragmas in the prior approach).
