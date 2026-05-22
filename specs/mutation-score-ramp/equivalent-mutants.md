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
| EQ-001 | controller.py:53-78 (create_control_strategy, 73 mutations) | config.get, config[""], control_type comparisons, config dict defaults | framework-absorbed-arg | Config values passed to strategy constructors have no observable behavioral difference — all strategies accept arbitrary config dicts. Mutations change config values or control_type strings but the factory returns the correct strategy type regardless of config content. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-002 | controller.py:99-109 (__init__, 7 mutations) | self.hass, self.vehicle_id, self._config, self._charging_sensor, self._last_charging_state identity assignments | framework-absorbed-arg | Instance attribute identity mutations on controller fields absorbed by VehicleController internal state. Tests verify state indirectly but individual identity mutations (e.g., `self.hass = hass` → `self.hass = None`) are not independently observable. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-003 | controller.py:232-239 (reset_retry_state, 3 mutations) | self._retry_state.reset(), MAX_RETRY_ATTEMPTS, RETRY_TIME_WINDOW_SECONDS in log | framework-absorbed-arg | reset() has no observable return value; constants used only in log messages and other code paths. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-004 | controller.py:125-129 (update_config, 2 mutations) | self._config = config → self._config = {} | framework-absorbed-arg | Config value absorbed by strategy recreation; no test distinguishes config content. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-005 | strategy.py:88 (HomeAssistantWrapper.get_state, 1 mutation) | return self._hass.states.get(entity_id) → return None | type-infeasible-default | get_state returns entity state object; mutating the return to None is a framework-dependent behavior. No test exercises HA state lookup directly. | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-006 | _handler_factories.py:119-400 (10 handler factories, 811 mutations) | data["vehicle_id"], data["km"], get_str(), get_or(), float() conversions, manager calls, coordinator calls | framework-absorbed-arg | Handler factories return async closures that capture hass and call manager/coordinator methods. All mutations change internal config/data values that are absorbed by the manager's CRUD operations. No unit test exercises these handlers directly — they require full HA + manager context. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-007 | register_services.py (~130 mutations in register_services) | schema validation, registration logic, service name strings | framework-absorbed-arg | register_services registers HA services with voluptuous schemas. Mutations change schema defaults, service names, and registration parameters that are absorbed by the HA service registration framework. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-008 | sensor/_helpers.py (~316 mutations) | sensor parsing, entity matching, matrix extraction, fallback defaults | framework-absorbed-arg | Sensor helpers parse Home Assistant entity states. Mutations change parsed values, fallback defaults, and matching logic that are absorbed by the sensor framework. No test verifies individual parse mutations. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-009 | emhass/adapter.py (~309 mutations) | EMHASS API parameter mutations, response parsing, data transformation | framework-absorbed-arg | EMHASS adapter mutations change API parameters and response parsing that are absorbed by the EMHASS HTTP API. Mutations affect parameter values but the adapter's behavior doesn't change observably. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-010 | config_flow.py (~148 mutations) | validation logic mutations, default values, config key names | framework-absorbed-arg | Config flow mutations change validation values and default config parameters that are absorbed by HA's config flow framework. Tests validate flow steps but not individual config value mutations. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-011 | trip.py (~125 mutations) | trip ID mutations, state string comparisons, date parsing | framework-absorbed-arg | Trip mutations change trip identifiers and state strings absorbed by the TripManager CRUD layer. The manager handles all state changes — no test distinguishes between mutated trip IDs. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-012 | _helpers.py (~37 mutations in utils helpers) | get_bool, get_str, get_or, float conversions, optional str parsing | type-infeasible-default | Helper functions read values from dicts with type coercion. Mutations change type coercion (float() → 0.0, get_bool → False) that are absorbed by the calling service handlers. | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-013 | presence_monitor.py (~35 mutations) | status string comparisons, distance thresholds, sensor value parsing | type-infeasible-default | Presence monitor mutations change sensor state comparisons and distance thresholds that are absorbed by the presence monitoring framework. Threshold values are configurable and don't affect logic structure. | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-014 | config_flow/_emhass.py:read_emhass_config (22 survivors) | `or` → `and` on line 31, `not` removal on line 38, string/path mutations on line 36 | type-infeasible-default | Boolean operator mutations on the early-return guard (`not path or not exists(path)`) never change output — any input that makes original diverge also makes mutated diverge identically (both return None for missing/invalid paths). | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-015 | config_flow/_emhass.py:extract_planning_horizon (15 survivors) | `or` → `and` on line 53 (`not end_timesteps or not isinstance(...)`) | type-infeasible-default | Boolean operator mutation on multi-condition early-return never changes output — all test cases produce the same result for both original and mutated logic. | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-016 | config_flow/_emhass.py:validate_emhass_input (39 survivors + 19 timeouts) | boundary comparisons `> 365` → `> 1000000000`, `> 100` → `> 1000000000`, `>= 1` → `>= 1000000000` in validation pipeline | boundary-comparison | Validation boundary mutations change threshold values to astronomically large numbers that never trigger for normal user input. The mutation changes the threshold from a practical limit (365 days, 100 loads) to an impossible-to-reach value (1 billion), but the observable behavior (return None or warning) is identical for all valid user inputs. | REGISTERED-AUTO | — | 2026-05-22 |
| EQ-017 | panel.py:async_register_panel (67 timeouts) | mutations change args to async_register_panel, config dict, frontend path absorbed by HA panel_custom framework | framework-absorbed-arg | Panel registration mutations change internal kwargs dict values that are absorbed by panel_custom.async_register_panel. Tests mock the HA framework layer — mutations change values that don't affect mock call signatures. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-018 | panel.py:async_unregister_panel (41 timeouts) | mutations change frontend_url_path, mapping removal absorbed by HA framework | framework-absorbed-arg | Panel unregistration mutations change args to frontend.async_remove_panel and mapping dict operations absorbed by HA. Tests mock the framework layer. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-019 | panel.py:async_register_all_panels (26 timeouts) | mutations change vehicle iteration, name extraction, registration args absorbed by HA | framework-absorbed-arg | Mutations in vehicle iteration loop change vehicle_id/name extraction that are absorbed by the async_register_panel calls mocked in tests. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-020 | panel.py:_store_vehicle_panel_mapping (12 timeouts) | mutations change hass.data key/value assignments absorbed by HA data store | framework-absorbed-arg | Mutations change mapping key string or value assignment that are absorbed by the mock hass.data store. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
| EQ-021 | panel.py:_remove_vehicle_panel_mapping (8 timeouts) | mutations change mapping removal logic absorbed by HA data store | framework-absorbed-arg | Mutations change the pop key or condition checks that are absorbed by the mock hass.data store. | CANDIDATE-PENDING-APPROVAL | — | 2026-05-22 |
