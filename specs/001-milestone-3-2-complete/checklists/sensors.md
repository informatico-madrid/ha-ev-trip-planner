# Sensor & Template Requirements Quality

**Purpose**: Validate template sensor, power profile, and schedule requirements  
**Created**: 2026-03-17  
**Domain**: Sensors & Templates

---

## Requirement Completeness

- [ ] CHK001 - Are template sensor entity names explicitly defined? [Completeness, Spec §US-3.2]
- [ ] CHK002 - Are `power_profile_watts` attributes specified? [Completeness, Spec §US-3.2]
- [ ] CHK003 - Are `deferrables_schedule` attributes specified? [Completeness, Spec §US-3.2]
- [ ] CHK004 - Is sensor generation logic fully defined? [Completeness, Spec §US-3.2]
- [ ] CHK005 - Is power profile calculation algorithm specified? [Completeness, Spec §US-3.2]

## Requirement Clarity

- [ ] CHK006 - Is sensor name pattern `sensor.emhass_perfil_diferible_{vehicle_id}` explicit? [Clarity]
- [ ] CHK007 - Is `power_profile_watts` array length defined? [Clarity, Spec §US-3.2]
- [ ] CHK008 - Is `deferrables_schedule` format specified? [Clarity, Spec §US-3.2]
- [ ] CHK009 - Is power value unit (Watts) explicit? [Clarity, Spec §US-3.2]
- [ ] CHK010 - Is date format in schedule defined? [Clarity, Spec §US-3.2]

## Requirement Consistency

- [ ] CHK011 - Are attribute names consistent across all vehicle sensors? [Consistency]
- [ ] CHK012 - Is power value format consistent (0W vs charging W)? [Consistency, Spec §US-3.2]
- [ ] CHK013 - Is timestamp format consistent in schedule? [Consistency, Spec §US-3.2]

## Acceptance Criteria Quality

- [ ] CHK014 - Is "168 values" array requirement quantified? [Acceptance Criteria, Spec §US-3.2]
- [ ] CHK015 - Is "3 decimal places" precision requirement explicit? [Measurability, Spec §US-3.2]
- [ ] CHK016 - Is "ISO 8601 format" timestamp requirement defined? [Measurability, Spec §US-3.2]
- [ ] CHK017 - Is "string format" power value requirement specified? [Measurability, Spec §US-3.2]

## Scenario Coverage

- [ ] CHK018 - Are requirements defined for single trip generation? [Coverage, Spec §US-3.2]
- [ ] CHK019 - Are requirements defined for multiple trips per day? [Coverage, Spec §US-3.2]
- [ ] CHK020 - Are requirements defined for trip deletion? [Coverage, Spec §US-3.2]
- [ ] CHK021 - Are requirements defined for trip editing? [Coverage, Spec §US-3.2]
- [ ] CHK022 - Are requirements defined for planning horizon changes? [Coverage, Spec §US-3.2]

## Edge Case Coverage

- [ ] CHK023 - Are requirements defined for zero trips scenario? [Edge Case, Gap]
- [ ] CHK024 - Are requirements defined for negative distance? [Edge Case, Spec §US-3.2]
- [ ] CHK025 - Are requirements defined for negative consumption? [Edge Case, Spec §US-3.2]
- [ ] CHK026 - Are requirements defined for multiple vehicles? [Edge Case, Spec §US-3.2]
- [ ] CHK027 - Are requirements defined for planning horizon > 7 days? [Edge Case, Spec §US-3.2]

## Non-Functional Requirements

- [ ] CHK028 - Are performance requirements defined for sensor updates? [Gap]
- [ ] CHK029 - Are update frequency requirements defined? [Gap]

## Dependencies & Assumptions

- [ ] CHK030 - Is template sensor platform requirement documented? [Assumption, Spec §US-3.2]
- [ ] CHK031 - Is trip_manager integration requirement defined? [Dependency, Spec §US-3.2]
- [ ] CHK032 - Is config_flow configuration requirement defined? [Dependency, Spec §US-3.2]

## Ambiguities & Conflicts

- [ ] CHK033 - Is "power_profile_watts" meaning clarified (0W vs charging W)? [Ambiguity, Spec §US-3.2]
- [ ] CHK034 - Is schedule array structure clarified? [Ambiguity, Spec §US-3.2]

---

**Total Items**: 34  
**Focus**: Sensor and template requirements quality validation  
**Next**: Review for ambiguities and gaps
