# Clarifications Required

**Feature**: `001-milestone-3-2-complete`  
**Created**: 2026-03-17  
**Source**: Checklist Review  
**Total Items**: 37

---

## 🔴 CRITICAL (Blocking Implementation)

### 1. Charging Sensor Requirement
**File**: `control.md` CHK024  
**Issue**: Are requirements defined for charging sensor failure?  
**Impact**: HIGH - Charging sensor is mandatory for config flow  
**Question**: What should happen if charging sensor is configured but fails?
- [ ] A) Stop charging control immediately
- [ ] B) Continue with fallback (assume unplugged)
- [ ] C) Notify user and wait for sensor recovery
- [ ] D) Other: __________

### 2. Shell Command Execution Approach
**File**: `emhass.md` CHK034  
**Issue**: Is "shell command execution" approach clarified?  
**Impact**: HIGH - Core to EMHASS integration  
**Question**: How should shell command be invoked?
- [ ] A) Direct shell command service call
- [ ] B) REST API call to EMHASS server
- [ ] C) Custom integration service
- [ ] D) Other: __________

### 3. Power Profile Watts Meaning
**File**: `sensors.md` CHK033  
**Issue**: Is "power_profile_watts" meaning clarified (0W vs charging W)?  
**Impact**: HIGH - Critical for EMHASS compatibility  
**Question**: What do power values represent in power_profile_watts array?
- [ ] A) 0W = no charging, 3600W = charging power
- [ ] B) 0W = no charging, positive values = charging power
- [ ] C) All values = charging power (0W means no power)
- [ ] D) Other: __________

### 4. Testing Scope Clarification
**File**: `testing.md` CHK034-035  
**Issue**: Is "no infrastructure tests" scope clarified?  
**Impact**: HIGH - Affects test design  
**Question**: What exactly is excluded from testing scope?
- [ ] A) Only tests that require actual HA infrastructure
- [ ] B) Only tests that don't mock network calls
- [ ] C) Only unit tests (no integration tests)
- [ ] D) Other: __________

### 5. Native Condition: State Approach
**File**: `control.md` CHK035  
**Issue**: Is "native condition: state" approach clarified?  
**Impact**: HIGH - Affects presence monitor implementation  
**Question**: Should presence monitoring use native HA conditions?
- [ ] A) Yes, use `condition: state` in automations
- [ ] B) No, use template conditions only
- [ ] C) Hybrid approach (some of each)
- [ ] D) Other: __________

---

## 🟡 HIGH PRIORITY (Significant Impact)

### 6. Manual Input Fallback for Planning Horizon
**File**: `config.md` CHK031  
**Issue**: Is "manual input fallback" for planning horizon clarified?  
**Impact**: HIGH - Affects config flow UX  
**Question**: What should happen if planning sensor is not available?
- [ ] A) Always allow manual input as fallback
- [ ] B) Require manual input only if sensor fails
- [ ] C) Require sensor, no manual fallback
- [ ] D) Other: __________

### 7. Schedule Array Structure
**File**: `sensors.md` CHK034  
**Issue**: Is schedule array structure clarified?  
**Impact**: HIGH - Critical for EMHASS compatibility  
**Question**: What is the exact structure of `deferrables_schedule` array?
- [ ] A) Array of objects: `[{date: "2026-03-17T14:00:00+01:00", p_deferrable0: "3600.0"}]`
- [ ] B) Array of arrays: `[["2026-03-17T14:00:00+01:00", "3600.0"]]`
- [ ] C) Single object with date and power
- [ ] D) Other: __________

### 8. Notification Content Format
**File**: `notifications.md` CHK031  
**Issue**: Is notification content format clarified?  
**Impact**: HIGH - Affects user experience  
**Question**: What should notification messages contain?
- [ ] A) Only essential info (charging activated/deactivated)
- [ ] B) Detailed info (trip ID, energy, time)
- [ ] C) Dynamic based on context
- [ ] D) Other: __________

### 9. Notification Timing Requirements
**File**: `notifications.md` CHK032  
**Issue**: Are notification timing requirements clarified?  
**Impact**: HIGH - Affects when notifications are sent  
**Question**: When should notifications be sent?
- [ ] A) Immediately when condition occurs
- [ ] B) At specific times (e.g., morning briefing)
- [ ] C) Only when user requests
- [ ] D) Other: __________

### 10. Shell Command Failure Handling
**File**: `emhass.md` CHK024  
**Issue**: Are requirements defined for shell command failure?  
**Impact**: HIGH - Affects error handling  
**Question**: What should happen if shell command fails?
- [ ] A) Log error and continue
- [ ] B) Retry up to 3 times
- [ ] C) Notify user immediately
- [ ] D) Other: __________

### 11. Power Profile Calculation Errors
**File**: `emhass.md` CHK025  
**Issue**: Are requirements defined for power profile calculation errors?  
**Impact**: HIGH - Affects robustness  
**Question**: What should happen if power profile calculation fails?
- [ ] A) Use default profile
- [ ] B) Skip publishing for affected trips
- [ ] C) Notify user and wait for manual input
- [ ] D) Other: __________

### 12. Phase Dependency Order
**File**: `implementation.md` CHK038  
**Issue**: Is phase dependency order clarified?  
**Impact**: HIGH - Affects implementation sequence  
**Question**: What is the correct order for implementation phases?
- [ ] A) As listed in plan (0→8)
- [ ] B) Different order based on dependencies
- [ ] C) Parallel implementation where possible
- [ ] D) Other: __________

### 13. Testing Scope Requirements
**File**: `testing.md` CHK035  
**Issue**: Are testing scope requirements clarified?  
**Impact**: HIGH - Affects test design  
**Question**: What exactly should be tested?
- [ ] A) Only business logic (no infrastructure)
- [ ] B) Only unit tests (no integration tests)
- [ ] C) Both unit and integration tests
- [ ] D) Other: __________

---

## 🟢 MEDIUM PRIORITY (Important but Not Blocking)

### 14. Sensor Not Found Requirement
**File**: `config.md` CHK022  
**Issue**: Are requirements defined for sensor not found?  
**Impact**: MEDIUM - Affects error handling  
**Question**: What should happen if configured sensor is not found?

### 15. Invalid Entity Selectors
**File**: `config.md` CHK025  
**Issue**: Are requirements defined for invalid entity selectors?  
**Impact**: MEDIUM - Affects validation  
**Question**: What validation should be performed on entity selectors?

### 16. Performance Requirements (Config Flow)
**File**: `config.md` CHK026  
**Issue**: Are performance requirements defined for config flow?  
**Impact**: MEDIUM - Affects UX  
**Question**: What performance targets should config flow meet?

### 17. Configuration Persistence
**File**: `config.md` CHK027  
**Issue**: Is configuration persistence requirement defined?  
**Impact**: MEDIUM - Affects data storage  
**Question**: How should configuration be persisted?

### 18. Conflicting Validation Requirements
**File**: `config.md` CHK032  
**Issue**: Are conflicting validation requirements resolved?  
**Impact**: MEDIUM - Affects validation logic  
**Question**: What are the conflicting requirements and how to resolve?

### 19. Charging Sensor Failure
**File**: `control.md` CHK024  
**Issue**: Are requirements defined for charging sensor failure?  
**Impact**: HIGH - See Critical #1

### 20. Presence Sensor Failure
**File**: `control.md` CHK025  
**Issue**: Are requirements defined for presence sensor failure?  
**Impact**: MEDIUM - Affects presence monitoring  
**Question**: What should happen if presence sensor fails?

### 21. Switch Control Failure
**File**: `control.md` CHK027  
**Issue**: Are requirements defined for switch control failure?  
**Impact**: MEDIUM - Affects control reliability  
**Question**: What should happen if switch control fails?

### 22. Script Execution Failure
**File**: `control.md` CHK028  
**Issue**: Are requirements defined for script execution failure?  
**Impact**: MEDIUM - Affects control reliability  
**Question**: What should happen if script execution fails?

### 23. Performance Requirements (Control)
**File**: `control.md` CHK029  
**Issue**: Are performance requirements defined for control operations?  
**Impact**: MEDIUM - Affects responsiveness  
**Question**: What performance targets should control operations meet?

### 24. Logging Requirements (Control)
**File**: `control.md` CHK030  
**Issue**: Are logging requirements defined for control operations?  
**Impact**: MEDIUM - Affects debugging  
**Question**: What logging should be performed for control operations?

### 25. Retry Reset Requirements
**File**: `control.md` CHK036  
**Issue**: Are retry reset requirements clarified?  
**Impact**: MEDIUM - Affects retry logic  
**Question**: When should retry counter be reset?

---

## 🟢 LOW PRIORITY (Nice to Have)

### 26-37. Additional Items
- `emhass.md` CHK025: Power profile calculation errors
- `emhass.md` CHK026: Performance requirements (publish)
- `emhass.md` CHK027: Logging requirements (EMHASS)
- `emhass.md` CHK035: Conflicting index assignment
- `implementation.md` CHK030: Phase delays
- `implementation.md` CHK033: Performance requirements (implementation)
- `implementation.md` CHK034: Documentation requirements
- `implementation.md` CHK039: Timeline range justification
- `notifications.md` CHK023: Notification delivery failure
- `notifications.md` CHK024: Invalid device selector
- `notifications.md` CHK025: Message formatting errors
- `notifications.md` CHK026: Performance requirements (notifications)
- `notifications.md` CHK027: Logging requirements (notifications)
- `sensors.md` CHK023: Zero trips scenario
- `sensors.md` CHK028: Performance requirements (sensors)
- `sensors.md` CHK029: Update frequency requirements
- `ux.md` CHK004: Dashboard auto-detection logic
- `ux.md` CHK014: "Understand exactly" definition
- `ux.md` CHK018: Lovelace integration failures
- `ux.md` CHK020: Performance requirements (dashboard)
- `ux.md` CHK021: Accessibility requirements (config flow)
- `ux.md` CHK022: Lovelace integration assumption
- `testing.md` CHK029: Performance testing requirements
- `testing.md` CHK030: Coverage analysis requirements

---

## 📊 Summary

| Priority | Count | Impact |
|----------|-------|--------|
| 🔴 CRITICAL | 5 | Blocking implementation |
| 🟡 HIGH | 8 | Significant impact |
| 🟢 MEDIUM | 11 | Important but not blocking |
| 🟢 LOW | 13 | Nice to have |
| **TOTAL** | **37** | |

---

## 🎯 Recommended Actions

### Immediate (Before Implementation)
1. **Resolve all CRITICAL items** - 5 items blocking implementation
2. **Resolve HIGH priority items** - 8 items with significant impact
3. **Document MEDIUM priority decisions** - 11 items for future reference

### Optional (Can Be Deferred)
- LOW priority items can be addressed during implementation as needed

---

**Total Clarifications Needed**: 37  
**Critical**: 5 (must resolve before implementation)  
**High**: 8 (should resolve before implementation)  
**Medium**: 11 (should document)  
**Low**: 13 (optional)

**Next**: Answer questions to resolve ambiguities and gaps
