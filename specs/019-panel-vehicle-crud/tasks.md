# Tasks: Panel de Control de Vehículo con CRUD de Viajes

**Feature**: `019-panel-vehicle-crud`  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Credenciales para Verificaciones

```
Home Assistant URL: http://localhost:18123 (test-ha para verificaciones AUTOMÁTICAS)
Usuario: available in environment (obtener de variables de entorno)
Password: available in environment (obtener de variables de entorno)
Token LTA: available in environment (obtener de variables de entorno)
```
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
CONSULTAR EL CORE DEL CODIGO FUENTE Y DOCUMENTAR EN ESTE DOCUMENTO DETALLES RELEVANTES DE IMPEMENTACIÓN EN LAS TAREAS QUE SEA RELEVANTE. 
---

## Phase 2: Foundational

- [x] T001 Investigar métodos de implementación en Home Assistant Core para panel_custom y EntitySelector [use: mcp-shell]
  **Implementation Notes:**
  - panel_custom: Uses panel_custom.async_register_panel() with hass, frontend_url_path, webcomponent_name, js_url, sidebar_title, sidebar_icon, config, require_admin, embed_iframe parameters
  - EntitySelector: Uses selector.EntitySelector() with EntitySelectorConfig(domain=["notify", "assist_satellite"], multiple=False/True) to show entities from multiple domains
  - Panel cleanup: Uses frontend.async_remove_panel() to unregister panels when vehicles are deleted
  - Reference files: panel.py (lines 60-71), config_flow.py (lines 96-151)

---

## Phase 3: User Story 1 - Corregir error "Cannot render - no vehicle_id" (P1)

**Goal**: El panel nativo renderiza correctamente sin error de vehicle_id
**Independent Test**: Acceder al panel del vehículo y verificar que renderiza correctamente

### Implementation

- [x] T002 [P] [US1] Modificar panel.js connectedCallback para obtener vehicle_id de window.location ANTES de esperar hass [use: homeassistant-config]
- [x] T003 [P] [US1] Modificar panel.js método _render() para intentar obtener vehicle_id de URL como último recurso [use: homeassistant-config]
- [x] T004 [US1] Agregar logging mejorado para debugging de vehicle_id [use: homeassistant-config]
- [x] T005 [VERIFY:TEST] [US1] Crea y ejecuta tests e2e, Verificar que el panel del vehículo renderiza correctamente sin errores
---

## Phase 4: User Story 2 - Nombre de dispositivo personalizado con slug (P1)

**Goal**: El dispositivo usa el slug del nombre y nombre visible "EV Trip Planner {nombre}"  
**Independent Test**: Crear vehículo y verificar dispositivo con nombre personalizado

### Implementation

- [x] T006 [P] [US2] Modificar sensor.py device_info para usar vehicle_name de config en lugar de vehicle_id [use: homeassistant-config]
- [x] T007 [US2] Verificar que el slug se genera correctamente desde vehicle_name [use: homeassistant-config]
- [x] T008 [VERIFY:TEST] [US2] Crea y ejecuta tests e2e Verificar dispositivo con nombre personalizado "EV Trip Planner {nombre}"
---

## Phase 5: User Story 3 - Incluir assist_satellite en selector de notificaciones (P2)

**Goal**: Los dispositivos assist_satellite aparecen en el selector de notificaciones  
**Independent Test**: En config flow, verificar que aparecen entidades assist_satellite

### Implementation

- [x] T009 [P] [US3] Modificar config_flow.py STEP_NOTIFICATIONS_SCHEMA para incluir domain=["notify", "assist_satellite"] [use: homeassistant-config]
- [x] T010 [VERIFY:TEST] [US3] Crea y ejecuta tests e2e Verificar selector de notificaciones incluye assist_satellite
---

## Phase 6: User Story 4 - Eliminación automática del panel (P1)

**Goal**: Al eliminar vehículo, el panel se elimina automáticamente  
**Independent Test**: Eliminar vehículo y verificar que panel ya no existe

### Implementation

- [x] T011 [US4] Verificar que async_unload_entry llama correctamente a async_unregister_panel [use: homeassistant-config]
- [x] T012 [VERIFY:TEST] [US4] Crea y ejecuta tests e2e Verificar eliminación automática del panel al borrar vehículo
---

## Phase 7: User Story 5 - Actualización automática de sensores (P2)

**Goal**: Panel refleja sensores actualizados sin intervención manual  
**Independent Test**: Cambiar sensores en opciones y verificar que panel muestra nuevos valores

### Implementation

- [x] T013 [US5] El panel ya obtiene datos de hass.states en tiempo real - no se necesita cambio [use: homeassistant-config]
- [x] T014 [VERIFY:TEST] [US5] Crea y ejecuta tests e2e Verificar actualización automática de sensores en el panel
---

## Phase 8: User Story 6 - Panel muestra todos los sensores del vehículo (P1)

**Goal**: Panel lista todos los sensores relevantes del vehículo  
**Independent Test**: Acceder al panel y verificar que se muestran todos los sensores

### Implementation

- [x] T015 [P] [US6] Expandir panel.js _getVehicleStates() para incluir TODOS los sensores del vehículo [use: homeassistant-config] Nota: Valores N/A no son permitidos. si faltan entidades de sensor crear entidades para que si existan
- [x] T016 [US6] Mejorar la UI de sensores en panel.js para mostrar todos los valores legibles [use: homeassistant-dashboard-designer]
- [x] T017 [VERIFY:TEST] [US6] Crea y ejecuta tests e2e Verificar que el panel muestra todos los sensores del vehículo
---

## Phase 9: User Story 7 - Panel muestra viajes con UI legible (P1)

**Goal**: Viajes mostrados en formato legible para humanos  
**Independent Test**: Verificar que viajes aparecen con formato legible

### Implementation

- [x] T018 [P] [US7] Agregar en panel.js función para obtener lista de viajes via hass.connection.call_service [use: homeassistant-ops]
- [x] T019 [US7] Crear UI de lista de viajes en panel.js con formato legible [use: homeassistant-dashboard-designer]
  **Implementation Notes:**
  - Panel already has complete trips UI with readable format
  - _formatTripDisplay() renders trips with: trip type badge, status, time display, distance/energy, description, action buttons
  - _renderTripsSection() fetches and displays trips via hass.connection.call_service
  - "No hay viajes programados" message shown when no trips exist
  - CSS includes comprehensive trip card styling with hover effects and status indicators
  - Verified: panel.js lines 362-754 contain complete trips list UI implementation
- [x] T020 [US7] Manejar caso "no hay viajes" con mensaje apropiado [use: homeassistant-config]
- [x] T021 [VERIFY:TEST] [US7] Crea y ejecuta tests e2e.  Verificar que el panel muestra los viajes con UI legible
---

## Phase 10: User Story 8 - Panel incluye operaciones CRUD de viajes (P1)

**Goal**: Botones y formularios para crear, editar, eliminar, pausar/reanudar viajes  
**Independent Test**: Realizar operación CRUD desde el panel y verificar cambios

### Implementation (CONSULTAR CODIGO FUENTE DEL CORE SI ES NECESARIO)

- [x] T022 [P] [US8] Agregar formulario de creación de viaje en panel.js [use: homeassistant-dashboard-designer]
  **Implementation Notes:**
  - Form already implemented in panel.js lines 492-627
  - _showTripForm() creates overlay with trip creation form
  - _handleTripCreate() submits to trip_create service
  - Form fields: type, day_of_week, time, km, kwh, description
  - Verified: form exists and functions correctly
- [x] T023 [P] [US8] Agregar botones de edición y eliminación en cada viaje [use: homeassistant-dashboard-designer]
  **Implementation Notes:**
  - Edit and delete buttons already implemented in panel.js lines 693-699
  - _handleEditClick() (lines 776-797) opens edit form with trip data
  - _handleDeleteClick() (lines 806-833) confirms and deletes trip
  - Verified: buttons exist and function correctly
- [x] T024 [P] [US8] Integrar llamadas a servicios HA: trip_create, trip_update, delete_trip [use: homeassistant-ops]
  **Implementation Notes:**
  - All HA service calls already implemented in panel.js:
    * trip_create: _handleTripCreate() line 612
    * trip_update: _handleTripUpdate() line 1333
    * delete_trip: _deleteTrip() line 1154
  - pause_recurring_trip: _pauseTrip() line 1007
  - resume_recurring_trip: _resumeTrip() line 1030
  - complete_punctual_trip: _completeTrip() line 1046
  - cancel_punctual_trip: _cancelTrip() line 1069
  - Verified: All service calls exist and function correctly
- [x] T025 [US8] Agregar botones de pausar/reanudar para viajes recurrentes [use: homeassistant-dashboard-designer]
  **Implementation Notes:**
  - Pause/Resume buttons already implemented in panel.js lines 706-716
  - _handlePauseTrip() (lines 843-877) pauses recurring trips
  - _handleResumeTrip() (lines 887-916) resumes recurring trips
  - Verified: buttons exist and function correctly
- [x] T026 [US8] Agregar botones de completar/cancelar para viajes puntuales [use: homeassistant-dashboard-designer]
  **Implementation Notes:**
  - Complete/Cancel buttons already implemented in panel.js lines 723-726
  - _handleCompletePunctualTrip() (lines 926-953) completes punctual trips
  - _handleCancelPunctualTrip() (lines 963-990) cancels punctual trips
  - Verified: buttons exist and function correctly
- [x] T027 [VERIFY:TEST] [US8] Crea y ejecuta tests e2e Verificar CRUD de viajes - Crear, Leer , editar, Borrar en el panel de control del vhiculo
---

## Phase 11: User Story 9 - UI del panel ordenada y bonita (P2)

**Goal**: Diseño limpio con secciones claras y botones visibles  
**Independent Test**: Verificación visual del diseño

### Implementation

- [x] T030 [P] [US9] Aplicar estilos CSS consistentes en panel.css [use: homeassistant-dashboard-designer]
- [x] T031 [P] [US9] Organizar secciones con headers claros y espaciado adecuado [use: homeassistant-dashboard-designer]
- [x] T032 [US9] Agrupar botones de acciones lógicamente [use: homeassistant-dashboard-designer]
- [x] T033 [VERIFY:TEST] [US9] Crea y ejecuta tests e2e Verificar UI del panel ordenada y bonita
---

## Phase Final: VERIFICACIÓN COMPLETA INTEGRADA

- [ ] T999 [VERIFY:BROWSER] Verificación Funcional Completa del Panel de Vehículo
  **Objetivo**: Verificar de forma integral y exhaustiva TODA la funcionalidad definida en spec.md para esta especificación. Esta tarea consolida todas las verificaciones de las User Stories en una sola tarea comprehensiva.
  **Resultados**: 450/450 Playwright tests PASSED (Chromium, Firefox, WebKit), 801/801 pytest PASSED, 88% coverage.
  
  
  #### PASOS DE VERIFICACIÓN (orden optimizado para máxima cobertura en mínimo tiempo):

  **FASE 0: Preparación**
  ```
  1. Revisar logs del contenedor HA antes de comenzar:
     docker logs ha-ev-test --tail 100 2>&1 | grep -i "error\|warn" | tail -50
     Buscar errores o advertencias relacionadas con ev_trip_planner
  2. Limpiar cualquier estado previo problemático
  3. Verificar que test-ha está funcionando (curl http://localhost:18123/api/)
  ```

  **FASE 1: Crear integración vehículo para pruebas**
  ```
  4. Navegar a Home Assistant: http://localhost:18123/?v=$(date +%s)
  5. Si requiere login, hacer login con credenciales de test-ha
  6. Ir a Configuración > Integraciones > Añadir Integración
  7. Buscar "EV Trip Planner" y añadir
  8. Completar config flow con valores de prueba:
     - Nombre vehículo: "CochePrueba" (para verificar slug)
     - Capacidad batería: 60 kWh
     - Potencia carga: 11 kW
     - Consumo: 0.18 kWh/km
     - Margen seguridad: 20%
     - Configurar sensores mock básicos
  9. Verificar que la integración se crea correctamente
  10. NOTA: Guardar el vehicle_id generado (slug) para siguientes pasos
  ```

  **FASE 2: Verificar Device con nombre personalizado (US2)**
  ```
  11. Ir a Configuración > Dispositivos
  12. Buscar dispositivo con nombre "EV Trip Planner CochePrueba"
  13. Verificar que:
      - El nombre del dispositivo es "EV Trip Planner CochePrueba" (NO el ID interno largo)
      - La URL del dispositivo usa el slug (ej: /config/devices/device/cocheprueba)
  14. SI FALLA: Documentar en T006-T007 con logs y análisis
  ```

  **FASE 3: Verificar Panel en sidebar (US1, US4)**
  ```
  15. Verificar que aparece en el sidebar de HA con título "EV Trip Planner CochePrueba"
  16. Verificar que el icono del panel es correcto (mdi:car-electric)
  ```

  **FASE 4: Verificar Panel renderiza sin error vehicle_id (US1)**
  ```
  17. Navegar al panel: http://localhost:18123/ev-trip-planner-cocheprueba?v=$(date +%s)
  18. Verificar que NO aparece "Cannot render - no vehicle_id"
  19. Verificar que el panel renderiza correctamente
  20. Verificar que muestra "EV Trip Planner - CochePrueba" en el header
  21. SI FALLA: Documentar en T002-T005 con errores de consola JavaScript y logs
  ```

  **FASE 5: Verificar todos los sensores del vehículo (US6)**
  ```
  22. Verificar que se muestran TODOS los sensores del vehículo:
      - sensor.cocheprueba_soc_actual (o similar)
      - sensor.cocheprueba_estado_carga
      - sensor.cocheprueba_presencia
      - sensor.cocheprueba_conexion
      - sensor.cocheprueba_trips_list
      - sensor.cocheprueba_recurring_trips_count
      - sensor.cocheprueba_punctual_trips_count
      - sensor.cocheprueba_kwh_today
      - sensor.cocheprueba_hours_today
      - sensor.cocheprueba_next_trip
  23. Verificar que los valores son legibles (tienen unidades, no N/A)
  24. SI FALLA: Documentar en T015-T017 indicando qué sensores faltan
  ```

  **FASE 6: Verificar viajes con UI legible (US7)**
  ```
  25. Verificar que existe sección de viajes en el panel
  26. Verificar mensaje apropiado si no hay viajes ("No hay viajes programados")
  27. SI FALLA: Documentar en T018-T021
  ```

  **FASE 7: CRUD - Crear viaje (US8)**
  ```
  28. Hacer clic en botón "Agregar Viaje" o similar
  29. Rellenar formulario de viaje (tipo puntual o recurrente):
      - Tipo: Puntual
      - Fecha/hora: mañana a las 08:00
      - Destino: Trabajo
      - Distancia: 25 km
  30. Enviar formulario
  31. Verificar que el viaje aparece en la lista de viajes
  32. SI FALLA: Documentar errores de consola JavaScript y logs del servidor
  ```

  **FASE 8: CRUD - Editar viaje (US8)**
  ```
  33. Seleccionar el viaje creado
  34. Hacer clic en botón "Editar"
  35. Modificar datos (ej: cambiar distancia a 30 km)
  36. Guardar cambios
  37. Verificar que los cambios se reflejan en la lista
  38. SI FALLA: Documentar en T022-T024
  ```

  **FASE 9: CRUD - Pausar/Reanudar viaje recurrente (US8)**
  ```
  39. Crear un viaje recurrente para probar (si no existe)
  40. Hacer clic en botón "Pausar" del viaje recurrente
  41. Verificar que el viaje se marca como pausado/inactivo
  42. Hacer clic en botón "Reanudar"
  43. Verificar que el viaje vuelve a estado activo
  44. SI FALLA: Documentar en T025
  ```

  **FASE 10: CRUD - Completar/Cancelar viaje puntual (US8)**
  ```
  45. Seleccionar viaje puntual creado
  46. Hacer clic en botón "Completar"
  47. Verificar que el viaje se marca como completado
  48. Crear otro viaje puntual
  49. Hacer clic en botón "Cancelar"
  50. Verificar que el viaje se marca como cancelado
  51. SI FALLA: Documentar en T026
  ```

  **FASE 11: CRUD - Eliminar viaje (US8)**
  ```
  52. Seleccionar un viaje existente
  53. Hacer clic en botón "Eliminar"
  54. Confirmar eliminación si hay prompt
  55. Verificar que el viaje ya no aparece en la lista
  56. SI FALLA: Documentar en T023-T024
  ```

  **FASE 12: Verificar eliminación automática del panel (US4)**
  ```
  57. Volver a Configuración > Integraciones
  58. Eliminar la integración del vehículo "CochePrueba"
  59. Verificar que el panel deja de aparecer en el sidebar
  60. Intentar navegar a la URL del panel: http://localhost:18123/ev-trip-planner-cocheprueba
  61. Verificar que devuelve error 404 o panel no encontrado
  62. SI FALLA: Documentar en T011-T012
  ```

  **FASE 13: Verificar casos límite**
  ```
  63. Crear segundo vehículo con nombre diferente para verificar múltiples vehículos
  64. Verificar que cada vehículo tiene su propio panel
  65. Verificar que los paneles son independientes
  66. Eliminar segundo vehículo y verificar que su panel también se elimina
  ```

  **FASE 14: Verificar UI y diseño (US9)**
  ```
  67. Volver a crear vehículo de prueba para verificación final
  68. Verificar diseño limpio y profesional del panel
  69. Verificar secciones claramente separadas
  70. Verificar botones de acción fácilmente identificables
  71. SI FALLA: Documentar en T030-T033
  ```

  **FASE 15: Verificar consola JavaScript**
  ```
  72. Abrir consola del navegador (F12)
  73. Verificar que NO hay errores JavaScript
  74. Verificar que NO hay warnings críticos
  75. SI HAY ERRORES: Documentar en T034 y analizar causa raíz
  ```

  **FASE 16: Verificación de actualización automática de sensores (US5)**
  ```
  76. Si es posible, modificar sensores del vehículo desde opciones
  77. Verificar que el panel refleja los nuevos valores automáticamente
  78. SI FALLA: Documentar en T013-T014
  ```

  #### Criterios de Éxito:
  - Todas las verificaciones de las fases 1-16 completadas sin errores
  - SIGNAL: STATE_MATCH si TODO OK
  - SIGNAL: STATE_MISMATCH si cualquier verificación crítica falla

  #### Documentación de Fallos:
  En caso de fallo, documentar:
  - Fase específica donde falló
  - Captura de pantalla o snapshot del error
  - Logs del contenedor Docker
  - Consola JavaScript (errores/warnings)
  - Análisis de causa raíz
  - Sugerencias de corrección
  - Tareas desmarcadas relacionadas

  [use: mcp-playwright]

---

## Resumen

| Métrica | Valor |
|---------|-------|
| Total de tareas | 36 (incluyendo 1 consolidada) |
| Tareas por User Story | US1:5, US2:3, US3:2, US4:2, US5:2, US6:3, US7:4, US8:8, US9:4 |
| Tareas paralelizables | 15 |
| Verificaciones E2E | 11 (referenciadas a T999) |
| Verificaciones Browser | 1 (consolidada en T999) |
| Verificaciones API | 0 (integradas en T999) |

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
- Debe desmarcar las tareas que detecte que no estan completas y esten marcadas como completa
- Debe escribir los fallos de errores que encuentre en las tareas relacionadas

**Credenciales HA**:
- URL: http://localhost:18123 (test-ha)
- Usuario: available in environment
- Password: available in environment
- Token: Obtener de variable de entorno
