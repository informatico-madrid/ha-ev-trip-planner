# Research Findings: Home Assistant Core Implementation Methods

**Feature**: 019-panel-vehicle-crud
**Date**: 2026-03-23
**Task**: T001 - Investigar métodos de implementación en Home Assistant Core para panel_custom y EntitySelector

## Executive Summary

This research documents the implementation methods for Home Assistant Core's `panel_custom` component and `EntitySelector` for implementing the EV Trip Planner panel with CRUD operations.

## 1. panel_custom Component API

### Function Signature

```python
async def async_register_panel(
    hass: HomeAssistant,
    frontend_url_path: str,                    # URL path for the panel
    webcomponent_name: str,                    # Web component name (e.g., "ev-trip-planner-panel")
    sidebar_title: str | None = None,          # Title shown in sidebar
    sidebar_icon: str | None = None,           # Icon for sidebar
    js_url: str | None = None,                 # URL to the JS file
    module_url: str | None = None,             # URL to ES module (alternative to js_url)
    embed_iframe: bool = False,                # Whether to use iframe
    trust_external: bool = False,              # Trust external scripts
    config: ConfigType | None = None,          # Configuration passed to panel
    require_admin: bool = False,               # Admin-only access
    config_panel_domain: str | None = None,    # Integration domain for config panel
) -> None:
```

### Key Implementation Details

1. **Registration**: Uses `frontend.async_register_built_in_panel()` internally
2. **Configuration**: The `config` dict is passed to the panel and contains `_panel_custom` metadata
3. **Error Handling**: Raises `ValueError` if neither `js_url` nor `module_url` is provided
4. **Panel Removal**: Use `frontend.async_remove_panel(hass, url_path)` to unregister

### Current Usage in Code

The code in `custom_components/ev_trip_planner/panel.py` already uses this API correctly:

```python
await panel_custom.async_register_panel(
    hass=hass,
    frontend_url_path=frontend_url_path,
    webcomponent_name=PANEL_COMPONENT_NAME,
    js_url="/local/ev_trip_planner/panel.js",
    sidebar_title=vehicle_name,
    sidebar_icon=DEFAULT_SIDEBAR_ICON,
    config={"vehicle_id": vehicle_id},
    require_admin=False,
    embed_iframe=False,
)
```

## 2. EntitySelector with Multiple Domains

### EntitySelectorConfig Schema

```python
class EntitySelectorConfig(EntityFilterSelectorConfig, total=False):
    """Class to represent an entity selector config."""

    exclude_entities: list[str]
    include_entities: list[str]
    multiple: bool
    filter: EntityFilterSelectorConfig | list[EntityFilterSelectorConfig]
```

### Domain Filtering

The `domain` field in `EntityFilterSelectorConfig` can be:
- **Single domain**: `domain="notify"`
- **Multiple domains**: `domain=["notify", "assist_satellite"]`

### Implementation Examples

#### Single Domain (Current Code)

```python
selector.EntitySelector(
    selector.EntitySelectorConfig(
        domain="notify",
        multiple=False,
    )
)
```

#### Multiple Domains (Required for assist_satellite)

```python
selector.EntitySelector(
    selector.EntitySelectorConfig(
        domain=["notify", "assist_satellite"],
        multiple=False,
    )
)
```

### How EntitySelector Works

1. **Entity Registry Query**: HA queries the entity registry for entities matching the specified domain(s)
2. **Filtering**: Additional filters can be applied via:
   - `domain`: Filter by entity domain
   - `device_class`: Filter by device class
   - `integration`: Filter by integration
   - `filter`: Additional entity filter configurations
3. **Validation**: The selector validates that selected entities exist and match the criteria

### Source Code Location

- **panel_custom**: `/home/malka/.local/lib/python3.11/site-packages/homeassistant/components/panel_custom/__init__.py`
- **EntitySelector**: `/home/malka/.local/lib/python3.11/site-packages/homeassistant/helpers/selector.py`

## 3. Implementation Findings for This Feature

### Finding 1: Panel Custom API Compatibility

**Status**: ✅ Already correct

The current implementation correctly uses `panel_custom.async_register_panel()` with all required parameters. No changes needed.

### Finding 2: EntitySelector Domain Limitation

**Status**: ❌ Requires fix

**Current code** (`config_flow.py` line 139-141):
```python
selector.EntitySelectorConfig(
    domain="notify",  # Only shows notify entities
    multiple=False,
)
```

**Required fix**:
```python
selector.EntitySelectorConfig(
    domain=["notify", "assist_satellite"],  # Shows both notify and assist_satellite
    multiple=False,
)
```

**Impact**: This will make `assist_satellite` devices (like Home Assistant Voice Satellites) visible in the notification configuration step.

### Finding 3: Panel Configuration Passing

**Status**: ✅ Already correct

The `config={"vehicle_id": vehicle_id}` is correctly passed to the panel, and the panel reads this from the `config` property.

### Finding 4: Panel Removal on Vehicle Delete

**Status**: ✅ Already implemented

The `async_unregister_panel()` function correctly calls `frontend.async_remove_panel()` when a vehicle is deleted.

## 4. Recommended Changes

### T009: Modify config_flow.py for assist_satellite Support

**File**: `custom_components/ev_trip_planner/config_flow.py`

**Lines to change**: 137-148

**Current**:
```python
STEP_NOTIFICATIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NOTIFICATION_SERVICE): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="notify",
                multiple=False,
            )
        ),
        vol.Optional(CONF_NOTIFICATION_DEVICES): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="notify",
                multiple=True,
            )
        ),
    }
)
```

**Proposed**:
```python
STEP_NOTIFICATIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NOTIFICATION_SERVICE): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["notify", "assist_satellite"],
                multiple=False,
            )
        ),
        vol.Optional(CONF_NOTIFICATION_DEVICES): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["notify", "assist_satellite"],
                multiple=True,
            )
        ),
    }
)
```

## 5. Verification Approach

### For EntitySelector Fix

1. **Browser Verification**: Start test-ha, navigate to config flow, reach notifications step, verify assist_satellite entities appear in dropdown
2. **API Verification**: Query entity registry to confirm assist_satellite entities exist:
   ```bash
   curl -H "Authorization: Bearer <TOKEN>" http://localhost:8123/api/states | grep assist_satellite
   ```

## 6. References

- Home Assistant Core 2024.3.3
- panel_custom documentation: `homeassistant.components.panel_custom`
- EntitySelector documentation: `homeassistant.helpers.selector.EntitySelector`
- Entity registry API: `homeassistant.helpers.entity_registry`

---

**Researcher**: SpecKit Implementation Agent
**Date**: 2026-03-23
**Status**: Complete - Ready for implementation
