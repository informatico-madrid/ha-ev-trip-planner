# Home Assistant Core Frontend - Custom Panel Serving

## Overview
Home Assistant serves custom panel JavaScript files from custom integrations through the `panel_custom` component and static path registration.

## How Custom Component JS is Served

### 1. Panel Custom Component
The `panel_custom` component in HA core allows registering custom panels with `js_url` or `module_url`.

**File:** `/usr/src/homeassistant/homeassistant/components/panel_custom/__init__.py`

### 2. How it Works

When a panel is registered via `panel_custom.async_register_panel()`:

```python
await panel_custom.async_register_panel(
    hass,
    frontend_url_path="ev-trip-planner-Coche2",
    webcomponent_name="ev-trip-planner-panel",
    js_url="/ev_trip_planner/panel.js",  # This is served from custom_components
    config={"vehicle_id": "Coche2"},
)
```

### 3. JS URL Resolution

The `js_url` is resolved relative to the integration's directory:
- `js_url="/ev_trip_planner/panel.js"` → `/ev_trip_planner/panel.js`
- This is served from: `custom_components/ev_trip_planner/frontend/panel.js`

### 4. Static Path Registration

Custom components are served via static paths registered in the HTTP component. The path is constructed as:

```python
# For js_url="/ev_trip_planner/panel.js"
static_path = f"/{integration_domain}/{js_url}"
# Result: "/ev_trip_planner/panel.js"
```

### 5. Panel Configuration Flow

1. **manifest.json** defines the frontend:
```json
{
  "frontend": {
    "name": "ev-trip-planner-panel",
    "js_url": "ev_trip_planner/panel.js"
  }
}
```

2. **configuration.yaml** registers the panel:
```yaml
panel_custom:
  - name: "ev-trip-planner-Coche2"
    sidebar_title: "Coche2"
    sidebar_icon: "mdi:car"
    js_url: "/ev_trip_planner/panel.js"
    config:
      vehicle_id: "Coche2"
```

3. **Frontend loads the panel:**
```javascript
// Browser requests: http://localhost:18123/ev_trip_planner/panel.js
// HA serves from: custom_components/ev_trip_planner/frontend/panel.js
```

### 6. Serving Mechanism

The static path is registered in `frontend/__init__.py`:

```python
# In async_setup()
local = hass.config.path("www")
if await hass.async_add_executor_job(os.path.isdir, local):
    static_paths_configs.append(StaticPathConfig("/local", local, not is_dev))

await hass.http.async_register_static_paths(static_paths_configs)
```

Custom component paths are handled through the same mechanism, with paths constructed based on the integration domain.

### 7. Import Maps

HA core uses import maps to handle module imports. For Lit web components:

```javascript
// The panel.js should use relative imports
import { LitElement, html, css } from 'lit';

// HA resolves this through its import map system
// which maps "lit" to the bundled Lit library
```

### 8. Key HA Core Patterns

**Panel URL Format:**
- URL: `/{frontend_url_path}` → `/ev-trip-planner-Coche2`
- JS served at: `/{integration_domain}/{js_url}` → `/ev_trip_planner/panel.js`

**Module URL vs JS URL:**
- `js_url`: Legacy, serves as regular `<script>` tag
- `module_url`: Modern ES modules with `type="module"`

### 9. Examples from HA Core

**KNX Panel:**
```python
module_url=f"{URL_BASE}/{knx_panel.entrypoint_js}",
URL_BASE = "/knx_static"
```

**Hassio Panel:**
```python
js_url="/api/hassio/app/entrypoint.js",
```

**Dynalite Panel:**
```python
module_url=f"{URL_BASE}/entrypoint-{build_id}.js",
URL_BASE = "/dynalite_static"
[StaticPathConfig(URL_BASE, path, cache_headers=(build_id != "dev"))]
```

### 10. Troubleshooting

**Panel not loading:**
1. Check `js_url` matches the file path
2. Verify integration is in `custom_components/`
3. Ensure panel is registered in `configuration.yaml`
4. Check HA logs for panel registration errors

**404 errors:**
- Ensure `js_url` starts with `/`
- Verify file exists at correct location
- Check HA serves from correct `custom_components` path

## Summary

HA serves custom component JS files through:
1. **panel_custom** component registration
2. **Static path** serving from `custom_components/{domain}/`
3. **Import maps** for module resolution
4. **Configuration.yaml** for panel configuration

The key insight is that `js_url` is resolved relative to the integration domain, not as an absolute path.
