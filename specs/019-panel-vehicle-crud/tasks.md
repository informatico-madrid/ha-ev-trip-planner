# Tasks: Panel de Control de Vehículo con CRUD de Viajes

**Feature**: `019-panel-vehicle-crud`  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Credenciales para Verificaciones

```
Home Assistant URL: http://localhost:18124 (test-ha para verificaciones AUTOMÁTICAS)
Usuario: available in environment (obtener de variables de entorno)
Password: available in environment (obtener de variables de entorno)
Token LTA: available in environment (obtener de variables de entorno)
```

## Despliegue para Verificaciones

**IMPORTANTE**: Antes de ejecutar cualquier verificación [VERIFY:BROWSER] o [VERIFY:API], DEBES iniciar test-ha y desplegar los cambios:

```bash
# Iniciar test-ha si no está运行
.ralph/scripts/start_test_ha.sh

# Copia componentes al directorio de test-ha
cp -r $WORKTREE_PATH/custom_components/ev_trip_planner test-ha/config/custom_components/

# Espera a que HA esté disponible
sleep 30

# Verifica que test-ha responde en http://localhost:18124
curl -s http://localhost:18124/api/ | grep -q "auth" && echo "test-ha OK"
```

**Después del despliegue**, ejecuta la verificación específica de la tarea.

## Dependencies

```
US1 (Error vehicle_id) ──┐
                         ├──► Phase Final: Polish
US2 (Nombre dispositivo)─┤
                         │
US3 (assist_satellite)──┤
                         │
US4 (Eliminación panel)─┤
                         │
US5 (Actualización sensores)─┤
US6 (Sensores vehículo) ──┤
US7 (Viajes UI legible) ──┤
US8 (CRUD viajes) ───────┘
US9 (UI bonita) ───────────►
```

## Phase 1: Setup

No hay tareas de setup requeridas - el proyecto ya existe.

---

## Phase 2: Foundational

- [x] T001 Investigar métodos de implementación en Home Assistant Core para panel_custom y EntitySelector [use: mcp-shell]

---

## Phase 3: User Story 1 - Corregir error "Cannot render - no vehicle_id" (P1)

**Goal**: El panel nativo renderiza correctamente sin error de vehicle_id  
**Independent Test**: Acceder al panel del vehículo y verificar que renderiza correctamente

### Implementation

- [x] T002 [P] [US1] Modificar panel.js connectedCallback para obtener vehicle_id de window.location ANTES de esperar hass [use: homeassistant-config]
- [x] T003 [P] [US1] Modificar panel.js método _render() para intentar obtener vehicle_id de URL como último recurso [use: homeassistant-config]
- [x] T004 [US1] Agregar logging mejorado para debugging de vehicle_id [use: homeassistant-config]
- [x] T005 [VERIFY:BROWSER] Verificar que el panel del vehículo renderiza correctamente:
  1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba
  2. Navegar a HA (hacer login si es necesario)
  3. Ir a Integraciones y crear un vehículo de prueba si no existe
  4. Navegar al panel /ev-trip-planner-{vehicle_id}
  5. Verificar que NO aparece "Cannot render - no vehicle_id"
  6. SI TODO OK: Emitir SIGNAL: STATE_MATCH
  [use: mcp-playwright]

---

## Phase 4: User Story 2 - Nombre de dispositivo personalizado con slug (P1)

**Goal**: El dispositivo usa el slug del nombre y nombre visible "EV Trip Planner {nombre}"  
**Independent Test**: Crear vehículo y verificar dispositivo con nombre personalizado

### Implementation

- [x] T006 [P] [US2] Modificar sensor.py device_info para usar vehicle_name de config en lugar de vehicle_id [use: homeassistant-config]
- [x] T007 [US2] Verificar que el slug se genera correctamente desde vehicle_name [use: homeassistant-config]
- [x] T008 [VERIFY:API] Verificar dispositivo:
  1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba
  2. Obtener token de acceso de HA (HA_TOKEN)
  3. Consultar /api/states para encontrar entidades del componente
  4. Verificar que el device_info usa vehicle_name para el nombre y vehicle_id (slug) para identifier
  5. SI TODO OK: Emitir SIGNAL: STATE_MATCH
  [use: homeassistant-ops skill / pytest]

---

## Phase 5: User Story 3 - Incluir assist_satellite en selector de notificaciones (P2)

**Goal**: Los dispositivos assist_satellite aparecen en el selector de notificaciones  
**Independent Test**: En config flow, verificar que aparecen entidades assist_satellite

### Implementation

- [x] T009 [P] [US3] Modificar config_flow.py STEP_NOTIFICATIONS_SCHEMA para incluir domain=["notify", "assist_satellite"] [use: homeassistant-config]
- [x] T010 [VERIFY:BROWSER] Verificar selector de notificaciones: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Navegar a HA (hacer login si es necesario) 3. Ir a Integraciones > Añadir > EV Trip Planner 4. Avanzar hasta el paso de notificaciones 5. Verificar que dispositivos assist_satellite aparecen en el dropdown 6. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright]

---

## Phase 6: User Story 4 - Eliminación automática del panel (P1)

**Goal**: Al eliminar vehículo, el panel se elimina automáticamente  
**Independent Test**: Eliminar vehículo y verificar que panel ya no existe

### Implementation

- [x] T011 [US4] Verificar que async_unload_entry llama correctamente a async_unregister_panel [use: homeassistant-config]
- [ ] T012 [VERIFY:BROWSER] Verificar eliminación de panel: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Crear un vehículo de prueba si no existe 3. Verificar que el panel aparece en el sidebar 4. Eliminar el vehículo desde Integraciones 5. Verificar que el panel ya no aparece en el sidebar 6. Verificar que la URL del panel devuelve error 404 7. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright]

---

## Phase 7: User Story 5 - Actualización automática de sensores (P2)

**Goal**: Panel refleja sensores actualizados sin intervención manual  
**Independent Test**: Cambiar sensores en opciones y verificar que panel muestra nuevos valores

### Implementation

- [ ] T013 [US5] El panel ya obtiene datos de hass.states en tiempo real - no se necesita cambio [use: homeassistant-config]
- [ ] T014 [VERIFY:BROWSER] Verificar actualización de sensores: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Crear un vehículo si no existe 3. Acceder al panel y notar los valores de sensores actuales 4. Cambiar sensores en opciones de la integración 5. Recargar el panel 6. Verificar que los valores se actualizaron 7. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright]

---

## Phase 8: User Story 6 - Panel muestra todos los sensores del vehículo (P1)

**Goal**: Panel lista todos los sensores relevantes del vehículo  
**Independent Test**: Acceder al panel y verificar que se muestran todos los sensores

### Implementation

- [ ] T015 [P] [US6] Expandir panel.js _getVehicleStates() para incluir TODOS los sensores del vehículo [use: homeassistant-config]
- [ ] T016 [US6] Mejorar la UI de sensores en panel.js para mostrar todos los valores legibles [use: homeassistant-dashboard-designer]
- [ ] T017 [VERIFY:BROWSER] Verificar sensores en panel: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Crear vehículo si no existe 3. Acceder al panel 4. Verificar que se muestran sensores: SOC, Range, Charging, kwh_today, hours_today, next_trip, etc. 5. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright]

---

## Phase 9: User Story 7 - Panel muestra viajes con UI legible (P1)

**Goal**: Viajes mostrados en formato legible para humanos  
**Independent Test**: Verificar que viajes aparecen con formato legible

### Implementation

- [ ] T018 [P] [US7] Agregar en panel.js función para obtener lista de viajes via hass.connection.call_service [use: homeassistant-ops]
- [ ] T019 [US7] Crear UI de lista de viajes en panel.js con formato legible [use: homeassistant-dashboard-designer]
- [ ] T020 [US7] Manejar caso "no hay viajes" con mensaje apropiado [use: homeassistant-config]
- [ ] T021 [VERIFY:BROWSER] Verificar viajes en panel: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Crear vehículo si no existe 3. Crear algunos viajes de prueba usando servicios HA 4. Acceder al panel 5. Verificar que los viajes aparecen en formato legible (ej: "Lunes 08:00 - Trabajo - 25km") 6. Si no hay viajes, verificar mensaje "No hay viajes programados" 7. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright]

---

## Phase 10: User Story 8 - Panel incluye operaciones CRUD de viajes (P1)

**Goal**: Botones y formularios para crear, editar, eliminar, pausar/reanudar viajes  
**Independent Test**: Realizar operación CRUD desde el panel y verificar cambios

### Implementation

- [ ] T022 [P] [US8] Agregar formulario de creación de viaje en panel.js [use: homeassistant-dashboard-designer]
- [ ] T023 [P] [US8] Agregar botones de edición y eliminación en cada viaje [use: homeassistant-dashboard-designer]
- [ ] T024 [P] [US8] Integrar llamadas a servicios HA: trip_create, trip_update, delete_trip [use: homeassistant-ops]
- [ ] T025 [US8] Agregar botones de pausar/reanudar para viajes recurrentes [use: homeassistant-dashboard-designer]
- [ ] T026 [US8] Agregar botones de completar/cancelar para viajes puntuales [use: homeassistant-dashboard-designer]
- [ ] T027 [VERIFY:BROWSER] CRUD - Crear viaje: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Acceder al panel del vehículo 3. Hacer clic en "Agregar Viaje" 4. Llenar formulario y enviar 5. Verificar que el viaje aparece en la lista 6. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright]

- [ ] T028 [VERIFY:BROWSER] CRUD - Editar viaje: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Seleccionar un viaje existente 3. Hacer clic en editar 4. Modificar datos y guardar 5. Verificar cambios reflejados 6. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright]

- [ ] T029 [VERIFY:BROWSER] CRUD - Eliminar viaje: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Seleccionar un viaje existente 3. Hacer clic en eliminar 4. Confirmar eliminación 5. Verificar que el viaje ya no aparece 6. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright]

---

## Phase 11: User Story 9 - UI del panel ordenada y bonita (P2)

**Goal**: Diseño limpio con secciones claras y botones visibles  
**Independent Test**: Verificación visual del diseño

### Implementation

- [ ] T030 [P] [US9] Aplicar estilos CSS consistentes en panel.css [use: homeassistant-dashboard-designer]
- [ ] T031 [P] [US9] Organizar secciones con headers claros y espaciado adecuado [use: homeassistant-dashboard-designer]
- [ ] T032 [US9] Agrupar botones de acciones lógicamente [use: homeassistant-dashboard-designer]
- [ ] T033 [VERIFY:BROWSER] Verificar diseño: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Acceder al panel 3. Tomar snapshot de la página 4. Verificar visualmente diseño limpio y profesional 5. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright]

---

## Phase Final: Polish & Cross-Cutting

- [ ] T034 Revisar y corregir cualquier error de JavaScript en panel.js [use: mcp-shell]
- [ ] T035 [VERIFY:BROWSER] Verificar consola: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Abrir panel en navegador 3. Revisar consola del navegador (F12) 4. Verificar que no hay errores JavaScript 5. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright]

- [ ] T036 [VERIFY:API] Verificar entidades: 1. **Desplegar**: Ver sección "Despliegue para Verificaciones" arriba 2. Obtener token de acceso (HA_TOKEN de variables de entorno) 3. Consultar /api/states para verificar sensores del vehículo 4. Verificar que todas las entidades relacionadas existen 5. SI TODO OK: Emitir SIGNAL: STATE_MATCH [use: mcp-playwright o curl]

---

## Resumen

| Métrica | Valor |
|---------|-------|
| Total de tareas | 36 |
| Tareas por User Story | US1:5, US2:3, US3:2, US4:2, USUS5:2, US6:3, US7:4, US8:8, US9:4 |
| Tareas paralelizables | 15 |
| Verificaciones Browser | 11 |
| Verificaciones API | 3 |

### Scope MVP (User Story 1)

Las tareas mínimas para tener un MVP funcional son:
- T002-T005 (US1): Corregir error vehicle_id

### Oportunidades de Ejecución Paralela

- T002 y T003 pueden ejecutarse en paralelo (diferentes secciones de panel.js)
- T006 y T007 pueden ejecutarse en paralelo (diferentes aspectos de device_info)
- T009 puede ejecutarse en paralelo con otras tareas
- T015, T016 pueden ejecutarse en paralelo
- T018, T019, T020 pueden ejecutarse en paralelo
- T022, T023, T024, T025, T026 pueden ejecutarse en paralelo
- T030, T031, T032 pueden ejecutarse en paralelo

### Notas sobre Verificaciones

**Autonomía del agente**: 
- El agente debe ser completamente autónomo en verificaciones
- Si necesita login, debe hacer login automáticamente
- Si necesita crear entidades para probar, debe crearlas
- Si falla, debe revisar logs de HA y consola del navegador
- Debe agregar logs adicionales si no tiene información suficiente

**Credenciales HA**:
- URL: http://localhost:18124 (test-ha)
- Usuario: available in environment
- Password: available in environment
- Token: Obtener de variable de entorno
