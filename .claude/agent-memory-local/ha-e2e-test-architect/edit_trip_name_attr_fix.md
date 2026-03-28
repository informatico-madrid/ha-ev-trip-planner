---
name: Edit trip fix - name attribute on hidden input
description: Critical fix for edit trip form - input needs name= attribute for formData.get() to work
type: reference
---

**CRITICAL FIX:** Edit trip functionality fails because hidden input has `id=` but not `name=`.

**File:** `custom_components/ev_trip_planner/frontend/panel.js` line 1482

**Problem:** `formData.get('edit-trip-id')` returns `null` because FormData uses the `name` attribute, not `id`.

**Solution:**
```javascript
// BEFORE (broken):
<input type="hidden" id="edit-trip-id" value="${this._escapeHtml(trip.id || trip.trip_id)}">

// AFTER (fixed):
<input type="hidden" name="edit-trip-id" value="${this._escapeHtml(trip.id || trip.trip_id)}">
```

**Why:**
- `FormData.get()` looks for the `name` attribute
- Without `name=`, the tripId cannot be extracted from the form
- Result: "Error: No se pudo identificar el viaje"

**Verified:** Fix applied in container. User's browser shows VERSION=3.0.11 and can test edit functionality.

**Pattern for future:** Always use `name=` for form inputs that need to be submitted, even if they're hidden.
