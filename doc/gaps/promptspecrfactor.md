# Prompt: Spec Refactor for SOLID Architecture and 100% Test Coverage

Create a new spec in `specs/solid-refactor-coverage/` to refactor the
source code architecture and achieve 100% test coverage.


## Context


The previous spec (`regression-orphaned-sensors-ha-core-investigation`) resolved
the orphaned sensors bug. Coverage ended up at ~85% because the `trip_manager.py`
module (~224 uncovered lines) and `emhass_adapter.py` have business logic
mixed with I/O and external dependencies (EMHASS, HA APIs), making them
impossible to test without deeply nested test doubles.


## Source of Truth for Test Doubles


**BEFORE deciding which type of double to use in any test, consult
`docs/TDD_METHODOLOGY.md` section `## Layered Test Doubles Strategy` and
`## Test Doubles Reference Table`.**
These two sections are the project's source of truth. Not the criteria of
the moment, not intuition, not "use Mock because it's easy".

The strategy has 3 mandatory layers:
- **Layer 1** — `tests/__init__.py`: Shared Fakes and Stubs (test data,
  `create_mock_*`, setup helpers). Never in `conftest.py`.
- **Layer 2** — Per-method Stubs: override only the specific method that
  needs a different response in that test.
- **Layer 3** — Patch at boundary: `patch()` exclusively at factories
  or dependencies injected by HA, never inside own code.

The table distinguishes: Fake, Stub, Spy, Mock, Fixture, Patch — each with
its use case. A test that is hard to write is a signal of bad design in the
source code, not a signal to add more doubles.

HA Rule of Gold (STRICT): `MagicMock(spec=RealClass)` mandatory for own
classes. Never `MagicMock()` without `spec`.


## Prior Diagnosis

- `trip_manager.py`: God Object class. Mixes persistence, energy calculations,
  EMHASS optimization and state management. The ~224 uncovered lines are EMHASS
  paths that require deeply nested doubles to reach them — clear signal that
  the code needs refactor, not more tests.
- `emhass_adapter.py`: Adapter with embedded business logic. Calls external APIs
  directly without injectable interface. Impossible to test error paths without
  deep Patch.
- `services.py`: Handlers that, although thin after the previous refactor,
  still access `trip_manager` without formal interface abstraction.


## Goal


Refactor the source code applying SOLID principles so that tests are easy to
write using the appropriate double per the table. 100% coverage must be a
consequence of good design, not the direct goal.

Where tests already exist that use `MagicMock()` without `spec`, or
unnecessarily deep Patches, or Fakes/Stubs defined in `conftest.py` instead of
`tests/__init__.py` — refactor those too to align with the Layered Test Doubles
Strategy. Only where it is worth it: if the test passes and the double is
correct for its layer, don't touch it.


## Mandatory Suggested Constraints IMPROVE IF YOU CAN

1. Consult `docs/TDD_METHODOLOGY.md` sections `## Layered Test Doubles
   Strategy` and `## Test Doubles Reference Table` before choosing any
   test double in any task.
2. If a test needs more than 2 levels of double nesting, the signal is to STOP
   and refactor the source code first — don't add more doubles.
3. Do NOT use `# pragma: no cover` except in structurally unreachable code
   documented with explicit reason and human review.
4. Each refactor must be preceded by its RED test before touching the source
   code (strict TDD RED → GREEN → REFACTOR).
5. The `TripManager` and `EmhassAdapter` classes are NOT SOLID today — do not
   write coverage tests on them without refactoring them first.
6. Keep all E2E tests passing at each phase checkpoint.
7. `MagicMock(spec=RealClass)` mandatory. Never `MagicMock()` without `spec`
   for own classes.
8. Shared Fakes/Stubs live in `tests/__init__.py`, not in `conftest.py`.


## Suggested Phases (the spec should develop them with detailed tasks) IT IS ONLY A SUGGESTION IMPROVE IF YOU CAN


### Phase A: Extract Pure Logic
Identify and extract pure functions from `trip_manager.py`:
- Energy calculations (kWh, hours)
- Trip validation
- Trip sorting and filtering
Move to pure modules (`calculations.py` already exists — extend if necessary).
Appropriate double per table: none — they are pure functions, test directly.
Result: these functions are 100% testable without any double.


### Phase B: Protocol for EmhassAdapter
Define `EmhassAdapterProtocol` using `typing.Protocol`.
`EmhassAdapter` implements the protocol (without changing its public interface).
`TripManager` receives the protocol via injection in `__init__`.
Appropriate double per table: Fake (real class with in-memory implementation,
defined in `tests/__init__.py`).
Result: TripManager tests use `FakeEmhassAdapter` — real class, no MagicMock,
no Patch.


### Phase C: Protocol for Storage
Define `StorageProtocol` for trip persistence operations.
`TripManager` receives storage via injection.
Appropriate double per table: Fake (`InMemoryTripStorage`) — real class with
dict in memory, no file I/O or HA Store touch, defined in `tests/__init__.py`.
Result: TripManager tests are synchronous, fast, no HA fixtures.


### Phase D: Consequent Coverage + Cleanup Existing Tests
With Phases A-C complete, the previously unreachable paths are testable with
simple doubles per the table.
Write the missing tests choosing the double per the table in each case.
Review existing tests for:
  - `MagicMock()` without `spec` → replace with `MagicMock(spec=RealClass)`
  - Fakes/Stubs in `conftest.py` that should be in `tests/__init__.py`
  - Patches inside own code (not at boundaries) → refactor
Only correct where the current double is wrong for its layer. Do not touch
tests that are already correct even if they could be written differently.
Target: 100% in `trip_manager.py`, `emhass_adapter.py`, `services.py`.
Prohibited anti-pattern: do not create `*_coverage.py` or `*_coverage2.py` files.
All new tests go to the corresponding canonical files.


### Phase E: Final Checkpoint
- `ruff check` clean
- `mypy` no new errors
- `pytest --randomly-seed=1/2/3` no flaky (3 runs mandatory)
- `make e2e` passes
- `quality_scale.yaml` updated with `test-coverage: done`