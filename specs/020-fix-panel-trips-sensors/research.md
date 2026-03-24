# Research: EV Trip Planner Panel Debug

## Executive Summary

The EV Trip Planner native panel has multiple issues preventing proper functionality:
1. **CSS 404** - Fixed: Path mismatch between panel.js and __init__.py
2. **Sensors showing 0.0%** - Likely caused by unavailable/unknown states being filtered out
3. **Trips stuck on "Cargando viajes..."** - Likely caused by vehicle ID extraction failure or service call issues
4. **Add trip button not working** - May be caused by panel not fully rendering

### Key Findings
- Vehicle ID extraction from URL is complex with 3 fallback methods
- Trip list service response handling has multiple format variations
- Sensor value formatting filters out unavailable/unknown states aggressively
- Extensive logging added to diagnose all issues

### Recommendations
1. **Add browser console logging** to diagnose vehicle ID extraction
2. **Check Home Assistant sensors** have valid states (not unavailable)
3. **Verify trip_list service** returns expected format
4. **Test add trip button** after panel fixes

---

## Detailed Analysis

### 1. Vehicle ID Extraction

**Location**: `panel.js` lines 67-102

The panel extracts vehicle_id from URL using 3 methods:

**Method 1: Split (most reliable)**
```javascript
const path = window.location.pathname;
if (path.includes('ev-trip-planner-')) {
  const parts = path.split('ev-trip-planner-');
  if (parts.length > 1) {
    const potentialId = parts[1].split('/')[0];
    this._vehicleId = potentialId;
  }
}
```

**Method 2: Regex fallback**
```javascript
const match = path.match(/\/ev-trip-planner-(.+)/);
if (match && match[1]) {
  this._vehicleId = match[1];
}
```

**Method 3: Hash fallback**
```javascript
if (!this._vehicleId && window.location.hash) {
  const hashMatch = window.location.hash.match(/\/ev-trip-planner-(.+)/);
  if (hashMatch && hashMatch[1]) {
    this._vehicleId = hashMatch[1];
  }
}
```

**Issue**: If URL doesn't match expected format (e.g., `/panel/ev-trip-planner-chispitas` vs `/ev-trip-planner-chispitas`), vehicle_id will be null.

**Diagnosis**: Check browser console for:
```
EV Trip Planner Panel: === URL EXTRACTION ===
EV Trip Planner Panel: full URL: [URL]
EV Trip Planner Panel: pathname: [pathname]
```

### 2. Trip List Service Call

**Location**: `panel.js` lines 393-458

The service call returns trip data in this format:
```javascript
{
  recurring_trips: [...],
  punctual_trips: [...]
}
```

**Response Handling**:
```javascript
let tripsData = response;

// Handle array response: [result]
if (Array.isArray(response) && response.length > 0) {
  tripsData = response[0];
}
// Handle object with result property
else if (response && response.result) {
  tripsData = response.result;
}
```

**Issue**: Service response format may vary between HA versions. Logging added to detect actual format.

**Diagnosis**: Check browser console for:
```
EV Trip Planner Panel: Full trip list response: [JSON]
EV Trip Planner Panel: Response type: [type]
EV Trip Planner Panel: tripsData has recurring_trips: [true/false]
```

### 3. Sensor Value Formatting

**Location**: `panel.js` lines 1757-1815

The `_formatSensorValue` function filters out sensors with:
- `unavailable` state
- `unknown` state
- `N/A` state
- `none` state
- Empty string
- `null`

**Issue**: If Home Assistant sensors are in `unavailable` or `unknown` state, they will be filtered out and not display.

**Diagnosis**: Check browser console for:
```
EV Trip Planner Panel: Filtering sensor [entity_id] with value: [value]
```

### 4. Add Trip Button

**Location**: `panel.js` line 505

The button uses inline onclick:
```html
<button class="add-trip-btn" onclick="window._tripPanel._showTripForm()">
  + Agregar Viaje
</button>
```

**Requirement**: `window._tripPanel` must be set to the panel instance.

**Location**: `panel.js` line 2109
```javascript
window._tripPanel = this;
```

**Issue**: If panel doesn't render completely, `window._tripPanel` won't be set and button won't work.

---

## Test Checklist

After deploying changes to Home Assistant:

1. **Open browser console** (F12)
2. **Navigate to panel** for a vehicle
3. **Check console output** for:
   - Vehicle ID extraction logs
   - Trip list service response
   - Sensor filtering logs
4. **Verify panel renders** with sensors and trips section
5. **Test add trip button** - should open modal

---

## Next Steps

### Immediate Actions Required

1. **Deploy updated panel.js** to Home Assistant
2. **Check browser console** for diagnostic logs
3. **Verify Home Assistant sensors** have valid states:
   ```bash
   # Check sensor states via API
   curl -s http://192.168.1.100:8123/api/states/sensor.chispitas_soc_actual
   ```

### If Vehicle ID is Null

**Possible Causes**:
- URL format doesn't match expected pattern
- Panel accessed via wrong path

**Solution**: Check actual URL pattern and adjust extraction logic.

### If Trip List Fails

**Possible Causes**:
- Vehicle ID is null (see above)
- Service doesn't exist or returns wrong format
- No trips configured for vehicle

**Solution**: Check service exists and returns expected format.

### If Sensors Show 0.0%

**Possible Causes**:
- Sensors in `unavailable` or `unknown` state
- Sensor entity IDs don't match expected pattern
- Sensor values are being filtered incorrectly

**Solution**: Check sensor states and entity ID patterns.

---

## Conclusion

The panel code has been enhanced with extensive logging to diagnose issues. The next step is to deploy to Home Assistant and collect console output to identify the root cause.

### Files Modified
- `custom_components/ev_trip_planner/frontend/panel.js` - Added debug logging

### Files to Check
- Home Assistant sensor states (unavailable/unknown)
- Vehicle ID in panel URL
- Trip list service response format
