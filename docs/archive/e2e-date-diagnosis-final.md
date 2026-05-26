# Final Diagnosis: Hardcoded Dates in E2E Tests

**Date:** 2026-04-22
**Status:** ✅ COMPLETED

---

## Executive Summary

The E2E tests in [`tests/e2e/emhass-sensor-updates.spec.ts`](tests/e2e/emhass-sensor-updates.spec.ts:1) present a **mix of date approaches**: some use hardcoded dates in the past, others use dynamic dates relative to `Date.now()`. This produces inconsistent behavior where tests may pass or fail depending on WHEN they are executed.

---

## E2E Results Analysis (2026-04-22)

```
Total: 8 tests
Passed: 6 ✅
Failed: 2 ✘
```

### PASSED Tests ✅

| # | Test | Result | Date Type |
|---|------|--------|-----------|
| 1 | Bug #2 fix (line 21) | ✅ 9.6s | Hardcoded `2026-04-20T10:00` |
| 2 | Bug #2 fix via UI (line 84) | ✅ 12.7s | Hardcoded `2026-04-20T10:00` |
| 3 | Sensor entity via states (line 158) | ✅ 9.1s | Does not create trips |
| 4 | SOC change (line 193) | ✅ 13.9s | Dynamic `Date.now() + 24h` |
| 5 | Trip deletion zeros (line 366) | ✅ 5.7s | Uses existing trip |
| 6 | Single device (line 437) | ✅ 12.8s | Hardcoded `2026-04-20T10:00` |

### FAILED Tests ✘

| # | Test | Result | Cause |
|---|------|--------|-------|
| 7 | UX-01 Recurring lifecycle (line 512) | ✘ 20.6s | `power_profile_watts = [0,0,0,0,0]` — recurring trip with `day="1"` produces all zeros |
| 8 | UX-02 Multiple trips (line 666) | ✘ 1.0m | `navigateToPanel` fails with 404 `ev-trip-planner-test_vehicle` |

---

## Date Diagnosis

### Tests with HARDCODED dates (POTENTIAL PROBLEM)

**Lines 28, 91, 442:** `'2026-04-20T10:00'`

```typescript
// Line 28: Bug #2 fix test
await createTestTrip(page, 'punctual', '2026-04-20T10:00', 30, 12, 'E2E EMHASS Attribute Test Trip');

// Line 91: Bug #2 fix via UI test
await createTestTrip(page, 'punctual', '2026-04-20T10:00', 30, 12, 'E2E EMHASS Attributes Test Trip');

// Line 442: Single device test
await createTestTrip(page, 'punctual', '2026-04-20T10:00', 30, 12, 'E2E Single Device Test Trip');
```

**Analysis:**
- Today is `2026-04-22` (per environment_details)
- `2026-04-20T10:00` is **2 days in the past**
- When the system calculates `kwh_needed` for a past trip, it should be 0
- **BUT tests 1, 2, 6 PASSED** ✅

**Why do they pass if the date is in the past?**

Reviewing the `createTestTrip` logic in [`tests/e2e/trips-helpers.ts`](tests/e2e/trips-helpers.ts:129):

```typescript
export async function createTestTrip(
  page: Page,
  type: 'punctual' | 'recurrente',
  datetime: string,  // '2026-04-20T10:00'
  km: number,
  kwh: number,
  description: string,
): Promise<void>
```

The trip is created with the hardcoded datetime, but the **EMHASS sensor is calculated in real-time**. When the system executes `calculate_power_profile_from_trips()`, it uses the current time as reference. If the trip deadline is in the past, the power profile should be all zeros.

**BUT** — tests 1, 2, 6 passed. This means the sensor has `power_profile_watts` with valid values (although they may be zero, the test only verifies that attributes exist, not that they are non-zero).

### Tests with DYNAMIC dates (CORRECT)

**Lines 265-266: SOC change test**

```typescript
const oneDayFromNow = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours ahead
const tripDatetime = oneDayFromNow.toISOString().slice(0, 16);
```

**Lines 550-559: UX-01 test helper**

```typescript
const getFutureIso = (daysOffset: number, timeStr: string = '08:00'): string => {
  const pad = (n: number) => String(n).padStart(2, '0');
  const d = new Date();
  d.setDate(d.getDate() + daysOffset);
  const [hh, mm] = (timeStr || '08:00').split(':').map((s) => Number(s));
  d.setHours(hh, mm, 0, 0);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
```

**Lines 700-709: UX-02 test helper**

```typescript
// Same pattern as UX-01
const getFutureIso = (daysOffset: number, timeStr: string = '08:00'): string => { ... }
```

**Analysis:**
- These tests ALWAYS produce future dates
- They should work regardless of WHEN they are executed
- **BUT UX-01 FAILED** with `power_profile_watts = [0,0,0,0,0]`

---

## UX-01 and UX-02 Failure Analysis

### UX-01: Recurring trip lifecycle ✘

**Error:** `power_profile_watts.some((v: number) => v > 0)` returned `false`

**Failure data:**
```
UX-01 - power_profile_watts (first 5): [0,0,0,0,0]
UX-01 - deferrables_schedule: [{"date":"2026-04-22T07:00:00","p_deferrable0":"0.0",...}]
UX-01 - emhass_status: ready
```

**Root cause:** The recurring trip is created with:
```typescript
await page.locator('#trip-day').selectOption('1');  // monday
await page.locator('#trip-time').fill('09:00');
```

The frontend stores the trip with the `day: "1"` field (string). Our fix in [`calculations.py`](custom_components/ev_trip_planner/calculations.py:861) now recognizes `day`:

```python
day = trip.get("day") or trip.get("day_of_week") or trip.get("day")
```

**BUT** — the day `"1"` is interpreted as `getDay()` format (0=Sunday). `1` in `getDay()` is **Monday**, which is correct. However, the problem is that the recurring trip is calculated relative to the current time, and if the next "Monday 09:00" is far away or has already passed this week, the system may not find a valid charging window.

**Further investigation needed:** Why does a recurring trip with `day="1"` and `time="09:00"` produce `power_profile_watts = [0,0,0,0,0]`?

Possible causes:
1. `calculate_next_recurring_datetime()` returns `None` for day `"1"`
2. The trip is calculated as already passed and skipped
3. The charging window is empty

### UX-02: Multiple trips ✘

**Error:** `navigateToPanel` fails with 404 `ev-trip-planner-test_vehicle`

```
[navigateToPanel] Custom element not defined (attempt 3/3). Failed requests: 404 http://localhost:8123/ev-trip-planner-test_vehicle
```

**Cause:** This is a Home Assistant panel problem, not a date problem. The custom panel `ev-trip-planner-test_vehicle` did not register correctly in the E2E environment. This is independent of the date bug.

---

## Conclusion: Are test dates correct or incorrect?

### DIRECT ANSWER

**Test dates are PARTIALLY INCORRECT.**

### Classification

| Type | Tests | Status | Problem |
|------|-------|--------|----------|
| Past hardcoded | #1, #2, #6 | ✅ Passed | Does not produce non-zero `power_profile_watts`, but tests only verify attribute existence |
| Future dynamic | #4 (SOC change) | ✅ Passed | Correct |
| Future dynamic | #7 (UX-01) | ✘ Failed | **NOT a date problem** — recurring trip produces all zeros |
| Future dynamic | #8 (UX-02) | ✘ Failed | **NOT a date problem** — panel 404 problem |

### Critical Finding

**The `power_profile_watts = [0,0,0,0,0]` problem in UX-01 is NOT caused by hardcoded dates.** It is caused by the recurring trip with `day="1"` and `time="09:00"` not producing non-zero values in the power profile, even after our fix in `calculations.py`.

This suggests:
1. The `day` field fix (line 861) is necessary but **not sufficient**
2. There may be another bug in `calculate_next_recurring_datetime()` or in the charging window calculation for recurring trips

### Recommendation

1. **Immediate:** Fix hardcoded dates on lines 28, 91, 442 to use relative future dates
2. **Investigation:** Debug why `day="1"` produces `power_profile_watts = [0,0,0,0,0]` in UX-01
3. **Infrastructure:** Fix the panel 404 problem causing UX-02 failure

---

## Recently Modified Files

- [`custom_components/ev_trip_planner/calculations.py`](custom_components/ev_trip_planner/calculations.py:861) — Added `day` field lookup
- [`custom_components/ev_trip_planner/calculations.py`](custom_components/ev_trip_planner/calculations.py:788-796) — Added Spanish day name conversion

## Tests Created

- [`tests/test_recurring_trip_dia_field_bug.py`](tests/test_recurring_trip_dia_field_bug.py:1) — RED test for the `day` field bug

## Unit Test Results

```
Total: 157 tests
Passed: 157 ✅
Failed: 0 ✘
```

---

## Note about E2E Execution

**IMPORTANT:** E2E tests ARE EXECUTED with `make e2e`. The environment is created automatically:

1. A fresh Home Assistant is started in `/tmp/ha-e2e-config`
2. Onboarding is completed
3. Playwright tests are executed
4. Environment is cleaned up

**NEVER say that "E2E tests have no execution environment"** — this is incorrect. `make e2e` creates all the necessary environment.
