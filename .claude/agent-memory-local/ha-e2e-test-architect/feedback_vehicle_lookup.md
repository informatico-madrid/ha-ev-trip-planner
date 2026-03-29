---
name: Case-insensitive vehicle lookup
description: Vehicle ID lookup must be case-insensitive to match frontend vehicle_id with HA config entry vehicle_name
type: feedback
---

## Rule: Vehicle ID comparison must be case-insensitive

**Why:** The frontend sends `vehicle_id: 'coche2'` (lowercase) but the HA config entry stores `vehicle_name: 'Coche2'` (capitalized). Direct string comparison fails, causing `_get_manager` to return "Vehicle not found" errors.

**How to apply:** Always use `.lower()` comparison when matching vehicle IDs from frontend requests to HA config entries:

```python
def _find_entry_by_vehicle(hass: HomeAssistant, vehicle_id: str):
    """Find config entry by vehicle name (case-insensitive)."""
    return next(
        (e for e in hass.config_entries.async_entries(DOMAIN)
         if e.data.get("vehicle_name", "").lower() == vehicle_id.lower()),
        None,
    )
```

**Impact:** This fix resolves the "Vehicle coche2 not found in config entries" error that occurred when creating trips via the UI.
