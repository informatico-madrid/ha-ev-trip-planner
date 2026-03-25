# Tasks: E2E Tests CRUD para Viajes EV Trip Planner

## Phase 1: Make It Work (POC)

Focus: Configurar entorno y crear tests CRUD básicos con funcionalidad real.

- [x] 1.1 Configurar trusted_networks en configuration.yaml
  - **Do**:
    1. Editar `/test-ha/config/configuration.yaml`
    2. Agregar `trusted_networks` con `allow_bypass_login_for_ips`
    3. Patrón: `127.0.0.1` y `192.168.1.0/24`
  - **Files**: `/test-ha/config/configuration.yaml`
  - **Done when**: Archivo tiene configuración de trusted_networks añadida
  - **Verify**: `grep -A 3 "trusted_networks" /test-ha/config/configuration.yaml | grep -q "allow_bypass_login_for_ips" && echo "PASS"`
  - **Commit**: `config(test-ha): add trusted_networks with allow_bypass_login_for_ips`
  - _Requirements: Dependencies section_
  - _Design: Error Handling_

- [x] 1.2 [P] Eliminar 5 tests de Nivel 1 (completamente inútiles)
  - **Do**:
    1. Eliminar `tests/e2e/dashboard-crud.spec.ts`
    2. Eliminar `tests/e2e/test-performance.spec.ts`
    3. Eliminar `tests/e2e/test-cross-browser.spec.ts`
    4. Eliminar `tests/e2e/test-pr-creation.spec.ts`
    5. Eliminar `tests/e2e/test-panel-loading.spec.ts`
  - **Files**: N/A (deletion)
  - **Done when**: Los 5 archivos eliminados del sistema
  - **Verify**: `test -f tests/e2e/dashboard-crud.spec.ts || echo "PASS"`
  - **Commit**: `chore(e2e): eliminate Nivel 1 tests (5 files)`
  - _Requirements: research.md section "Tests que Deben Eliminarse"_

- [x] 1.3 [P] Eliminar test-integration.spec.ts
  - **Do**:
    1. Eliminar `tests/e2e/test-integration.spec.ts`
    2. Justificación: tests duplicados según research.md
  - **Files**: N/A (deletion)
  - **Done when**: Archivo eliminado
  - **Verify**: `test -f tests/e2e/test-integration.spec.ts || echo "PASS"`
  - **Commit**: `chore(e2e): remove duplicate integration test`
  - _Requirements: research.md section "Tests que Deben Eliminarse"_

- [ ] 1.4 [P] Configurar ambiente de tests
  - **Do**:
    1. Verificar `.env` tiene HA_URL y VEHICLE_ID definidos
    2. Confirmar variables: `HA_URL=http://192.168.1.100:18123`
    3. Confirmar variables: `VEHICLE_ID=Coche2`
  - **Files**: `.env`
  - **Done when**: Variables de entorno verificadas
  - **Verify**: `grep -q "HA_URL" .env && grep -q "VEHICLE_ID" .env && echo "PASS"`
  - **Commit**: `chore(test): verify environment configuration`
  - _Requirements: Design "Security Considerations"_

- [ ] 1.5 [P] Crear trip-crud.spec.ts - Test Create Recurrente
  - **Do**:
    1. Crear `tests/e2e/trip-crud.spec.ts`
    2. Escribir test describe para CRUD de viajes
    3. Implementar test: "should create a recurring trip"
    4. Usar selector: `ev-trip-planner-panel >> .add-trip-btn`
    5. Formulario: `#trip-type` -> "recurrente", `#trip-day` -> "1", `#trip-time` -> "08:00"
    6. Datos: `#trip-km` -> "25.5", `#trip-kwh` -> "5.2", `#trip-description` -> "Test trip"
    7. Submit: click button[type="submit"]
    8. Validar: formOverlay.toBeHidden(), tripCards.toHaveCount({ min: 1 })
  - **Files**: `tests/e2e/trip-crud.spec.ts`
  - **Done when**: Test file creado con test create recurrente
  - **Verify**: `grep -q "should create a recurring trip" tests/e2e/trip-crud.spec.ts && echo "PASS"`
  - **Commit**: `test(e2e): create trip-crud.spec.ts for recurring trip`
  - _Requirements: FR-3, AC-1.1 to AC-1.15_
  - _Design: Test Orchestrator (trip-crud.spec.ts)_

- [ ] 1.6 [P] Crear trip-crud.spec.ts - Test Edit Trip
  - **Do**:
    1. Agregar test: "should edit an existing trip"
    2. Check si tripCards.count() > 0, skip si no
    3. Click `.trip-action-btn.edit-btn` primera card
    4. Validar formOverlay.visible()
    5. Editar: `#edit-trip-time` -> "14:30", `#edit-trip-km` -> "40.0"
    6. Submit: click button[type="submit"]
    7. Validar: formOverlay.toBeHidden(), tripCard.text().toContain("40.0 km"), toContain("14:30")
  - **Files**: `tests/e2e/trip-crud.spec.ts`
  - **Done when**: Test edit trip agregado
  - **Verify**: `grep -q "should edit an existing trip" tests/e2e/trip-crud.spec.ts && echo "PASS"`
  - **Commit**: `test(e2e): add edit trip test to trip-crud.spec.ts`
  - _Requirements: FR-4, AC-3.1 to AC-3.12_
  - _Design: Test Orchestrator (trip-crud.spec.ts)_

- [ ] 1.7 [P] Crear trip-crud.spec.ts - Test Delete Trip
  - **Do**:
    1. Agregar test: "should delete an existing trip"
    2. Check tripCards.count() > 0, skip si no
    3. Click `.trip-action-btn.delete-btn` primera card
    4. Configurar dialog handler: `page.on('dialog', dialog => dialog.accept())`
    5. Validar: tripCards.toHaveCount({ min: 0 })
    6. Si era último: validar `.no-trips.toBeVisible()`
  - **Files**: `tests/e2e/trip-crud.spec.ts`
  - **Done when**: Test delete trip agregado
  - **Verify**: `grep -q "should delete an existing trip" tests/e2e/trip-crud.spec.ts && echo "PASS"`
  - **Commit**: `test(e2e): add delete trip test to trip-crud.spec.ts`
  - _Requirements: FR-5, AC-4.1 to AC-4.10_
  - _Design: Test Orchestrator (trip-crud.spec.ts)_

- [ ] 1.8 [VERIFY] Quality checkpoint: lint && typecheck
  - **Do**:
    1. Ejecutar lint: `pnpm lint`
    2. Ejecutar typecheck: `pnpm check-types`
  - **Files**: `tests/e2e/trip-crud.spec.ts`
  - **Done when**: Sin errores de lint o type
  - **Verify**: `pnpm lint && pnpm check-types`
  - **Commit**: `chore(e2e): pass quality checkpoint`
  - _Research: pnpm lint, pnpm check-types_

## Phase 2: Refactoring

- [ ] 2.1 [P] Refactorizar code quality en trip-crud.spec.ts
  - **Do**:
    1. Eliminar todos waitForTimeout del código
    2. Reemplazar con Playwright waits: toBeVisible, toBeHidden, toHaveCount
    3. Eliminar assertions débiles: `expect(true).toBe(true)` o `count >= 0`
    4. Reemplazar con assertions específicas: toContain, toHaveText
  - **Files**: `tests/e2e/trip-crud.spec.ts`
  - **Done when**: 0 ocurrencias de waitForTimeout, 0 weak assertions
  - **Verify**: `! grep -q "waitForTimeout" tests/e2e/trip-crud.spec.ts && echo "PASS"`
  - **Commit**: `refactor(test): remove waitForTimeout and weak assertions`
  - _Requirements: NFR-4, NFR-5, NFR-6_
  - _Design: Test Strategy_

- [ ] 2.2 [VERIFY] Quality checkpoint: test run
  - **Do**:
    1. Ejecutar tests: `pnpm test trip-crud.spec.ts`
    2. Verificar todos pasan
  - **Files**: `tests/e2e/trip-crud.spec.ts`
  - **Done when**: Todos los tests pasan
  - **Verify**: `pnpm test trip-crud.spec.ts`
  - **Commit**: `chore(e2e): pass test run`
  - _Research: pnpm test_

## Phase 3: Testing

- [ ] 3.1 [P] Crear trip-states.spec.ts - Test Pause Trip
  - **Do**:
    1. Crear `tests/e2e/trip-states.spec.ts`
    2. Test: "should pause a recurring trip"
    3. Configurar dialog handler ANTES del click
    4. Click `.pause-btn` en trip recurrente activo
    5. Dialog handler acepta: dialog.accept()
    6. Validar: tripCard.setAttribute('data-active', 'false'), badge text toContain("Inactivo")
  - **Files**: `tests/e2e/trip-states.spec.ts`
  - **Done when**: Test pause trip creado
  - **Verify**: `grep -q "should pause a recurring trip" tests/e2e/trip-states.spec.ts && echo "PASS"`
  - **Commit**: `test(e2e): create pause trip test`
  - _Requirements: FR-6, AC-5.1 to AC-5.10_
  - _Design: Test States (trip-states.spec.ts)_

- [ ] 3.2 [P] Crear trip-states.spec.ts - Test Resume Trip
  - **Do**:
    1. Test: "should resume a paused trip"
    2. Configurar dialog handler
    3. Click `.resume-btn` en trip recurrente inactivo
    4. Dialog handler acepta
    5. Validar: tripCard.setAttribute('data-active', 'true'), badge text toContain("Activo")
  - **Files**: `tests/e2e/trip-states.spec.ts`
  - **Done when**: Test resume trip creado
  - **Verify**: `grep -q "should resume a paused trip" tests/e2e/trip-states.spec.ts && echo "PASS"`
  - **Commit**: `test(e2e): create resume trip test`
  - _Requirements: FR-7, AC-5.1 to AC-5.10_
  - _Design: Test States (trip-states.spec.ts)_

- [ ] 3.3 [P] Crear trip-states.spec.ts - Test Complete Cancel Punctual
  - **Do**:
    1. Test: "should complete a punctual trip"
    2. Verificar trip type es puntual
    3. Click `.complete-btn` en trip puntual
    4. Validar badge text toContain("Completado"), buttons desaparecen
  - **Files**: `tests/e2e/trip-states.spec.ts`
  - **Done when**: Test complete trip creado
  - **Verify**: `grep -q "should complete a punctual trip" tests/e2e/trip-states.spec.ts && echo "PASS"`
  - **Commit**: `test(e2e): create complete punctual trip test`
  - _Requirements: FR-8, AC-6.1 to AC-6.7_
  - _Design: Test States (trip-states.spec.ts)_

- [ ] 3.4 [P] Crear trip-states.spec.ts - Test Cancel Punctual
  - **Do**:
    1. Test: "should cancel a punctual trip"
    2. Click `.cancel-btn` en trip puntual
    3. Validar badge text toContain("Cancelado"), buttons desaparecen
  - **Files**: `tests/e2e/trip-states.spec.ts`
  - **Done when**: Test cancel trip creado
  - **Verify**: `grep -q "should cancel a punctual trip" tests/e2e/trip-states.spec.ts && echo "PASS"`
  - **Commit**: `test(e2e): create cancel punctual trip test`
  - _Requirements: FR-9, AC-6.1 to AC-6.7_
  - _Design: Test States (trip-states.spec.ts)_

- [ ] 3.5 [VERIFY] Quality checkpoint: lint && typecheck && test
  - **Do**:
    1. Ejecutar lint
    2. Ejecutar typecheck
    3. Ejecutar tests
  - **Files**: `tests/e2e/trip-states.spec.ts`
  - **Done when**: Todos los quality gates pasan
  - **Verify**: `pnpm lint && pnpm check-types && pnpm test`
  - **Commit**: `chore(e2e): pass quality checkpoint`
  - _Research: pnpm lint, pnpm check-types, pnpm test_

## Phase 4: Quality Gates

- [ ] 4.1 Local quality check
  - **Do**:
    1. Run lint: `pnpm lint`
    2. Run typecheck: `pnpm check-types`
    3. Run tests: `pnpm test`
  - **Done when**: All commands pass
  - **Verify**: `pnpm lint && pnpm check-types && pnpm test`
  - **Commit**: `fix(e2e): address lint/type issues`

## Phase 5: PR Lifecycle

- [ ] 5.1 Verify tests pass in CI
  - **Do**:
    1. Push branch: `git push -u origin e2e-tests`
    2. Create PR: `gh pr create --title "E2E Tests CRUD para Viajes EV Trip Planner" --body "Tests E2E completos para CRUD de viajes"`
    3. Monitor CI: `gh pr checks --watch`
  - **Verify**: `gh pr checks` shows all green
  - **Done when**: CI pipeline passes
  - **Commit**: None

## Phase 6: Verification Final

- [ ] VF [VERIFY] Goal verification: E2E tests all pass
  - **Do**:
    1. Run full test suite: `pnpm test`
    2. Verify no waitForTimeout: `! grep -r "waitForTimeout" tests/e2e/`
    3. Verify no weak assertions: `! grep -r "expect(true).toBe(true)" tests/e2e/`
    4. Document results in .progress.md
  - **Verify**: All tests pass, 0 waitForTimeout, 0 weak assertions
  - **Done when**: Full test suite passes
  - **Commit**: `chore(e2e): verify E2E tests complete`

## Notes
- **Tests created**: trip-crud.spec.ts (3 tests), trip-states.spec.ts (4 tests)
- **Tests eliminated**: 6 files (5 Nivel 1 + test-integration.spec.ts)
- **Design pattern**: Dialog handler ANTES del click es obligatorio
- **Selector pattern**: `ev-trip-planner-panel >> .element` para Shadow DOM
