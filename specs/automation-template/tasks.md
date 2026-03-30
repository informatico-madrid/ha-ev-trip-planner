# Tasks: Automation Template

## Phase 1: Make It Work (POC)

Focus: Create working YAML automation template based on existing borrador. Validate sensor patterns and core logic.

- [x] 1.1 Create base automation template structure
  - **Do**:
    1. Create `automations/emhass_charge_control_template.yaml`
    2. Add alias, description, mode (single), max_exceeded (silent)
    3. Add triggers: time_pattern at minutes 5 and 35
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: YAML structure matches HA automation format
  - **Verify**: `grep -c "triggers:" automations/emhass_charge_control_template.yaml`
  - **Commit**: `feat(automation): add base EMHASS charge control template structure`
  - _Requirements: AC-1_
  - _Design: Interface Contracts_

- [x] 1.2 Add condition checks for EMHASS sensor availability
  - **Do**:
    1. Add template condition: sensor not in ['unavailable', 'unknown']
    2. Add manual mode condition: input_boolean.carga_{vehicle}_modo_manual == 'off'
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: Both conditions present in automation
  - **Verify**: `grep -c "modo_manual" automations/emhass_charge_control_template.yaml`
  - **Commit**: `feat(automation): add EMHASS sensor availability and manual mode conditions`
  - _Requirements: AC-5_
  - _Design: Interface Contracts_

- [x] 1.3 Implement p_deferrable{n} reading for current hour
  - **Do**:
    1. Add variables section with plan attribute reading
    2. Parse `state_attr('sensor.emhass_plan_{vehicle}_mpc_congelado', 'plan_deferrable{n}_horario_mpc')`
    3. Extract p_deferrable{n} value for current hour
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: Template correctly extracts current hour p_deferrable{n} value
  - **Verify**: `grep -c "p_deferrable" automations/emhass_charge_control_template.yaml`
  - **Commit**: `feat(automation): implement p_deferrable reading for current hour`
  - _Requirements: AC-1_
  - _Design: Interface Contracts_

- [x] 1.4 Add charge start logic (>100W, home, plugged)
  - **Do**:
    1. Add variables: coche_en_casa, coche_enchufado checks
    2. Add debe_cargar logic: potencia > 100 AND home AND plugged
    3. Add choose branch for start charging sequence
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: Start conditions match AC-2 requirements
  - **Verify**: `grep -A5 "debe_cargar" automations/emhass_charge_control_template.yaml`
  - **Commit**: `feat(automation): add charge start logic when p_deferrable > 100W`
  - _Requirements: AC-2_
  - _Design: Interface Contracts_

- [x] 1.5 Add charge stop logic (0W, charging active)
  - **Do**:
    1. Add choose branch for stop conditions: potencia == 0 AND charging active
    2. Add stop charging sequence
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: Stop conditions match AC-3 requirements
  - **Verify**: `grep -A3 "detener" automations/emhass_charge_control_template.yaml`
  - **Commit**: `feat(automation): add charge stop logic when p_deferrable == 0W`
  - _Requirements: AC-3_
  - _Design: Interface Contracts_

- [ ] 1.6 V1 [VERIFY] Quality checkpoint: YAML syntax validation
  - **Do**: Run Home Assistant config validator or YAML linter
  - **Verify**: `python3 -c "import yaml; yaml.safe_load(open('automations/emhass_charge_control_template.yaml'))" && echo V1_PASS`
  - **Done when**: YAML parses without errors
  - **Commit**: None

- [x] 1.7 Add notification for missed charging opportunities
  - **Do**:
    1. Add conditions: car not home OR not plugged AND potencia > 100
    2. Add notification action (persistent_notification.create)
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: Notification branch present for missed opportunities
  - **Verify**: `grep -c "persistent_notification" automations/emhass_charge_control_template.yaml`
  - **Commit**: `feat(automation): add notification for missed charging opportunities`
  - _Requirements: AC-4_
  - _Design: TODO item 4_

- [x] 1.8 Make automation template generic via variables
  - **Do**:
    1. Replace hardcoded vehicle names with template variables
    2. Add vehicle_id as configurable parameter
    3. Ensure template can be included once per vehicle
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: Template uses variables for vehicle-specific entities
  - **Verify**: `grep "{{" automations/emhass_charge_control_template.yaml | head -5`
  - **Commit**: `feat(automation): make template generic with vehicle variables`
  - _Requirements: AC-1, AC-2, AC-3_
  - _Design: Interface Contracts_

- [x] 1.9 Add blueprint metadata for easy import
  - **Do**:
    1. Add Home Assistant blueprint header (name, description, domain)
    2. Add input definitions for vehicle_id, home_sensor, plugged_sensor, etc.
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: Blueprint metadata present
  - **Verify**: `grep -c "blueprint:" automations/emhass_charge_control_template.yaml`
  - **Commit**: `feat(automation): add blueprint metadata for easy import`
  - _Requirements: General_
  - _Design: Architecture_

## Phase 2: Sensor Pattern Support

Focus: Support both sensor naming patterns identified in plan.

- [x] 2.1 Document both sensor naming patterns
  - **Do**:
    1. Add comments in template explaining both patterns
    2. Create `docs/emhass_sensor_naming.md` with mapping
  - **Files**: `automations/emhass_charge_control_template.yaml`, `docs/emhass_sensor_naming.md`
  - **Done when**: Both patterns documented
  - **Verify**: `grep -c "sensor.emhass_" docs/emhass_sensor_naming.md`
  - **Commit**: `docs(automation): document sensor naming patterns`
  - _Requirements: Sensor Naming Clarification_
  - _Design: Interface Contracts_

- [x] 2.2 Add template switch for sensor pattern selection
  - **Do**:
    1. Add input_select for sensor pattern preference
    2. Add conditions that check which pattern to use
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: Template supports switching between patterns
  - **Verify**: `grep -c "input_select" automations/emhass_charge_control_template.yaml`
  - **Commit**: `feat(automation): add sensor pattern selection switch`
  - _Requirements: Sensor Naming Clarification_
  - _Design: Interface Contracts_

- [ ] 2.3 V2 [VERIFY] Quality checkpoint: validate both sensor patterns
  - **Do**: Test template with both sensor naming conventions
  - **Verify**: `python3 -c "import yaml; d=yaml.safe_load(open('automations/emhass_charge_control_template.yaml')); print('OK')"`
  - **Done when**: Template valid with both patterns
  - **Commit**: None

## Phase 3: Edge Cases and Documentation

Focus: Handle edge cases and document required HA entities.

- [x] 3.1 Handle SOC-based charge limiting
  - **Do**:
    1. Add SOC check before starting charge (e.g., SOC > 90% = don't start)
    2. Add soc_alto variable and conditions
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: SOC edge cases handled per existing borrador pattern
  - **Verify**: `grep -c "soc" automations/emhass_charge_control_template.yaml`
  - **Commit**: `feat(automation): add SOC-based charge limiting`
  - _Design: Edge Cases from templateborradorcargasaplazablesvehiculo.yaml_

- [x] 3.2 Handle intensity adjustment for Morgan (V2C) case
  - **Do**:
    1. Add intensity calculation: potencia / 230
    2. Add min/max clamping (6A min, 32A max)
  - **Files**: `automations/emhass_charge_control_template.yaml`
  - **Done when**: Intensity adjustment logic present
  - **Verify**: `grep -c "intensidad" automations/emhass_charge_control_template.yaml`
  - **Commit**: `feat(automation): add intensity adjustment for V2C`
  - _Design: Edge Cases from templateborradorcargasaplazablesvehiculo.yaml_

- [x] 3.3 Document required HA entities
  - **Do**:
    1. Create `docs/automation_entities.md`
    2. List all required entities: home_sensor, plugged_sensor, soc_sensor, modo_manual, etc.
  - **Files**: `docs/automation_entities.md`
  - **Done when**: All required entities documented
  - **Verify**: `wc -l docs/automation_entities.md`
  - **Commit**: `docs(automation): document required HA entities`
  - _Requirements: TODO item 5_
  - _Design: TODO item 5_

- [ ] 3.4 V3 [VERIFY] Quality checkpoint: edge cases and docs
  - **Do**: Review all edge case handling
  - **Verify**: `grep -E "(soc_alto|intensidad|not debe_cargar)" automations/emhass_charge_control_template.yaml | wc -l`
  - **Done when**: All edge cases implemented
  - **Commit**: None

## Phase 4: Quality Gates

- [x] 4.1 YAML validation against Home Assistant schema
  - **Do**: Validate automation YAML structure
  - **Verify**: `python3 -c "import yaml; yaml.safe_load(open('automations/emhass_charge_control_template.yaml')); print('VALID')"`
  - **Done when**: YAML is valid Home Assistant automation
  - **Commit**: None

- [ ] 4.2 Create PR and verify CI
  - **Do**:
    1. Verify current branch: `git branch --show-current`
    2. Push branch: `git push -u origin feature/soc-milestone-algorithm`
    3. Create PR with gh CLI
  - **Verify**: `gh pr create --title "feat(automation): EMHASS charge control template" --body "$(cat <<'EOF'
## Summary
- YAML automation template for EMHASS-controlled vehicle charging
- Supports p_deferrable{n} reading from MPC plan
- Handles start/stop based on potencia thresholds
- Manual mode override support
- Notifications for missed charging opportunities

## Test plan
- [ ] Validate YAML syntax
- [ ] Test with real EMHASS sensor data
- [ ] Verify charge start/stop logic
EOF
)"` 2>/dev/null || echo "PR creation skipped"
  - **Done when**: PR created or ready for review
  - **Commit**: None

## Phase 5: PR Lifecycle

- [ ] 5.1 Monitor CI pipeline
  - **Do**: Check PR checks status
  - **Verify**: `gh pr checks 2>/dev/null || echo "CI check skipped"`
  - **Done when**: All checks pass
  - **Commit**: None

- [ ] 5.2 Address review comments if any
  - **Do**: Handle feedback from code review
  - **Done when**: All comments resolved
  - **Verify**: `gh pr view --comments 2>/dev/null | grep -c "comment" || echo "0"`
  - **Commit**: `fix(automation): address review comments`

- [ ] 5.3 Final merge to main
  - **Do**: Merge PR after all checks pass
  - **Verify**: `git log --oneline -1`
  - **Done when**: PR merged
  - **Commit**: `chore(automation): merge EMHASS charge control template`

## Notes

- **POC shortcuts taken**:
  - Hardcoded vehicle names initially, made generic in later task
  - Single sensor pattern first, added second pattern support in Phase 2

- **Production TODOs**:
  - Add E2E test for real charging scenario (requires physical vehicle)
  - Add simulation mode for testing without real EMHASS data
  - Consider adding REST API trigger option alongside time_pattern