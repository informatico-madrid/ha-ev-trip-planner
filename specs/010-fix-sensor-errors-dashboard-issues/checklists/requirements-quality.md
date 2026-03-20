# Requirements Quality Checklist: Fix Sensor Errors, Dashboard Issues

**Purpose**: Validate specification completeness and quality for bug fixes - testing the requirements themselves, not the implementation
**Created**: 2026-03-20
**Feature**: [spec.md](../spec.md)

**Note**: This checklist follows the `/speckit.checklist` command pattern for validating requirement quality.

---

## Requirement Completeness

- [ ] CHK001 - Are all 4 bug fixes (P001-P004) explicitly defined with requirements? [Completeness, Spec Problem Summary]
- [ ] CHK002 - Are error scenarios (AttributeError, ValueError, Storage unavailable) explicitly specified? [Completeness, Spec Technical Notes]
- [ ] CHK003 - Are the affected files and line numbers documented for each bug? [Completeness, Spec Technical Notes]
- [ ] CHK004 - Is the baseline state (existing code) documented before fixes? [Completeness, Gap]

---

## Requirement Clarity

- [x] CHK005 - Is "hours_needed_today updates correctly" quantified with specific criteria? [Clarity, RESOLVED]
  **Resolution**: Spec now includes "every 30 seconds (standard HA interval)" and returns kW
- [ ] CHK006 - Are the exact device_class values for each sensor type explicitly defined? [Clarity, Spec FR-002]
- [ ] CHK007 - Is the Container fallback behavior specified with concrete steps? [Clarity, Spec FR-004]
- [x] CHK008 - Are "clear instructions" for manual dashboard import defined? [Ambiguity, RESOLVED]
  **Resolution**: Spec now defines: (1) file path, (2) steps to import in Lovelace UI
- [ ] CHK009 - Is the error message "VehicleController has no attribute" explicitly referenced? [Clarity, Spec FR-001]

---

## Requirement Consistency

- [ ] CHK010 - Do FR-001 and Technical Notes P001 refer to the same method call? [Consistency]
- [ ] CHK011 - Are Success Criteria consistent with Functional Requirements? [Consistency]
- [ ] CHK012 - Do all FRs have matching acceptance criteria? [Consistency]

---

## Acceptance Criteria Quality

- [ ] CHK013 - Is "no errors in logs" measurable with specific log patterns? [Measurability, Spec FR-001]
- [ ] CHK014 - Are acceptance criteria testable (can we verify they pass)? [Measurability]
- [ ] CHK015 - Does FR-002 specify exact device_class for each sensor (not just categories)? [Measurability]

---

## Scenario Coverage

- [ ] CHK016 - Are primary scenarios (happy path) defined for all 4 bugs? [Coverage]
- [ ] CHK017 - Are exception scenarios covered (what happens when each fix fails)? [Exception Flow, Gap]
- [x] CHK018 - Is the recovery scenario defined if dashboard import partially fails? [Recovery Flow, RESOLVED]
  **Resolution**: Dashboard must be robust - no partial failures. Use fallback strategies. Tests must cover all failure modes.

---

## Edge Case Coverage

- [ ] CHK019 - Is the edge case of "no trips at all" covered in P003? [Edge Case, Spec FR-003]
- [ ] CHK020 - Is the edge case of "both services unavailable" in Container covered? [Edge Case]
- [ ] CHK021 - Are sensor fallback values specified when data is unavailable? [Edge Case, Gap]

---

## Non-Functional Requirements

- [ ] CHK022 - Are performance requirements (30-second update interval) specified? [NFR, Gap]
- [ ] CHK023 - Are backward compatibility requirements documented for sensor API? [NFR, Gap]
- [ ] CHK024 - Are error handling requirements (logging levels) specified? [NFR, Gap]

---

## Dependencies & Assumptions

- [ ] CHK025 - Is the assumption about HA Container (no Supervisor) validated? [Assumption]
- [ ] CHK026 - Are dependencies on Home Assistant Core versions specified? [Dependency, Gap]
- [ ] CHK027 - Is the dependency between P001 (get_charging_power) and P002 (device_class) documented? [Dependency]

---

## Ambiguities & Conflicts

- [x] CHK028 - Is "potencia de carga" (charging power) defined in kW or A? [Ambiguity, RESOLVED]
  **Resolution**: Charging power must be in kW ( kilowatts )
- [ ] CHK029 - Is the fallback sensor value when no trips defined (0, None, N/A)? [Ambiguity, Spec FR-003]
- [x] CHK030 - Do Scenario 2 (Dashboard unique name) and FR-004 (Container import) conflict? [Conflict, RESOLVED]
  **Resolution**: Dashboard must handle name collisions gracefully - append `-2-`, `-3-`, etc. to name. Must be robust against duplicate imports. Test coverage required for all collision scenarios.

---

## Notes

- Check items off as completed: `[x]`
- Items marked [Gap] indicate missing requirements that need clarification
- Items marked [Ambiguity] need specific definition
- Items marked [Conflict] need resolution before implementation
