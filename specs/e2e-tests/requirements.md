# Requirements: E2E Tests for EV Trip Planner

## Goal
Validar funcionalidad completa del panel EV Trip Planner mediante pruebas E2E que cubran operaciones CRUD, estados de viajes y comportamiento del Shadow DOM de Lit Components, asegurando que los tests validen funcionalidad real (persistencia en HA) y no solo UI estática.

## Technical Context

### Shadow DOM y Lit Components

El panel `ev-trip-planner-panel` utiliza Lit v2.8.0 con **Shadow DOM OPEN** por defecto. Esto significa:

- ✅ Playwright puede atravesar Shadow DOM con el selector `>>`
- ✅ No se requieren workarounds ni JavaScript injection
- ✅ Los elementos del template están accesibles directamente

**Patrones de Selectores Validados:**
```typescript
ev-trip-planner-panel >> .add-trip-btn
ev-trip-planner-panel >> .trip-card
ev-trip-planner-panel >> #trip-type
ev-trip-planner-panel >> button[type="submit"]
```

### Servicios de Home Assistant

| Servicio | Parámetros | Descripción |
|----------|------------|-------------|
| `ev_trip_planner.trip_create` | vehicle_id, type, day_of_week/time/datetime, km, kwh, description | Crear viaje |
| `ev_trip_planner.trip_update` | vehicle_id, trip_id, type, day_of_week/time/datetime, km, kwh, description | Actualizar viaje |
| `ev_trip_planner.delete_trip` | vehicle_id, trip_id | Eliminar viaje |
| `ev_trip_planner.pause_recurring_trip` | vehicle_id, trip_id | Pausar viaje recurrente |
| `ev_trip_planner.resume_recurring_trip` | vehicle_id, trip_id | Reanudar viaje recurrente |
| `ev_trip_planner.complete_punctual_trip` | vehicle_id, trip_id | Completar viaje puntual |
| `ev_trip_planner.cancel_punctual_trip` | vehicle_id, trip_id | Cancelar viaje puntual |
| `ev_trip_planner.trip_list` | vehicle_id | Listar viajes |

## User Stories

### US-1: Crear viaje recurrente
**As a** usuario del panel EV Trip Planner
**I want to** crear un nuevo viaje recurrente con configuración completa
**So that** tenga viajes programados que se ejecuten automáticamente

**Acceptance Criteria:**
- [ ] AC-1.1: Dado que estoy en el panel del vehículo, cuando hago click en `.add-trip-btn`, entonces se muestra el `.trip-form-overlay`
- [ ] AC-1.2: Dado que el formulario está visible, cuando selecciono "recurrente" en `ev-trip-planner-panel >> #trip-type`, elijo día en `ev-trip-planner-panel >> #trip-day` y completo hora en `ev-trip-planner-panel >> #trip-time`, entonces el formulario guarda correctamente
- [ ] AC-1.3: Dado que estoy rellenando el formulario, cuando ingreso valores en `#trip-km` y `#trip-kwh`, estos se validan como números positivos y se envían al servicio `ev_trip_planner.trip_create` con parámetros vehicle_id, type="recurrente", day_of_week, time, km, kwh, description
- [ ] AC-1.4: Dado que el formulario está completo, cuando hago submit en `button[type="submit"]`, entonces se cierra el `.trip-form-overlay` y aparece una nueva `.trip-card` en la lista
- [ ] AC-1.5: Dado que el viaje se creó, entonces la `.trip-card` muestra tipo "recurrente" con badge `.status-active` verde, hora programada en `.trip-time`, y la llamada al servicio `ev_trip_planner.trip_create` se ejecutó con parámetros correctos

### US-2: Crear viaje puntual
**As a** usuario del panel EV Trip Planner
**I want to** crear un nuevo viaje puntual con destino y detalles específicos
**So that** planifique viajes únicos con información detallada

**Acceptance Criteria:**
- [ ] AC-2.1: Dado que estoy en el panel del vehículo, cuando selecciono "puntual" en `#trip-type`, entonces el formulario muestra campos relevantes para viajes únicos (input datetime en lugar de input time)
- [ ] AC-2.2: Dado que el formulario está visible, cuando ingreso destino, distancia estimada en `#trip-km` y kWh esperado en `#trip-kwh`, entonces estos valores se guardan correctamente y se envían al servicio `ev_trip_planner.trip_create` con parámetros vehicle_id, type="puntual", datetime, km, kwh, description, destination
- [ ] AC-2.3: Dado que el viaje puntual se creó, entonces la `.trip-card` muestra estado "Pendiente" con badge `.status-pending` y aparece botón `.complete-btn` en `.trip-actions`
- [ ] AC-2.4: Dado que el viaje es puntual, cuando hago click en `.complete-btn`, entonces se ejecuta el servicio `ev_trip_planner.complete_punctual_trip` con parámetros vehicle_id y trip_id
- [ ] AC-2.5: Dado que el viaje es puntual, cuando hago click en `.cancel-btn`, entonces se ejecuta el servicio `ev_trip_planner.cancel_punctual_trip` con parámetros vehicle_id y trip_id

### US-3: Editar viaje existente
**As a** usuario del panel EV Trip Planner
**I want to** modificar los parámetros de un viaje ya creado
**So that** ajuste horarios, distancias o descripciones cuando cambien las necesidades

**Acceptance Criteria:**
- [ ] AC-3.1: Dado que existen `.trip-card` en la lista, cuando hago click en `.edit-btn` dentro de `.trip-actions`, entonces se abre el `.trip-form-overlay` con los valores actuales del viaje cargados en `#edit-trip-time`, `#edit-trip-km`, etc.
- [ ] AC-3.2: Dado que el formulario está cargado con datos existentes, cuando modifico valores en `#edit-trip-time`, `#edit-trip-km` y `#edit-trip-kwh`, estos se actualizan reactivamente en el DOM
- [ ] AC-3.3: Dado que el formulario está completo, cuando hago submit en `button[type="submit"]`, entonces se cierra el `.trip-form-overlay` y la `.trip-card` muestra los nuevos valores
- [ ] AC-3.4: Dado que edito un viaje, entonces la llamada al servicio `ev_trip_planner.trip_update` se ejecuta con parámetros vehicle_id, trip_id, y los nuevos valores, y la `.trip-card` actualizada refleja los cambios

### US-4: Eliminar viaje
**As a** usuario del panel EV Trip Planner
**I want to** eliminar un viaje que ya no necesite
**So that** mantenga la lista de viajes actualizada y libre de entradas obsoletas

**Acceptance Criteria:**
- [ ] AC-4.1: Dado que existe una `.trip-card`, cuando hago click en `.delete-btn` dentro de `.trip-actions`, entonces aparece un diálogo de confirmación del navegador
- [ ] AC-4.2: Dado que el diálogo de confirmación está visible, cuando acepto la eliminación mediante `dialog.accept()`, entonces se ejecuta el servicio `ev_trip_planner.delete_trip` con parámetros vehicle_id y trip_id, y la `.trip-card` correspondiente desaparece del DOM
- [ ] AC-4.3: Dado que elimino el último viaje, entonces se muestra el mensaje `.no-trips` indicando que no hay viajes configurados y la lista `.trip-card` tiene count = 0
- [ ] AC-4.4: Dado que elimino un viaje, entonces la llamada al servicio `ev_trip_planner.delete_trip` se ejecuta en Home Assistant y persiste en el almacenamiento del integracion

### US-5: Pausar/Reanudar viaje recurrente
**As a** usuario del panel EV Trip Planner
**I want to** pausar y reanudar viajes recurrentes según necesidades cambiantes
**So that** controle cuándo se ejecutan automáticamente los viajes programados

**Acceptance Criteria:**
- [ ] AC-5.1: Dado que existe un viaje recurrente activo, cuando hago click en `.pause-btn` dentro de `.trip-actions`, entonces aparece un diálogo de confirmación del navegador
- [ ] AC-5.2: Dado que acepto pausar el viaje mediante `dialog.accept()`, entonces se ejecuta el servicio `ev_trip_planner.pause_recurring_trip` con parámetros vehicle_id y trip_id, el `.trip-card` cambia `data-active` a "false" y el badge `.trip-status` muestra texto "Inactivo" con clase `.status-inactive`
- [ ] AC-5.3: Dado que el viaje está pausado (data-active="false"), entonces el `.trip-actions` muestra botón `.resume-btn` en lugar de `.pause-btn`
- [ ] AC-5.4: Dado que el viaje está pausado, cuando hago click en `.resume-btn`, entonces se ejecuta el servicio `ev_trip_planner.resume_recurring_trip` con parámetros vehicle_id y trip_id, el `.trip-card` cambia `data-active` a "true" y el badge `.trip-status` muestra texto "Activo" con clase `.status-active`
- [ ] AC-5.5: Dado que reanudo el viaje, entonces la llamada al servicio `ev_trip_planner.resume_recurring_trip` se ejecuta en Home Assistant y persiste el estado activo

### US-6: Completar/Cancelar viaje puntual
**As a** usuario del panel EV Trip Planner
**I want to** completar o cancelar viajes puntuales según se ejecuten o no
**So that** mantenga el historial de viajes actualizado y preciso

**Acceptance Criteria:**
- [ ] AC-6.1: Dado que existe un viaje puntual pendiente, cuando hago click en `.complete-btn` dentro de `.trip-actions`, entonces se ejecuta el servicio `ev_trip_planner.complete_punctual_trip` con parámetros vehicle_id y trip_id, y el badge `.trip-status` cambia a texto "Completado" con clase `.status-completed`
- [ ] AC-6.2: Dado que completo el viaje, entonces el `.trip-card` ya no muestra elementos `.trip-action-btn` (count = 0) y el viaje desaparece de la lista de pendientes
- [ ] AC-6.3: Dado que existe un viaje puntual pendiente, cuando hago click en `.cancel-btn` dentro de `.trip-actions`, entonces aparece un diálogo de confirmación del navegador
- [ ] AC-6.4: Dado que acepto cancelar el viaje mediante `dialog.accept()`, entonces se ejecuta el servicio `ev_trip_planner.cancel_punctual_trip` con parámetros vehicle_id y trip_id, el badge `.trip-status` muestra texto "Cancelado" con clase `.status-cancelled`, y desaparecen los `.trip-action-btn`
- [ ] AC-6.5: Dado que marco como completado o cancelado, entonces la llamada al servicio correspondiente (`ev_trip_planner.complete_punctual_trip` o `ev_trip_planner.cancel_punctual_trip`) se ejecuta en Home Assistant y persiste el estado en el backend

### US-7: Entorno sin autenticación
**As a** tester de pruebas E2E
**I want to** ejecutar pruebas sin necesidad de login manual
**So that** las pruebas sean automatizadas, rápidas y reproducibles

**Acceptance Criteria:**
- [ ] AC-7.1: Dado que navego al panel con `page.goto(url, { waitUntil: 'domcontentloaded' })`, entonces la página carga inmediatamente sin redirigir a login porque el backend reconoce la IP de confianza
- [ ] AC-7.2: Dado que el entorno HA está configurado con `trusted_networks` que incluye `127.0.0.1` y `::1`, entonces el proveedor de autenticación bypass se activa automáticamente para el contenedor de tests
- [ ] AC-7.3: Dado que el entorno tiene configurado `allow_bypass_login: true` en `auth_providers`, entonces puedo acceder directamente a `/panel/ev-trip-planner-{VEHICLE_ID}` sin credenciales y sin pantalla de autorización
- [ ] AC-7.4: Dado que ejecuto las pruebas, entonces todas las interacciones funcionan sin prompts de autenticación y los navegadores se cargan directamente en el panel del vehículo
- [ ] AC-7.5: Dado que el entorno usa `trusted_users` con el usuario ID correcto, entonces el backend identifica al usuario y aplica los permisos correctos sin requerir login

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Create recurring trip | High | Viaje se guarda con tipo recurrente, día y hora programada |
| FR-2 | Create punctual trip | High | Viaje se guarda con tipo puntual, destino y detalles |
| FR-3 | Edit existing trip | High | Valores actualizados persisten en UI y backend |
| FR-4 | Delete trip | High | Viaje eliminado y UI actualizada tras confirmación |
| FR-5 | Pause recurring trip | Medium | Viaje marcado como inactivo con `data-active="false"` |
| FR-6 | Resume recurring trip | Medium | Viaje marcado como activo con `data-active="true"` |
| FR-7 | Complete punctual trip | Medium | Viaje marcado como completado sin acciones |
| FR-8 | Cancel punctual trip | Medium | Viaje marcado como cancelado sin acciones |
| FR-9 | Validate trip list | High | `.trip-card` count refleja viajes persistidos en HA |
| FR-10 | Handle empty state | Medium | `.no-trips` mensaje visible sin viajes |
| FR-11 | Shadow DOM navigation | High | Selectores con `>>` atraviesan Shadow DOM correctamente |
| FR-12 | Form validation | High | Campos numéricos aceptan solo valores válidos |
| FR-13 | Confirmation dialogs | High | Eliminaciones y pausas requieren confirmación |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | No hardcoded waits | Time | No usar `waitForTimeout` en tests |
| NFR-2 | Shadow DOM selectors | Pattern | Usar `>>` para atravesar Shadow DOM |
| NFR-3 | Navigation strategy | Performance | Usar `waitUntil: 'domcontentloaded'` |
| NFR-4 | No authentication | Setup | Bypass login con trusted_networks |
| NFR-5 | Real functionality validation | Test quality | Validar persistencia en HA, no solo UI estática |
| NFR-6 | Test flakiness | Reliability | Usar Playwright waits nativos, no timeouts |
| NFR-7 | Test maintainability | Pattern | Selectores estables con clases CSS identificables |
| NFR-8 | Environment configuration | Config | VEHICLE_ID y HA_URL desde environment variables |
| NFR-9 | Dialog handling | Pattern | Usar `page.on('dialog', dialog => dialog.accept())` para confirmaciones |
| NFR-10 | Service execution validation | Quality | Validar que los servicios HA se ejecutan correctamente, no solo cambios UI |
| NFR-11 | data attribute tracking | Pattern | Validar cambios en `data-active` attribute para estados de viajes |
| NFR-12 | Status badge classes | Pattern | Validar clases `.status-active`, `.status-inactive`, `.status-pending`, `.status-completed`, `.status-cancelled` |

## Glossary
- **Recurrente**: Viaje que se programa repetidamente (diario/semanal)
- **Puntual**: Viaje único con destino específico
- **Shadow DOM**: Encapsulamiento de DOM en componentes web modernos
- **Lit Components**: Framework de UI de Google usado en este panel
- **VEHICLE_ID**: Identificador del vehículo en Home Assistant
- **Trips**: Viajes configurados en el panel EV Trip Planner
- **CRUD**: Create, Read, Update, Delete - operaciones básicas de datos
- **Dialog**: Ventana modal de confirmación de eliminación

## Patrones de Testing Recomendados

```typescript
// 1. Navegación sin authentication (trusted_networks bypass)
await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
  waitUntil: 'domcontentloaded'  // NO networkidle (WebSockets abiertos)
});

// 2. Esperar renderizado del componente Lit
await page.locator('ev-trip-planner-panel').first().waitFor({ state: 'attached' });

// 3. Interactuar con elementos del Shadow DOM usando >>
const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
await addTripBtn.click();

// 4. Validar formularios
const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
await expect(formOverlay).toBeVisible();

// 5. Rellenar formulario con selectores internos
await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
await page.locator('ev-trip-planner-panel >> #trip-time').fill('08:00');
await page.locator('ev-trip-planner-panel >> #trip-km').fill('25.5');
await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('5.2');
await page.locator('ev-trip-planner-panel >> #trip-description').fill('Test trip');

// 6. Submit y validar cierre del overlay
await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
await expect(formOverlay).toBeHidden();

// 7. Validar persistencia en UI
const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
await expect(tripCards.count()).toBeGreaterThan(0);

// 8. Validar estados con data attributes
const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
await expect(tripCard).toHaveAttribute('data-active', 'true');

// 9. Validar badges de estado con clases específicas
await expect(tripCard.locator('.trip-status.status-active')).toBeVisible();

// 10. Manejo de diálogos de confirmación
page.on('dialog', async dialog => {
  await dialog.accept();  // O dialog.dismiss() para cancelar
});

// 11. Validar ausencia de elementos
await expect(tripCard.locator('.trip-action-btn')).toHaveCount(0);

// 12. Validar mensaje de estado vacío
await expect(page.locator('ev-trip-planner-panel >> .no-trips')).toBeVisible();
```

## Out of Scope
- Pruebas de API directa (solo UI y servicios indirectos)
- Validación de emails o notificaciones push
- Pruebas de performance o carga
- Migración de datos o backups
- Configuración inicial del panel (asume panel ya instalado)
- Validación de estados de sensores externos (asume VEHICLE_ID válido)

## Dependencies
- Home Assistant URL (`HA_URL`) con configuración de `trusted_networks` y `allow_bypass_login`
- VEHICLE_ID existente en Home Assistant (ej: "Coche2")
- Integración `ev_trip_planner` ya instalada y configurada
- Panel personalizado `ev-trip-planner-{VEHICLE_ID}` desplegado
- Playwright test framework y browser instalado
- Environment variables configuradas en `.env` file

## Success Criteria
- [x] 7 User Stories completamente especificadas con AC testables
- [x] 13 Functional Requirements con prioridades definidas
- [x] 8 Non-Functional Requirements con métricas claras
- [x] Shadow DOM testing validado con selector `>>`
- [x] Entorno sin login documentado y configurado
- [x] Todas las operaciones CRUD y estados cubiertos
- [x] Validación de funcionalidad real, no solo UI

## Unresolved Questions
- ¿VEHICLE_ID específico debe usarse en documentación o mantenerse genérico?
- ¿El campo `#trip-day` es obligatorio para viajes recurrentes o opcional?
- ¿Los viajes recurrentes pueden programarse en diferentes días (semanal, mensual) o solo diario?
- ¿Existe límite de caracteres para descripciones de viajes?

## Next Steps
1. Approve requirements document for implementation
2. Update test files to cover all 7 user stories
3. Verify environment configuration for trusted_networks
4. Run full E2E test suite as validation
5. Document any flaky tests and add retries if needed
