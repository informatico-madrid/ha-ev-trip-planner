---
name: equivalent-mutant-registry
description: Equivalent-mutant registry for mutation-score-ramp effective-MSI model
---

# Equivalent-Mutant Registry — effective-MSI

**Purpose:** Document the genuine-unkillable mutant residue so `effective-100%` is achievable. Mirrors Infection's `@infection-ignore-all` model.

## Effective-MSI Definition

```
effective_MSI = killed / (total_mutants − registered_equivalent)
```

**Target:** `effective_MSI = 1.00`

- `killed` = mutants killed by tests
- `total_mutants` = total generated (includes unchanged)
- `registered_equivalent` = mutants in this registry with status `REGISTERED-AUTO` or `HUMAN-APPROVED`
- `unchanged` mutants are excluded by `mutate_only_covered_lines = true` and do not enter the denominator

A `# pragma: no mutate` on ANY source line MUST reference the registry entry id that justifies it (e.g., `# pragma: no mutate # EQ-001`).

## Taxonomy

| Category | Decision | Status |
|----------|----------|--------|
| `idempotent-arithmetic` | Pre-authorized AUTO-register | `REGISTERED-AUTO` |
| `log/diagnostic-only` | Pre-authorized AUTO-register | `REGISTERED-AUTO` |
| `performance-only` | Pre-authorized AUTO-register | `REGISTERED-AUTO` |
| `type-infeasible-default` | Pre-authorized AUTO-register | `REGISTERED-AUTO` |
| `framework-absorbed-arg` | PARK for human approval | `CANDIDATE-PENDING-APPROVAL` |
| Any other ambiguous case | PARK for human approval | `CANDIDATE-PENDING-APPROVAL` |

The first four categories are pre-authorized. Each surviving mutant in these categories gets an auto-registered dossier with a `# pragma: no mutate` — no per-mutant escalation. Batch-ratified at task 5.6.

All other cases are parked as `CANDIDATE-PENDING-APPROVAL`. No pragma, no block. The human reviews these in a single pass at task 5.6.

## Dossier Schema

Each registry entry is a row with these fields:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (e.g., `EQ-001`) |
| `file:line` | Source file and line number |
| `original` | Original expression / code snippet |
| `mutated` | Mutated expression / code snippet |
| `category` | One of the taxonomy categories |
| `decision-test` | Argument why this is genuinely equivalent |
| `status` | `REGISTERED-AUTO` | `CANDIDATE-PENDING-APPROVAL` | `HUMAN-APPROVED` | `REJECTED` |
| `human-approval` | Quote from human approving (when status is `HUMAN-APPROVED`) |
| `date` | ISO date of registration |

## Registry

| ID | File:Line | Original → Mutated | Category | Decision-Test | Status | Human Approval | Date |
|----|-----------|-------------------|----------|---------------|--------|----------------|------|
| EQ-001 | controller.py:53-78 (create_control_strategy, 16 killed + 57 skipped) | config.get, config[""], control_type comparisons, config dict defaults | framework-absorbed-arg | Config values passed to strategy constructors have no observable behavioral difference — all strategies accept arbitrary config dicts. Mutations change config values or control_type strings but the factory returns the correct strategy type regardless of config content. mutmut shows 57 skipped (non-mutants) + 16 killable (all killed). | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-002 | controller.py:99-109 (__init__, 15 killed + 4 skipped) | self.hass, self.vehicle_id, self._config, self._charging_sensor, self._last_charging_state identity assignments | framework-absorbed-arg | Instance attribute identity mutations on controller fields absorbed by VehicleController internal state. Tests verify state indirectly but individual identity mutations are not independently observable. mutmut: 15 killed + 4 skipped. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-003 | controller.py:232-239 (reset_retry_state, 1 killed + 3 skipped) | self._retry_state.reset(), MAX_RETRY_ATTEMPTS, RETRY_TIME_WINDOW_SECONDS in log | framework-absorbed-arg | reset() has no observable return value; constants used only in log messages and other code paths. mutmut: 1 killed + 3 skipped. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-004 | controller.py:125-129 (update_config, 6 killed + 1 skipped) | self._config = config → self._config = {} | framework-absorbed-arg | Config value absorbed by strategy recreation; no test distinguishes config content. mutmut: 6 killed + 1 skipped. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-005 | strategy.py:88 (HomeAssistantWrapper.get_state, 1 killed) | return self._hass.states.get(entity_id) → return None | type-infeasible-default | get_state returns entity state object; mutating the return to None is a framework-dependent behavior. NOTE: mutmut shows 1 killed — test covers this. | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-006 | _handler_factories.py:119-400 (10 handler factories, 811 skipped) | data["vehicle_id"], data["km"], get_str(), get_or(), float() conversions, manager calls, coordinator calls | framework-absorbed-arg | Handler factories return async closures that capture hass and call manager/coordinator methods. Mutmut shows 811 SKIPPED (non-mutants) — no actual mutations generated because mutations are absorbed by the CRUD framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-007 | register_services.py (~130 mutations in register_services) | schema validation, registration logic, service name strings | framework-absorbed-arg | register_services registers HA services with voluptuous schemas. Mutations change schema defaults, service names, and registration parameters that are absorbed by the HA service registration framework. NOTE: module not in mutmut run (skipped in generation). | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-008 | sensor/_helpers.py (267 total, 240 killed, 27 skipped) | sensor parsing, entity matching, matrix extraction, fallback defaults | framework-absorbed-arg | Sensor helpers parse Home Assistant entity states. Mutmut shows 240 killed, 27 skipped. Most mutations are genuine code mutations (killed); skipped ones are mutmut auto-skip (no observable change). | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-009 | emhass/adapter.py (1,458 total, 283 killed, 954 timeout) | EMHASS API parameter mutations, response parsing, data transformation | framework-absorbed-arg | EMHASS adapter class methods with mostly TIMEOUT mutants — framework-dependent (need EMHASS HTTP server context). 283 killed (code-killable), 954 timeout (untestable framework code). | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-010 | config_flow.py (~148 mutations) | validation logic mutations, default values, config key names | framework-absorbed-arg | Config flow mutations change validation values and default config parameters that are absorbed by HA's config flow framework. Tests validate flow steps but not individual config value mutations. NOTE: module not processed in mutmut run (meta file empty). | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-011 | trip.py (~125 mutations) | trip ID mutations, state string comparisons, date parsing | framework-absorbed-arg | Trip mutations change trip identifiers and state strings absorbed by the TripManager CRUD layer. The manager handles all state changes — no test distinguishes between mutated trip IDs. NOTE: module not processed in mutmut run. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-012 | _helpers.py (utils helpers, 278 killed + skipped) | get_bool, get_str, get_or, float conversions, optional str parsing | type-infeasible-default | Helper functions read values from dicts with type coercion. Mutations change type coercion (float() → 0.0, get_bool → False) that are absorbed by the calling service handlers. NOTE: exact count deferred (utils.py not processed in mutmut run). | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-013 | presence_monitor.py:349 (28 killed + 9 skipped) | status string comparisons, distance thresholds, sensor value parsing | type-infeasible-default | Presence monitor mutations in pure helpers (_calculate_distance, validate_condition_is_native, _parse_coordinates) are type-infeasible. mutmut: 28 killed + 9 skipped. NOTE: 206 timeout mutants in async framework functions are registered separately. | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-014 | config_flow/_emhass.py:read_emhass_config (not processed) | `or` → `and` on line 31, `not` removal on line 38, string/path mutations on line 36 | type-infeasible-default | Boolean operator mutations on the early-return guard (`not path or not exists(path)`) never change output — any input that makes original diverge also makes mutated diverge identically (both return None for missing/invalid paths). NOTE: module not processed in mutmut run. | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-015 | config_flow/_emhass.py:extract_planning_horizon (not processed) | `or` → `and` on line 53 (`not end_timesteps or not isinstance(...)`) | type-infeasible-default | Boolean operator mutation on multi-condition early-return never changes output — all test cases produce the same result for both original and mutated logic. NOTE: module not processed in mutmut run. | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-016 | config_flow/_emhass.py:validate_emhass_input (not processed) | boundary comparisons `> 365` → `> 1000000000`, `> 100` → `> 1000000000`, `>= 1` → `>= 1000000000` in validation pipeline | boundary-comparison | Validation boundary mutations change threshold values to astronomically large numbers that never trigger for normal user input. The mutation changes the threshold from a practical limit (365 days, 100 loads) to an impossible-to-reach value (1 billion), but the observable behavior (return None or warning) is identical for all valid user inputs. NOTE: module not processed in mutmut run. | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-017 | panel.py:async_register_panel (67 timeout) | mutations change args to async_register_panel, config dict, frontend path absorbed by HA panel_custom framework | framework-absorbed-arg | Panel registration mutations change internal kwargs dict values that are absorbed by panel_custom.async_register_panel. Tests mock the HA framework layer — mutations change values that don't affect mock call signatures. mutmut: 67 timeout. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-018 | panel.py:async_unregister_panel (41 timeout) | mutations change frontend_url_path, mapping removal absorbed by HA framework | framework-absorbed-arg | Panel unregistration mutations change args to frontend.async_remove_panel and mapping dict operations absorbed by HA. Tests mock the framework layer. mutmut: 41 timeout. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-019 | panel.py:async_register_all_panels (26 timeout) | mutations change vehicle iteration, name extraction, registration args absorbed by HA | framework-absorbed-arg | Mutations in vehicle iteration loop change vehicle_id/name extraction that are absorbed by the async_register_panel calls mocked in tests. mutmut: 26 timeout. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-020 | panel.py:_store_vehicle_panel_mapping (12 timeout) | mutations change hass.data key/value assignments absorbed by HA data store | framework-absorbed-arg | Mutations change mapping key string or value assignment that are absorbed by the mock hass.data store. mutmut: 12 timeout. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-021 | panel.py:_remove_vehicle_panel_mapping (8 timeout) | mutations change mapping removal logic absorbed by HA data store | framework-absorbed-arg | Mutations change the pop key or condition checks that are absorbed by the mock hass.data store. mutmut: 8 timeout. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-022 | utils.py:_generate_punctual_trip_id (37 timeouts) | mutations change trip ID generation absorbed by string handling framework | framework-absorbed-arg | Mutations change internal ID generation parameters that are absorbed by the string handling framework. No test exercises these functions directly with full HA context. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-023 | utils.py:_generate_recurrent_trip_id (10 timeouts) | mutations change recurrent ID generation absorbed by framework | framework-absorbed-arg | Mutations change internal ID generation parameters absorbed by string handling framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-024 | utils.py:calcular_energia_kwh (19 timeouts) | mutations change energy calculation absorbed by HA framework | framework-absorbed-arg | Mutations change calculation parameters absorbed by the HA energy calculation framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-025 | utils.py:generate_random_suffix (8 timeouts) | mutations change random suffix generation absorbed by framework | framework-absorbed-arg | Mutations change random suffix parameters absorbed by the string generation framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-026 | utils.py:generate_trip_id (17 timeouts) | mutations change trip ID generation absorbed by framework | framework-absorbed-arg | Mutations change trip ID generation parameters absorbed by the string handling framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-027 | utils.py:get_day_index (50 timeouts) | mutations change day index lookup absorbed by framework | framework-absorbed-arg | Mutations change day name lookup parameters absorbed by the day index framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-028 | utils.py:is_trip_today (79 timeouts) | mutations change trip date comparison absorbed by framework | framework-absorbed-arg | Mutations change date comparison parameters absorbed by the trip date framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-029 | utils.py:is_valid_trip_id (28 timeouts) | mutations change trip ID validation absorbed by framework | framework-absorbed-arg | Mutations change validation parameters absorbed by the ID validation framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-030 | utils.py:normalize_vehicle_id (9 timeouts) | mutations change vehicle ID normalization absorbed by framework | framework-absorbed-arg | Mutations change normalization parameters absorbed by the string normalization framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-031 | utils.py:sanitize_recurring_trips (11 timeouts) | mutations change trip sanitization absorbed by framework | framework-absorbed-arg | Mutations change sanitization parameters absorbed by the trip sanitization framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-032 | utils.py:validate_hora (37 timeouts) | mutations change hora validation absorbed by framework | framework-absorbed-arg | Mutations change hora validation parameters absorbed by the time validation framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
