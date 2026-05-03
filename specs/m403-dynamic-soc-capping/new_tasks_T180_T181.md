
---

- [ ] T180 **Fix variable shadowing regression in emhass_adapter.py:1126-1135** — CRITICAL REGRESSION from T176/T177

The pyright fixes in T176/T177 added `trip: dict[str, Any] = {}` at line 1128 which shadows the trip variable from tuple unpacking. In the else branch (fallback path when trip_deadlines is empty), `trip_id = trip.get("id")` uses the empty dict instead of the actual trip from the tuple, so trip_id is always None and `if not trip_id: continue` skips ALL trips.

**CURRENT CODE (BROKEN)**:
```python
for item in trips_to_process:
    trip_id: str | None = None
    trip: dict[str, Any] = {}    # <-- BUG: shadows trip from tuple
    if trip_deadlines:
        trip_id, deadline_dt, trip = item
    else:
        trip_id = trip.get("id")  # trip is {} -> None -> continue skips!
        deadline_dt = None
    if not trip_id:
        continue
    assert isinstance(trip_id, str)
```

**CORRECT FIX**:
```python
for item in trips_to_process:
    if trip_deadlines:
        trip_id, deadline_dt, trip = item
    else:
        _, _, trip = item  # Unpack trip from the fallback tuple (None, None, trip)
        trip_id = trip.get("id")
        deadline_dt = None
    if not trip_id:
        continue
    assert isinstance(trip_id, str)
```

**Steps**:
1. Read `custom_components/ev_trip_planner/emhass_adapter.py` lines 1126-1140
2. Remove `trip_id: str | None = None` at line 1127
3. Remove `trip: dict[str, Any] = {}` at line 1128
4. Add `_, _, trip = item` in the else branch BEFORE `trip_id = trip.get("id")`
5. Run: `python3 -m pytest tests/test_emhass_adapter_trip_id_coverage.py tests/test_emhass_adapter.py::test_async_publish_all_deferrable_loads_populates_per_trip_cache -x --tb=short -q` -> verify 3/3 PASS
6. Run: `python3 -m pyright custom_components/ev_trip_planner/emhass_adapter.py 2>&1 | tail -3` -> verify 0 errors (pyright should still pass because trip is always bound before use)
7. Run: `python3 -m pytest tests/ -q --tb=no 2>&1 | tail -3` -> verify 0 failed

- **Done when**: `python3 -m pytest tests/test_emhass_adapter_trip_id_coverage.py tests/test_emhass_adapter.py::test_async_publish_all_deferrable_loads_populates_per_trip_cache -q 2>&1 | tail -3` shows 3 passed AND `python3 -m pyright custom_components/ev_trip_planner/emhass_adapter.py 2>&1 | tail -3` shows 0 errors
- **Verify**: `python3 -m pytest tests/test_emhass_adapter_trip_id_coverage.py tests/test_emhass_adapter.py::test_async_publish_all_deferrable_loads_populates_per_trip_cache -q 2>&1 | grep -c PASSED` returns 3
- **Checkpoint**: `python3 -m pytest tests/ -q --tb=no 2>&1 | tail -3` -> 0 failed

---

- [ ] T181 **ruff format: Fix format regression on emhass_adapter.py**

The T176/T177 changes to emhass_adapter.py introduced formatting violations. `ruff format --check` reports 1 file needs reformatting.

**Steps**:
1. Run: `python3 -m ruff format custom_components/ev_trip_planner/emhass_adapter.py`
2. Run: `python3 -m ruff format --check custom_components/ tests/ 2>&1 | tail -3` -> verify 0 files would be reformatted
3. Run: `python3 -m pytest tests/ -q --tb=no 2>&1 | tail -3` -> verify 0 failed

- **Done when**: `python3 -m ruff format --check custom_components/ tests/` exits with code 0
- **Verify**: `python3 -m ruff format --check custom_components/ tests/ 2>&1 | grep "Would reformat" && echo "FAIL" || echo "PASS"`
- **Checkpoint**: `python3 -m pytest tests/ -q --tb=no 2>&1 | tail -3` -> 0 failed

---

Quality Gate QG19-FINAL-V2: After T180-T181, re-run the full Quality Gate:
1. `python3 -m ruff check custom_components/ tests/ 2>&1 | tail -3` -> 0 errors
2. `python3 -m ruff format --check custom_components/ tests/ 2>&1 | tail -3` -> 0 files to format
3. `python3 -m pyright custom_components/ 2>&1 | tail -5` -> 0 errors
4. `python3 -m pytest tests/ -q --tb=no 2>&1 | tail -3` -> 0 failed
5. `python3 -m pytest tests/ --cov=custom_components.ev_trip_planner --cov-report=term-missing -q 2>&1 | grep "TOTAL"` -> 100%
6. `make e2e 2>&1 | tail -10` -> all E2E tests pass
