---
spec: bug-hypothesis-entry-data-options
phase: research
created: 2026-04-23
---

# Research: Config Entry `data` vs `options` Storage for EMHASS Adapter Creation

## Executive Summary

The bug hypothesis is **INCORRECT for the current codebase**. The values `planning_horizon_days` and `max_deferrable_loads` are stored exclusively in `entry.data` via the initial config flow and are **never** written to `entry.options` by the options flow. The check at `__init__.py:141` reading from `entry.data` is correct. However, there is an inconsistency in how different config values are read across the codebase (some check only `data`, some check both `data` and `options`).

## Analysis

### 1. Config Flow: Where values go

**File**: `custom_components/ev_trip_planner/config_flow.py`

All 5 config flow steps collect data into a single `vehicle_data` dict (via `self._get_vehicle_data()`), and the final entry is created at line 812-814:

```python
result = self.async_create_entry(
    title=vehicle_name,
    data=vehicle_data,  # ALL values go here
)
```

The `vehicle_data` dict contains (from all 5 steps):

| Step | Keys stored in `vehicle_data` → `entry.data` |
|------|-----|
| Step 1 (user) | `vehicle_name` |
| Step 2 (sensors) | `battery_capacity_kwh`, `charging_power_kw`, `kwh_per_km`, `safety_margin_percent`, `soc_sensor` |
| Step 3 (emhass) | `planning_horizon_days`, `max_deferrable_loads`, `index_cooldown_hours`, `planning_sensor_entity` |
| Step 4 (presence) | `charging_sensor`, `home_sensor`, `plugged_sensor` |
| Step 5 (notifications) | `notification_service`, `notification_devices` |

**None of these values are passed as `options=`** — they all go into `entry.data`.

### 2. Options Flow: What it stores

**File**: `config_flow.py`, lines 877-945, `EVTripPlannerOptionsFlowHandler`

The options flow only handles 4 values:

```python
# Lines 902-909
if CONF_BATTERY_CAPACITY in user_input:
    update_data[CONF_BATTERY_CAPACITY] = user_input[CONF_BATTERY_CAPACITY]
if CONF_CHARGING_POWER in user_input:
    update_data[CONF_CHARGING_POWER] = user_input[CONF_CHARGING_POWER]
if CONF_CONSUMPTION in user_input:
    update_data[CONF_CONSUMPTION] = user_input[CONF_CONSUMPTION]
if CONF_SAFETY_MARGIN in user_input:
    update_data[CONF_SAFETY_MARGIN] = user_input[CONF_SAFETY_MARGIN]

return self.async_create_entry(title="", data=update_data)
```

This writes to `entry.options`. **It does NOT touch `entry.data`.**

**CRITICAL**: `planning_horizon_days`, `max_deferrable_loads`, `index_cooldown_hours`, and `planning_sensor_entity` are **NOT** in the options form at all. They cannot be edited through the HA UI options dialog.

### 3. How HA stores data

When `ConfigFlow.async_create_entry(data=vehicle_data)` is called:
- HA creates a `ConfigEntry` with `data=vehicle_data`
- `options` defaults to `{}`
- Both are persisted to the HA config entry database

When `OptionsFlow.async_create_entry(data=update_data)` is called:
- HA calls `async_update_entry(entry, options=update_data)`
- Only `entry.options` is modified
- `entry.data` is **NOT** modified

### 4. The check at `__init__.py:141` is correct

```python
# Line 141
if entry.data.get("planning_horizon_days") or entry.data.get("max_deferrable_loads"):
    emhass_adapter = EMHASSAdapter(hass, entry)
```

This reads from `entry.data` because:
- These values are only ever placed in `entry.data` (never in options)
- `entry.data` persists across HA restarts
- The options flow never modifies or removes these keys

### 5. Inconsistency: How different values are read

| Value | Where it lives | Read pattern | File:Line |
|-------|---------------|--------------|-----------|
| `vehicle_name` | `entry.data` only | `entry.data.get()` | `__init__.py:122,194` |
| `soc_sensor` | `entry.data` only | `entry.data.get()` | `__init__.py:136` |
| `charging_power_kw` | `entry.data` AND `entry.options` | `entry.options.get()` → `entry.data.get()` fallback | `emhass_adapter.py:2145-2147` |
| `planning_horizon_days` | `entry.data` only | `entry.data.get()` | `__init__.py:141` |
| `max_deferrable_loads` | `entry.data` only | `entry.data.get()` | `__init__.py:141, emhass_adapter.py:77` |

The only value that can exist in **both** `data` and `options` is `charging_power_kw` (because it's in the options form). The `update_charging_power` method correctly handles this by checking `options` first, then `data` as fallback.

### 6. EMHASS Adapter reads from `entry.data` consistently

**File**: `emhass_adapter.py`, lines 66-77

```python
elif hasattr(entry, "data"):
    self.entry_id = entry.entry_id
    self._entry_dict = entry.data
    entry_data = entry.data

self.max_deferrable_loads = entry_data.get(CONF_MAX_DEFERRABLE_LOADS, 50)
```

And in `update_charging_power` (lines 2143-2147):
```python
new_power = entry.options.get("charging_power_kw")
if new_power is None:
    new_power = entry.data.get("charging_power_kw")
```

### 7. Test verification

Tests in `test_integration_uninstall.py` (lines 100-105) set up mock entries:
```python
entry.data = {
    "vehicle_name": "EMHASS Test Vehicle",
    "planning_horizon_days": 7,
    "max_deferrable_loads": 50,
    "charging_power_kw": 7.4,
}
```

All EMHASS-related values are in `entry.data`. No test sets them in `entry.options`.

## Related Specs Discovery

Scanned existing specs for relationships. No specs directly related to this config flow data storage pattern were found in the current specs directories.

## Quality Commands

| Type | Command | Source |
|------|---------|--------|
| Test (emhass_adapter) | `pytest tests/test_emhass_adapter.py` | package.json / test files |
| Test (config_flow) | `pytest tests/test_config_flow*.py` | test files |
| Test (uninstall) | `pytest tests/test_integration_uninstall.py` | test files |

## Verdict

### The hypothesis is INCORRECT for `planning_horizon_days` and `max_deferrable_loads`

- These values go to `entry.data` via the initial config flow
- They are NEVER part of the options flow
- `entry.data` persists after restarts
- The check at `__init__.py:141` is correct

### But there IS an inconsistency worth noting

`charging_power_kw` is the only value that can exist in both places. The code in `update_charging_power` correctly handles this (options first, data fallback). But the adapter creation check doesn't apply to this value — it only checks `planning_horizon_days` and `max_deferrable_loads`, which are correctly always in `entry.data`.

### Risk: Future-proofing

If a future enhancement adds `planning_horizon_days` or `max_deferrable_loads` to the options form, the adapter creation check at line 141 would break. The safer pattern (used in `update_charging_power`) would be:

```python
ph = entry.options.get("planning_horizon_days")
if ph is None:
    ph = entry.data.get("planning_horizon_days")
mdl = entry.options.get("max_deferrable_loads")
if mdl is None:
    mdl = entry.data.get("max_deferrable_loads")
if ph or mdl:
    emhass_adapter = EMHASSAdapter(hass, entry)
```

But this is a **future** concern, not a current bug.

## Sources

| Source | Key Point |
|--------|-----------|
| `config_flow.py:812-814` | `async_create_entry(data=vehicle_data)` — all values go to entry.data |
| `config_flow.py:901-911` | Options flow only stores 4 keys to options |
| `config_flow.py:877-945` | `EVTripPlannerOptionsFlowHandler` — no EMHASS fields |
| `emhass_adapter.py:2145-2147` | Correct dual-check pattern for values that can be in both |
| `emhass_adapter.py:77` | `max_deferrable_loads` read from `entry.data` (correct) |
| `__init__.py:141` | Conditional EMHASS adapter creation (correct for current data placement) |
| `const.py:37-39` | CONF_MAX_DEFERRABLE_LOADS = "max_deferrable_loads", CONF_PLANNING_HORIZON = "planning_horizon_days" |
| `test_integration_uninstall.py:100-105` | Tests confirm EMHASS values in entry.data |
| `test_emhass_adapter.py:23-31` | MockConfigEntry puts all values in entry.data |
