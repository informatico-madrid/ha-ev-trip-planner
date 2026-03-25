# Requirements: E2E Tests CRUD para Viajes EV Trip Planner

## Goal
Crear tests E2E con Playwright que validen el flujo completo CRUD (Create, Read, Update, Delete) de viajes en el panel ev-trip-planner-panel, usando selectors correctos con Shadow DOM y servicios de Home Assistant.

## User Stories

### US-1: Crear viaje recurrente
**As a** usuario del panel EV Trip Planner
**I want to** crear un viaje recurrente vía UI
**So that** pueda planificar rutas regulares automáticamente

**Acceptance Criteria:**
- [ ] AC-1.1: Panel muestra botón `.add-trip-btn` visible
- [ ] AC-1.2: Click en botón abre overlay `.trip-form-overlay` en <10s
- [ ] AC-1.3: Select `#trip-type` permite elegir 'recurrente'
- [ ] AC-1.4: Select `#trip-day` muestra opciones 1-7 (días semana)
- [ ] AC-1.5: Input `#trip-time` acepta formato HH:MM (ej: "08:00")
- [ ] AC-1.6: Input `#trip-km` acepta valores numéricos positivos
- [ ] AC-1.7: Input `#trip-kwh` acepta valores numéricos positivos
- [ ] AC-1.8: Input `#trip-description` acepta texto arbitrario
- [ ] AC-1.9: Submit llama servicio `ev_trip_planner.trip_create`
- [ ] AC-1.10: Overlay cierra tras submit exitoso
- [ ] AC-1.11: Trip card aparece en `.trips-list`
- [ ] AC-1.12: Card muestra badge "Recurrente" con emoji
- [ ] AC-1.13: Card muestra día seleccionado con nombre completo (Lunes, Martes, etc.)
- [ ] AC-1.14: Card muestra hora HH:MM
- [ ] AC-1.15: Card muestra distancia en formato "X.X km"

### US-2: Crear viaje puntual
**As a** usuario del panel
**I want to** crear un viaje puntual con fecha/hora específica
**So that** pueda planificar eventos únicos

**Acceptance Criteria:**
- [ ] AC-2.1: Select `#trip-type` permite elegir 'puntual'
- [ ] AC-2.2: Input `#trip-datetime` muestra formato datetime-local
- [ ] AC-2.3: Input acepta timestamp "YYYY-MM-DDTHH:MM"
- [ ] AC-2.4: Submit llama servicio `ev_trip_planner.trip_create`
- [ ] AC-2.5: Card muestra badge "Puntual" con fecha HH:MM
- [ ] AC-2.6: Card muestra botón "✅ Completar" (visible solo para puntuales)
- [ ] AC-2.7: Card muestra botón "❌ Cancelar" (visible solo para puntuales)

### US-3: Editar viaje existente
**As a** usuario
**I want to** modificar detalles de viaje existente
**So that** pueda actualizar cambios en horarios/distancia

**Acceptance Criteria:**
- [ ] AC-3.1: Trip card muestra botón "✏️ Editar" (.edit-btn)
- [ ] AC-3.2: Click en edit abre overlay con campos pre-populated
- [ ] AC-3.3: Select `#trip-type` refleja tipo actual
- [ ] AC-3.4: `#trip-time` o `#trip-datetime` refleja valor actual
- [ ] AC-3.5: `#trip-km` refleja distancia actual
- [ ] AC-3.6: `#trip-kwh` refleja consumo actual
- [ ] AC-3.7: `#trip-description` refleja descripción actual
- [ ] AC-3.8: Submit actualiza viaje con servicio `ev_trip_planner.trip_update`
- [ ] AC-3.9: Overlay cierra tras update exitoso
- [ ] AC-3.10: Card UI refleja valores actualizados inmediatamente
- [ ] AC-3.11: Click en "Cancelar" (.btn-secondary) cierra sin guardar
- [ ] AC-3.12: Click en "X Close" (.close-form-btn) cierra sin guardar

### US-4: Eliminar viaje
**As a** usuario
**I want to** eliminar viaje no necesario
**So that** limpie lista de viajes obsoletos

**Acceptance Criteria:**
- [ ] AC-4.1: Trip card muestra botón "🗑️ Eliminar" (.delete-btn)
- [ ] AC-4.2: Click en delete abre dialog de confirmación nativo de browser
- [ ] AC-4.3: Dialog muestra mensaje de confirmación
- [ ] AC-4.4: Listener en event `dialog` captura confirmación
- [ ] AC-4.5: `dialog.accept()` llama servicio `ev_trip_planner.delete_trip`
- [ ] AC-4.6: `dialog.dismiss()` cancela eliminación
- [ ] AC-4.7: Trip card desaparece de lista tras confirmación
- [ ] AC-4.8: Si último viaje eliminado, muestra mensaje ".no-trips"
- [ ] AC-4.9: `.trips-section` permanece visible tras eliminación
- [ ] AC-4.10: `.add-trip-btn` permanece visible tras eliminación

### US-5: Pausar/Reanudar viaje recurrente
**As a** usuario
**I want to** pausar o reanudar viaje recurrente
**So that** pueda detener temporalmente viajes sin eliminarlos

**Acceptance Criteria:**
- [ ] AC-5.1: Viaje activo muestra botón "⏸️ Pausar" (.pause-btn)
- [ ] AC-5.2: Viaje inactivo muestra botón "▶️ Reanudar" (.resume-btn)
- [ ] AC-5.3: Click en pause abre dialog de confirmación
- [ ] AC-5.4: `dialog.accept()` llama servicio `ev_trip_planner.pause_recurring_trip`
- [ ] AC-5.5: Viaje muestra atributo `data-active="false"` tras pausa
- [ ] AC-5.6: Badge cambia a estado "Inactivo"
- [ ] AC-5.7: Click en resume llama servicio `ev_trip_planner.resume_recurring_trip`
- [ ] AC-5.8: Viaje muestra atributo `data-active="true"` tras reanudar
- [ ] AC-5.9: Badge cambia a estado "Activo"
- [ ] AC-5.10: Count de trips no cambia tras pause/resume

### US-6: Completar/Cancelar viaje puntual
**As a** usuario
**I want to** marcar viaje puntual como completado o cancelado
**So that** registre fin de viaje único sin eliminarlo

**Acceptance Criteria:**
- [ ] AC-6.1: Viaje puntual muestra botón "✅ Completar" (.complete-btn)
- [ ] AC-6.2: Viaje puntual muestra botón "❌ Cancelar" (cancel-btn)
- [ ] AC-6.3: Click en complete llama servicio `ev_trip_planner.complete_punctual_trip`
- [ ] AC-6.4: Click en cancel llama servicio `ev_trip_planner.cancel_punctual_trip`
- [ ] AC-6.5: Viaje muestra badge de estado "Completado" o "Cancelado"
- [ ] AC-6.6: Botones complete/cancel desaparecen tras acción
- [ ] AC-6.7: Viaje permanece en lista (no se elimina)

### US-7: Validar UI del panel
**As a** tester
**I want to** verificar elementos UI básicos del panel
**So that** garantice render correcto del componente Lit

**Acceptance Criteria:**
- [ ] AC-7.1: Custom element `ev-trip-planner-panel` se registra en customElements
- [ ] AC-7.2: `.add-trip-btn` visible en top del panel
- [ ] AC-7.3: `.trips-section` visible con header
- [ ] AC-7.4: `.trips-header` muestra texto "Viajes Programados"
- [ ] AC-7.5: `.trips-list` contiene `.trip-card` elementos
- [ ] AC-7.6: `.no-trips` muestra mensaje cuando lista vacía
- [ ] AC-7.7: Shadow DOM traversal funciona con selector `>>`

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Panel Lit renderizado correctamente | High | Custom element `ev-trip-planner-panel` existe en DOM |
| FR-2 | Selector Shadow DOM `>>` funciona | High | `ev-trip-planner-panel >> .trip-card` encuentra elementos |
| FR-3 | Servicio trip_create | High | Crea viaje con parámetros: vehicle_id, type, day_of_week/time/datetime, km, kwh, description |
| FR-4 | Servicio trip_update | High | Actualiza viaje con trip_id y campos modificables |
| FR-5 | Servicio delete_trip | High | Elimina viaje con vehicle_id y trip_id |
| FR-6 | Servicio pause_recurring_trip | Medium | Pausa viaje recurrente |
| FR-7 | Servicio resume_recurring_trip | Medium | Reanuda viaje recurrente |
| FR-8 | Servicio complete_punctual_trip | Medium | Marca viaje puntual como completado |
| FR-9 | Servicio cancel_punctual_trip | Medium | Cancela viaje puntual |
| FR-10 | Dialog de confirmación | High | Browser native dialog aparece al eliminar/pausar |
| FR-11 | Form overlay | High | `.trip-form-overlay` aparece y desaparece correctamente |
| FR-12 | Estado data-active | Medium | Trip card atributo refleja activo/inactivo |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Performance test | Load time | Panel visible en <5s |
| NFR-2 | Test execution time | Duration | CRUD completo <60s |
| NFR-3 | Test reliability | Pass rate | 95% success rate |
| NFR-4 | No wait for timeout | Code quality | 0 occurrences de waitForTimeout |
| NFR-5 | Playwright waits | Code quality | 100% uso de waitForSelector/toBeVisible |
| NFR-6 | Specific assertions | Test quality | 0 occurrences de expect(true).toBe(true) |

## Glossary
- **Shadow DOM**: Encapsulación de DOM de web components (Lit)
- **Selector >>**: Syntax Playwright para atravesar Shadow DOM boundaries
- **Recurrente**: Viaje que se repite cada X día de la semana
- **Puntual**: Viaje único con fecha y hora específica
- **Overlay**: Formulario flotante sobre panel principal
- **Trip card**: Elemento UI que representa un viaje en lista
- **Service**: Función de Home Assistant para ejecutar acciones

## Out of Scope
- Tests de performance de carga inicial
- Tests cross-browser (solo Chrome/Firefox)
- Tests de dashboards de Lovelace antiguos
- Tests de creación de PRs o CI/CD
- Tests de configuración de usuario/contraseña
- Tests de autenticación HA (bypass login)

## Dependencies
- **Trusted networks**: `configuration.yaml` debe tener `allow_bypass_login_for_ips` con IPs 127.0.0.1 y 192.168.1.0/24
- **Custom panel**: ev-trip-planner-panel v3.0.0+ con Shadow DOM support
- **Home Assistant**: Versión con custom_components.ev_trip_planner instalado
- **Playwright**: Browser Chrome/Firefox instalado en environment de tests

## Success Criteria
- [ ] Todos los tests E2E ejecutan sin `waitForTimeout`
- [ ] Tests de CRUD completan flujo Create → Read → Update → Delete
- [ ] Servicios HA se llaman con parámetros correctos
- [ ] Shadow DOM traversal con `>>` funciona para todos los selectors
- [ ] Dialog de confirmación se maneja correctamente
- [ ] Atributos `data-active` reflejan estado correcto
- [ ] Tests son deterministas (95%+ pass rate)
- [ ] Tests ejecutan en <60s por scenario completo

## Unresolved Questions
- ¿`allow_bypass_login_for_ips` está disponible en la versión exacta de HA en test-ha?
- ¿Qué nombre de día exacto muestra panel para `day_of_week=1`? (Lunes, Monday, etc.)
- ¿Dialog message exacto para confirmación de delete/pause?
- ¿Formato exacto de fecha para trips puntuales en UI?

## Next Steps
1. Actualizar configuration.yaml con `allow_bypass_login_for_ips`
2. Eliminar tests de Nivel 1 (dashboard-crud, test-performance, test-cross-browser, test-pr-creation, test-panel-loading)
3. Refactorizar tests de Nivel 2 (remover waitForTimeout, reemplazar con Playwright waits)
4. Crear test de auth validation con bypass configuration
5. Validar que `allow_bypass_login_for_ips` funciona en HA version actual
