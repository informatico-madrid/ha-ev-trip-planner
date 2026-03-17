# Feature Specification: Complete Milestone 3.1 & 3.2 - EMHASS Integration & Vehicle Control

**Feature Branch**: `001-milestone-3-2-complete`  
**Created**: 2026-03-17  
**Status**: ✅ Clarified & Ready for Planning  
**Last Updated**: 2026-03-17 (Clarification Answers Integrated)

## User Scenarios & Testing

### User Story 1 - Configure Vehicle with UX Improvements (Milestone 3.1) (Priority: P1)

**User Journey**: El usuario configura un vehículo nuevo con descripciones claras que explican qué hace cada campo y qué sensor debe seleccionar.

**Why this priority**: Sin mejoras UX, los usuarios configurarán mal el sistema y no entenderán qué están haciendo.

**Independent Test**: Se puede probar completamente configurando un vehículo y verificando que todas las descripciones y helper texts aparecen correctamente.

**Acceptance Scenarios**:

1. **Given** el usuario está añadiendo un nuevo vehículo, **When** llega al campo "SOC Sensor", **Then** ve una descripción clara: "Sensor que indica el % de batería del vehículo (ej: sensor.ovms_soc)"

2. **Given** el usuario está configurando el control de carga, **When** ve la opción "External EMHASS", **Then** ve el texto corregido: "Notificaciones Only - Solo avisar cuando sea necesario"

3. **Given** el usuario está configurando el horizonte de planificación, **When** marca el checkbox, **Then** ve una explicación clara: "Usar sensor de horizonte de planificación de tu optimizador"

4. **Given** el usuario completa la configuración, **When** revisa los campos, **Then** entiende exactamente qué está configurando y por qué

---

### User Story 2 - Configure EMHASS Integration (Milestone 3.2) (Priority: P1)

**User Journey**: El usuario configura la integración con EMHASS, especificando parámetros de planificación y carga diferible con validación adecuada.

**Why this priority**: Es la base de todo el Milestone 3. Sin esta configuración, no se puede publicar ningún viaje como carga diferible.

**Independent Test**: Se puede probar completamente configurando un vehículo con EMHASS, verificando que los parámetros se guardan correctamente y se valida contra capacidades reales.

**Acceptance Scenarios**:

1. **Given** el usuario está configurando EMHASS, **When** introduce manualmente el horizonte de planificación (ej: 7 días), **Then** el sistema acepta el valor y lo guarda correctamente

2. **Given** el usuario tiene un sensor de planificación en EMHASS, **When** lo selecciona, **Then** el sistema lo usa para validar el horizonte (si el sensor dice 3 días, el máximo es 3)

3. **Given** el usuario no tiene sensor de planificación, **When** configura manualmente el horizonte, **Then** el sistema usa el valor manual sin intentar leer sensor

4. **Given** el usuario configura max_deferrable_loads manualmente, **When** el sistema lo guarda, **Then** el usuario es responsable de ajustar su configuración de EMHASS si es necesario

5. **Given** el usuario completa la configuración, **When** el sistema muestra un panel de control, **Then** puede monitorizar las cargas diferibles activas

---

### User Story 3 - Publish Trips as Deferrable Loads (Milestone 3.2) (Priority: P1)

**User Journey**: El sistema convierte automáticamente cada viaje planificado en una carga diferible que EMHASS puede consumir y optimizar.

**Why this priority**: Es el núcleo de la integración. Sin esto, EMHASS no puede optimizar la carga del vehículo.

**Independent Test**: Se puede probar creando un viaje recurrente y verificando que aparece como carga diferible en el panel de control y se publica correctamente.

**Acceptance Scenarios**:

1. **Given** el usuario ha creado un viaje recurrente de 50 km con consumo de 0.15 kWh/km, **When** el sistema calcula la energía necesaria, **Then** publica una carga diferible con 7.5 kWh totales y potencia nominal de 11000 W

2. **Given** el usuario tiene un viaje con deadline a las 22:00, **When** son las 18:00, **Then** el sistema publica `def_end_timestep` con 4 horas de ventana disponible

3. **Given** el usuario añade múltiples viajes, **When** el sistema los procesa, **Then** asigna índices únicos a cada viaje (0, 1, 2, ...) sin conflictos

4. **Given** el usuario elimina un viaje, **When** el sistema detecta el cambio, **Then** actualiza o elimina la carga diferible correspondiente

5. **Given** el usuario tiene un panel de control, **When** revisa las cargas diferibles, **Then** ve todas las configuradas con su estado actual

---

### User Story 4 - Control Physical Charging (Milestone 3.2) (Priority: P2)

**User Journey**: El sistema activa/desactiva físicamente la carga del vehículo basado en la optimización de EMHASS y las condiciones de presencia.

**Why this priority**: Es la capa de control que ejecuta la decisión de carga. Sin esto, la optimización es solo teórica.

**Independent Test**: Se puede probar configurando un control de tipo "switch" y verificando que el sistema enciende/apaga el switch correctamente.

**Acceptance Scenarios**:

1. **Given** el vehículo está en casa y enchufado, **WHEN** EMHASS programa carga, **THEN** el sistema activa el switch de carga

2. **Given** el vehículo no está en casa, **WHEN** EMHASS programa carga, **THEN** el sistema NO activa el switch y envía una notificación

3. **Given** el vehículo no está enchufado, **WHEN** EMHASS programa carga, **THEN** el sistema NO activa el switch y envía una notificación

4. **Given** el sistema está controlando la carga, **WHEN** el usuario desconecta el vehículo, **THEN** el sistema desactiva inmediatamente el switch

---

### User Story 5 - Smart Notifications (Milestone 3.2) (Priority: P3)

**User Journey**: El usuario recibe notificaciones inteligentes cuando hay problemas con la carga o cuando la carga se activa/desactiva.

**Why this priority**: Mejora la experiencia del usuario al mantenerlo informado del estado del sistema.

**Independent Test**: Se puede probar configurando un servicio de notificación y verificando que se reciben mensajes apropiados en situaciones clave.

**Acceptance Scenarios**:

1. **Given** el usuario tiene un viaje urgente programado, **WHEN** el vehículo no está enchufado, **THEN** el usuario recibe una notificación de alerta con detalles del viaje

2. **Given** el sistema activa la carga, **WHEN** la activación es exitosa, **THEN** el usuario recibe una notificación de confirmación

3. **Given** el sistema no puede activar la carga por seguridad, **WHEN** intenta activar, **THEN** el usuario recibe una notificación explicativa

---

### Edge Cases

- **EMHASS API unavailable**: Inform user via notification channel selected in config flow. If EMHASS cannot publish deferrable loads, notify via control panel and notifications that trip has no deferrable load - manual review required.
- **Multiple vehicles sharing same charger**: NOT SUPPORTED - charger dedicated to single vehicle. Future improvement to add multi-vehicle support to TODO
- **Trip deadline in past**: Trip is either Completed or Cancelled, deferrable load no longer sent to EMHASS. Control panel includes History section
- **Malformed EMHASS schedules**: CRITICAL BUG - should never happen. If occurs, log at HA standard level, notify via control panel and notifications
- **Vehicle unplugged during active charging**: Home Assistant automation sends advance warnings (1 hour before, 10 minutes before, at activation time) via notification channel. If user plugs in later, charging starts automatically (EMHASS has it as active deferrable load). If EMHASS published a deferrable load, user plugging in will activate charging automatically. For service-based control, could send action when connection detected.
- **Conflicting trip schedules**: NOT ALLOWED - validation prevents saving trips with conflicts. User warned before saving if trip collides with existing trip. Recurring trips repeat pattern checked
- **max_deferrable_loads exceeds EMHASS capacity**: NOT HANDLED - future improvement. Defer understanding until system fully operational after MVP is working
- **Planning sensor not available**: If sensor needed to save trip, prevent saving and notify user. If sensor needed for activation/other functionality, notify via desktop notification and HA standard recommendations. Log at HA standard level. Note: sensor may have been used previously, may not be needed anymore

## Requirements

### Functional Requirements

#### Milestone 3.1 - UX Improvements

- **FR-3.1-001**: System MUST display clear descriptions for every configuration field in config_flow
- **FR-3.1-002**: System MUST show helper text explaining what each sensor should be
- **FR-3.1-003**: System MUST correct "External EMHASS" label to "Notifications Only"
- **FR-3.1-004**: System MUST clarify checkbox functionality for planning horizon
- **FR-3.1-005**: System MUST NOT reference sensors that don't exist (e.g., emhass_planning_horizon)

#### Milestone 3.2 - EMHASS Integration

- **FR-3.2-001**: System MUST allow users to configure EMHASS integration parameters (planning horizon, max deferrable loads) during vehicle setup
- **FR-3.2-002**: System MUST calculate deferrable load parameters automatically from trip data (kWh needed, charging power, deadline)
- **FR-3.2-003**: System MUST publish each trip as a separate EMHASS deferrable load entity with unique index
- **FR-3.2-004**: System MUST support multiple trips per vehicle with automatic index assignment (0 to max_deferrable_loads-1)
- **FR-3.2-005**: System MUST create/update template sensor entities `sensor.emhass_perfil_diferible_{vehicle_id}` with attributes:
  - `power_profile_watts`: Array de tantos valores como venta de horizonte configurada por el usuario en config flow, por defecto 7,  valores (potencia en Watts por hora)
  - `deferrables_schedule`: Plan detallado con atributos por hora (ej: `p_deferrable0`, `p_deferrable1`)
- **FR-3.2-006**: System MUST support different vehicle control strategies (switch, service, script)
- **FR-3.2-007**: System MUST check presence conditions (home, plugged) before activating charging
- **FR-3.2-008**: System MUST send notifications when charging is necessary but cannot be executed
- **FR-3.2-009**: System MUST update deferrable loads automatically when trips are added, edited, or deleted
- **FR-3.2-010**: System MUST handle edge cases gracefully (missing entities, invalid schedules, API failures)
- **FR-3.2-011**: System MUST support manual max_deferrable_loads input (user is responsible for EMHASS configuration)
- **FR-3.2-012**: System MUST support manual planning horizon input when sensor is not available
- **FR-3.2-013**: System MUST create a Lovelace dashboard automatically when vehicle is configured
- **FR-3.2-014**: System MUST provide shell command examples for user to integrate with their EMHASS configuration (curl to EMHASS API)
- **FR-3.2-015**: System MUST generate trip IDs with format: `rec_{day}_{random}` for recurrent, `pun_{date}_{random}` for punctual
- **FR-3.2-016**: System MUST use template sensors (NOT custom platforms) for deferrable load data
- **FR-3.2-017**: System MUST auto-detect Lovelace availability and use appropriate dashboard complexity

#### **NEW - Trip Lifecycle Management (Clarified)**

- **FR-3.2-018**: System MUST differentiate between trip completion and cancellation for recurring trips
  - **Punctual trips**: Release EMHASS index when completed (trip in past)
  - **Recurring trips**: Reset deferrable load to next cycle in planning horizon
  - **Cancel vs Delete**: Cancel = skip current cycle, Delete = remove trip entirely
- **FR-3.2-019**: System MUST provide clear status messages in control panel
  - **Nominal state**: "No trips scheduled for this period"
  - **Error state**: Descriptive error message explaining what failed
- **FR-3.2-020**: System MUST follow Home Assistant logging standards (DEBUG, INFO, WARNING, ERROR)

### Key Entities

- **Trip**: Represents a planned journey with distance, deadline, recurrence pattern, and energy requirements
  - **Types**: Recurrent (repeats weekly) or Punctual (one-time)
  - **Status**: Pending, Completed, Cancelled (not deleted)
- **Deferrable Load**: EMHASS entity representing a trip with parameters (total hours, power, start/end time windows)
- **Vehicle Control Strategy**: Abstract interface for activating/deactivating charging (switch, service, script)
- **Presence Monitor**: Component that checks if vehicle is at home and plugged in
- **EMHASS Adapter**: Bridge between trip data and EMHASS API
- **Control Panel**: Dashboard for monitoring and managing deferrable loads

## Success Criteria

### Measurable Outcomes

#### Milestone 3.1

- **SC-3.1-001**: Users can understand what each configuration field does (100% clarity score in user testing)
- **SC-3.1-002**: Configuration errors reduced by 50% compared to previous version
- **SC-3.1-003**: Support tickets related to configuration reduced by 60%

#### Milestone 3.2

- **SC-3.2-001**: Users can complete EMHASS configuration in under 3 minutes from start to finish
- **SC-3.2-002**: System correctly publishes all trips as deferrable loads within 60 seconds of trip creation
- **SC-3.2-003**: System supports at least 50 simultaneous deferrable loads per vehicle without errors
- **SC-3.2-004**: 100% of deferrable load parameters are calculated correctly (verified against manual calculation)
- **SC-3.2-005**: Vehicle control activation succeeds within 10 seconds of EMHASS schedule update
- **SC-3.2-006**: Presence check prevents charging activation in 100% of cases when vehicle is not at home
- **SC-3.2-007**: Notification system delivers messages within 5 seconds of trigger event
- **SC-3.2-008**: System handles at least 95% of edge cases without crashing or data loss
- **SC-3.2-009**: Control panel shows all active deferrable loads with real-time status
- **SC-3.2-010**: Users can monitor and manage deferrable loads without editing YAML files

## Assumptions

- EMHASS is installed and running in the user's Home Assistant instance
- User has access to configure EMHASS configuration.yaml
- Vehicle integration (OVMS, Renault, etc.) exposes charging control via switch/service
- Presence sensors (binary_sensor) are available in the user's HA instance
- User has appropriate permissions to call services and read sensors
- Default values (7 days planning horizon, 50 max loads) are appropriate for most use cases
- Planning horizon sensor may or may not exist - system must handle both cases
- User is responsible for configuring `number_of_deferrable_loads` in EMHASS config.json
- Control panel MUST be a Lovelace dashboard (auto-detected availability)
- Trip lifecycle management handles both recurrent and punctual trips differently
- Logging follows HA standards (DEBUG, INFO, WARNING, ERROR)
- Template sensors are the standard method for creating deferrable load entities
- Trip ID format MUST follow: `rec_{day}_{random}` or `pun_{date}_{random}`
- Shell command examples will be provided for user to integrate with their EMHASS setup
- User's EMHASS integration may vary (different locations, different shell command implementations)

## Notes

- This specification includes both Milestone 3.1 (UX improvements) and Milestone 3.2 (EMHASS integration)
- Milestone 3.1 MUST be implemented BEFORE Milestone 3.2 to ensure good UX
- Milestone 2 is considered COMPLETE and does not require changes
- All implementation must follow Home Assistant 2026 best practices (async/await, proper typing)
- Code must be testable with pytest-homeassistant-custom-component library (TDD, coverage requirements in implementation)
- No implementation details (languages, frameworks, APIs) should be included in user-facing documentation
- Planning horizon sensor is OPTIONAL - system must work with manual input if sensor not available
- max_deferrable_loads is MANUAL INPUT - user is responsible for configuring EMHASS `number_of_deferrable_loads` accordingly
- YAML manual configuration is NOT recommended - use control panel instead
- Control panel MUST be created when configuring a vehicle (Lovelace dashboard)
- **NEW**: Trip completion releases EMHASS index for punctual trips; recurring trips reset to next cycle
- **NEW**: Cancel ≠ Delete - Cancel skips current cycle, Delete removes trip entirely
- **NEW**: Logging follows HA standards (DEBUG, INFO, WARNING, ERROR)
- **NEW**: Trip ID format MUST be `{type}_{day_or_date}_{random}` (e.g., `rec_lun_abc123`, `pun_20251119_abc123`)
- **NEW**: Deferrable load sensors MUST be template sensors with attributes: `power_profile_watts` and `deferrables_schedule`
- **NEW**: Shell command examples will be provided for user integration (not hardcoded)
- **NEW**: User's EMHASS integration may vary - system provides examples, not hardcoded implementations
- **NEW**: Config flow steps 3-5 MUST be implemented (EMHASS, Presence, Notifications)
- **NEW**: Tests should be adjusted to match code source when discrepancies exist (code takes precedence)



## Additional Clarifications

### SOC Sensor Validation (RESOLVED)
**Decision**: System validates SOC sensor at vehicle setup time.

**Behavior**:
- **At setup**: User MUST provide valid SOC sensor with correct type and units. If sensor is invalid or missing, vehicle cannot be added.
- **During operation**: If SOC sensor stops working or provides invalid data, notify user via dashboard and notifications (same as other sensor failures).
- **Existing functionality**: Current plugin implementation already handles this validation.

**Rationale**:
- Ensures vehicle setup is valid from the start
- Graceful degradation if sensor fails later
- Leverages existing validation logic

### Planning Horizon Validation (RESOLVED)
**Decision**: User can input any integer value, but system provides guidance.

**Configuration**:
- **Maximum value**: 365 days (annual limit)
- **Recommended value**: 7 days (weekly recurrence)
- **Validation message**: "Máximo: 365 días. Recomendado: 7 días para recurrencia semanal"
- **Input type**: Integer field with range validation (1-365)

**Rationale**:
- Trip patterns can vary (weekly, monthly, yearly)
- User has flexibility but gets guidance
- Prevents unreasonable values (e.g., 1000 days)

### Energy Calculation (RESOLVED)
**Decision**: Two-value consumption system: real-time sensor + manual fallback.

**Configuration**:
- **Real-time consumption sensor**: User selects consumption sensor in config flow
  - Auto-populates fallback field with initial value
  - Updates in real-time as sensor provides new data
  - **Mandatory**: Cannot save vehicle without valid consumption sensor
- **Manual fallback**: Static value in config flow
  - Auto-populated when selecting consumption sensor
  - User can modify manually at any time
  - Used when real-time sensor fails or is unavailable
- **Blocking validation**: Cannot save vehicle without consumption value
  - If both real-time and fallback fail: blocking error with notifications
  - Standard HA logging and error reporting

**Formula**:
- **Base calculation**: `energy_kWh = distance_km * consumption_kWh_per_km`
- **Precision**: 3 decimal places (e.g., 7.500 kWh)
- **Validation**:
  - Distance cannot be negative
  - Consumption cannot be negative
  - If distance = 0: Trip should not be saved
  - If consumption = 0: Consumption sensor may be faulty
- **Approximation**: Formula is approximate - designed to prevent user from running out of charge

**Units**:
- Input: km, kWh/km
- Output: kWh (3 decimal precision)

**Rationale**:
- Two-value system provides robustness
- Real-time sensor for accuracy, fallback for reliability
- Blocking validation ensures vehicle configuration is always valid
- Standard HA error handling for failures

### def_end_timestep Format (RESOLVED)
**Decision**: Keep existing implementation if functional.

**Current State**:
- Internal format: Unix timestamp (or whatever is currently working)
- User-facing format: Standard Spanish format
- **Action**: Do not change existing implementation if it's working

**Rationale**:
- Existing functionality is stable
- No need to change working code
- Focus on EMHASS integration, not trip creation

### Vehicle Control Strategy - Charging Sensor (RESOLVED)
**Decision**: System requires charging status sensor as mandatory configuration.

**Configuration**:
- **Strategy selection**: User selects strategy type (switch, service, script) in config flow
- **Entity selection**: User selects appropriate entity based on strategy
  - **Switch**: User selects `switch` entity for charging control
  - **Service**: User selects service ID for charging control
  - **Script**: User selects script for charging control
- **Charging status**: User MUST configure charging status sensor in config flow
  - **Type**: `binary_sensor.charging` or similar
  - **Mandatory**: Cannot save vehicle configuration without charging sensor
  - **Blocking validation**: Config flow will not allow saving without valid charging sensor
- **Current state**: Manual configuration only (no pre-defined vehicle profiles yet)

**Error Handling**:
- **If charging sensor missing**: Blocking error - cannot save vehicle configuration
  - Notification: "Se requiere sensor de estado de carga para configurar este vehículo"
  - Log: Standard HA logging (ERROR level)
- **If charging control fails**: Retry policy
  - **Switch-based**: No action needed - switch state persists automatically
  - **Service-based**: Detect connection and send charge action
  - **Retry**: Continue retrying until charging window passes (trip starts)
  - **Disconnect/reconnect**: Reset counter - continue charging if switch is active
  - **Notification**: After 3 attempts in 5 minutes, notify user via selected channel

**Rationale**:
- User's vehicle integration must be functional first
- Charging status sensor is mandatory for reliable operation
- Blocking validation ensures proper configuration
- Retry policy continues until trip window expires

### Notification Messages (RESOLVED)
**Decision**: System uses appropriate, descriptive messages for each scenario.

**Message Templates**:
- **Charging activated**: "Carga activada para viaje a {destination}. Energía necesaria: {energy} kWh"
- **Charging failed**: "No se pudo activar la carga tras 3 intentos. Verifica tu integración de vehículo/cargador en Home Assistant."
- **Notification service failed**: "El servicio de notificaciones no está disponible. Verifica tu configuración de notificaciones."
- **Generic errors**: Descriptive message explaining what failed and why

**Rationale**:
- Messages are clear and actionable
- System cannot control notification service failures (user's responsibility)
- Focus on what we can control

### EMHASS API Failure (RESOLVED)
**Decision**: If EMHASS API is unavailable, trip has no deferrable load.

**Behavior**:
- **If EMHASS API unavailable**: System cannot publish deferrable loads to EMHASS
- **Result**: Trip is saved but has no deferrable load in EMHASS
- **Notification**: User is notified via:
  - Control panel: "Este viaje no tiene carga diferible en EMHASS - Revisión manual requerida"
  - Notifications: Alert about missing deferrable load
- **Manual review**: User must manually check EMHASS configuration

**Rationale**:
- Trip data is still saved and managed
- User is informed of the issue
- Manual intervention is the fallback

### Vehicle Plugging In After EMHASS Schedule (RESOLVED)
**Decision**: Charging activates automatically if deferrable load is active.

**Behavior**:
- **Scenario**: EMHASS has already scheduled deferrable load, user plugs in vehicle later
- **Switch-based control**: Switch is already open/active, charging starts automatically
- **Service-based control**: System could send action when connection is detected
- **EMHASS behavior**: EMHASS publishes sensors with energy usage plans, not direct activation
- **Our role**: We create deferrable load sensors; EMHASS activates them based on optimization

**Rationale**:
- EMHASS handles scheduling, we handle sensor creation
- Automatic activation when user plugs in
- Service-based control could add connection detection

### Trip Editing Fields (RESOLVED)
**Decision**: Editing fields are defined in trip service/actions.

**Current State**:
- Trip CRUD operations are defined in service/actions
- Control panel calls these services
- Editable fields are defined in service implementations
- **Action**: No changes needed to editing logic

**Rationale**:
- Existing service/actions define what can be edited
- Control panel leverages existing functionality
- No duplication of logic

### Auto-detection Error Handling (RESOLVED)
**Decision**: Fatal blocking error if config.json cannot be read.

**Behavior**:
- **If config.json is corrupt**: Fatal error, notify user, log error
- **If no read permissions**: Fatal error, notify user, log error
- **If EMHASS not installed**: Fatal error, notify user, log error
- **Action**: Block configuration from completing until resolved

**Rationale**:
- Auto-detection is critical for initial setup
- User cannot proceed without valid EMHASS configuration
- Fatal errors must be blocking

### Index Assignment Strategy (RESOLVED)
**Decision**: Index is used to match trips with deferrable loads.

**Current State**:
- Trip CRUD is already functional
- Index assignment is part of existing implementation
- **Action**: Preserve existing functionality, fix any bugs if discovered
- **Recommendation**: Index should provide:
  - One-to-one mapping: trip_id → emhass_index
  - Counting/tracking capability
  - Easy lookup by trip or by index

**Rationale**:
- Existing implementation is stable
- Don't break working functionality
- Focus on bug fixes if needed

### Testing Approach (RESOLVED)
**Decision**: Standard pytest code coverage with mocks and fixtures.

**Requirements**:
- **Coverage type**: Standard pytest code coverage (lines, branches, statements)
- **Threshold**: 90% minimum coverage for ALL source code
- **Blocking**: 90% coverage is a merge requirement - PR blocked if coverage < 90%
- **Test infrastructure**: Use mocks and fixtures (pytest-homeassistant-custom-component)
- **No infrastructure tests**: Do not test real infrastructure (no concurrency tests, no real HA tests)
- **Focus**: Test code logic, not infrastructure
- **No 50 tests**: Quality over quantity - use effective mocks

**Rationale**:
- 90% coverage ensures high code quality
- Blocking merge requirement enforces testing discipline
- Standard pytest coverage metrics are sufficient
- Mocks provide reliable testing without infrastructure dependencies

### EMHASS Sensor Attributes (RESOLVED)
**Decision**: System creates sensors with exact attributes required by EMHASS config.json.

**Sensor Entity**: `sensor.emhass_deferrable_load_config_{index}`

**Required Attributes**:
1. **total_energy** (float): Energía total en kWh (ej: 7.500)
2. **power** (float): Potencia nominal en W (ej: 3600)
3. **start_timestep** (int): Inicio en timesteps desde ahora (ej: 0 = inmediato)
4. **end_timestep** (int): Fin en timesteps (ej: 168 = 24 horas con timestep de 60s)
5. **is_semi_continuous** (bool): Si es semi-continuo (true) o continuo (false)
6. **minimum_power** (float): Potencia mínima en W (ej: 0)
7. **operating_hours** (int): Horas de operación (ej: 0 = calcular automáticamente)
8. **startup_penalty** (float): Penalización de arranque (ej: 0)
9. **is_single_constant** (bool): Si es carga constante (true) o variable (false)

**Calculation**:
- **total_energy**: `distance_km * consumption_kWh_per_km` (3 decimal precision)
- **power**: User-configured charging power in W (ej: 3600W = 3.6kW)
- **start_timestep**: Calculated from trip deadline and charging duration
- **end_timestep**: Calculated from trip deadline
- **is_semi_continuous**: Based on vehicle charging capability
- **minimum_power**: 0 (can be adjusted per vehicle)
- **operating_hours**: 0 (EMHASS calculates automatically)
- **startup_penalty**: 0 (no penalty for most EVs)
- **is_single_constant**: true (constant power charging)

**EMHASS Integration**:
- System publishes deferrable load parameters via shell command
- Shell command must be configured in `configuration.yaml`
- Parameters are validated against `config.json` constraints
- Index mapping: `trip_id → emhass_index` (0 to max_deferrable_loads-1)

**Rationale**:
- Attributes match EMHASS config.json exactly
- Calculation is approximate but sufficient for EV charging
- System validates against EMHASS capacity constraints
- User-configurable power ensures compatibility

### Input Validation (RESOLVED)
**Decision**: Prevent saving with invalid input, show error message.

**Behavior**:
- **Validation**: System validates input before saving
- **If invalid**: Prevent save, show error message at input field
- **User action**: User must correct the error before saving
- **Error messages**: Descriptive messages explaining what's wrong and how to fix

**Rationale**:
- Prevents invalid data from being saved
- User-friendly validation feedback
- Consistent with HA best practices

### Trip ID Format (RESOLVED)
**Decision**: Trip ID MUST follow format: `{type}_{day_or_date}_{random}`

**Format Examples**:
- Recurrent trips: `rec_lun_abc123`, `rec_mie_def456` (day abbreviation + random)
- Punctual trips: `pun_20251119_abc123` (date + random)

**Rationale**:
- Human-readable trip identification
- Consistent with services.yaml examples
- Tests expect this format
- Code source takes precedence over tests

### Control Panel - Lovelace Dashboard (RESOLVED)
**Decision**: Control panel MUST be a Lovelace dashboard created automatically.

**Implementation**:
- **Simple installation**: Dashboard with markdown cards
- **With Lovelace**: Full dashboard with apexcharts-card for visualization
- **Auto-detection**: System checks if Lovelace is available
- **Dashboard location**: `/lovelace/ev-trip-planner-{vehicle_id}.yaml`

**Rationale**:
- Dashboard is standard HA way to visualize data
- Compatible with all HA installations
- Can be imported automatically during config flow
- Uses existing entities and sensors

### Shell Command Integration (RESOLVED)
**Decision**: System provides shell command examples for user to integrate with their EMHASS configuration.

**Architecture**:
- System creates template sensors with deferrable load data
- User integrates these sensors into their shell command in `configuration.yaml`
- System provides example shell command showing how to use the sensor attributes

**Example from user's HA**:
```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -H "Content-Type: application/json" -X POST -d '{
      "P_deferrable": {{ (state_attr('sensor.emhass_perfil_diferible_ovms_chispitas', 'power_profile_watts') | default([0]*168) + state_attr('sensor.emhass_perfil_diferible_morgan', 'power_profile_watts') | default([0]*168)) | tojson }}
    }' http://192.168.1.100:5000/action/dayahead-optim
```

**Key Points**:
- `power_profile_watts`: Array de 168 valores (potencia en Watts por hora)
- Cada valor corresponde a una ventana de tiempo de 1 hora
- Valores comienzan desde la hora actual o siguiente
- Array puede contener múltiples cargas diferibles (una por vehículo)
- System provides example showing how to insert sensor data into shell command

**Rationale**:
- User's EMHASS integration may vary (different locations, different implementations)
- System cannot assume shell commands are already configured
- System provides examples for user to adapt to their setup
- Template sensors are created by system, shell command is user responsibility
- Example shows how to integrate sensor attributes into curl command

### Config Flow Steps (RESOLVED)
**Decision**: All steps 1-5 MUST be implemented in config flow.

**Steps**:
1. Step 1: Vehicle basic info (name, type, battery)
2. Step 2: SOC sensor, consumption sensor
3. Step 3: EMHASS integration (planning horizon, max loads)
4. Step 4: Presence detection (home sensor, plugged sensor)
5. Step 5: Notifications (notification service, devices)

**Rationale**:
- Complete vehicle setup in single flow
- All required parameters collected upfront
- Consistent with HA config flow best practices
- Creates dashboard automatically after completion

### Testing - Code Precedence (RESOLVED)
**Decision**: When tests and code disagree, code source takes precedence.

**Action**:
- Adjust tests to match code implementation
- Code documentation takes priority over test expectations
- Focus on functional correctness, not test format

**Rationale**:
- Code is the source of truth
- Tests should validate actual behavior
- Easier to update tests than rewrite working code

## Research Notes

### max_deferrable_loads Validation

**Current Status**: MANUAL INPUT CONFIRMED

**Finding**: EMHASS config.json uses `number_of_deferrable_loads` parameter (e.g., value: 2)

**Decision**: User will manually input this value in config_flow. User is responsible for:
1. Setting `number_of_deferrable_loads` in EMHASS config.json
2. Ensuring the value matches the number of deferrable loads they want to manage

**Rationale**:
- No API to read EMHASS config dynamically
- Reading config.json requires file system access which may not be available
- User is already responsible for EMHASS configuration
- Simpler to let user input the value manually

### emhass_planning_horizon Sensor

**Current Status**: MANUAL INPUT CONFIRMED

**Finding**: `sensor.emhass_planning_horizon` does NOT exist in EMHASS

**Decision**: User will manually input planning horizon (1-30 days) in config_flow

**Rationale**:
- No sensor exists in EMHASS
- Planning horizon is configured in EMHASS config.json as `planning_horizon_days`
- User already knows their EMHASS configuration
- Simpler to let user input manually

### Snippet YAML vs Control Panel

**Current Status**: CONTROL PANEL REQUIRED

**Finding**: Manual YAML configuration is problematic (error-prone, not scalable, requires restart)

**Decision**: System MUST create a control panel when configuring a vehicle

**Features**:
- Dashboard card showing active deferrable loads
- Real-time status monitoring
- Ability to activate/deactivate loads from UI
- No YAML editing required

**Recommendation**: Use Home Assistant dashboard with custom cards or create custom component

### Trip Lifecycle Management (NEW)

**Current Status**: CLARIFIED

**Finding**: Two types of trips with different lifecycle behaviors:
- **Punctual trips**: Complete → Release EMHASS index (trip in past)
- **Recurrent trips**: Complete → Reset to next cycle in planning horizon

**Decision**: System must handle:
- **Cancel**: Skip current cycle (keep recurrence)
- **Delete**: Remove trip entirely
- **Complete**: Release index (punctual) or reset (recurrent)

**Rationale**:
- Different behaviors for different trip types
- Cancel ≠ Delete in UX
- Index management depends on trip type

### Logging Standards

**Current Status**: HA STANDARDS CONFIRMED

**Finding**: "Code must be testable" refers to development quality (TDD, coverage)

**Decision**: Logging follows HA standards:
- DEBUG: Development and debugging
- INFO: Important operational events
- WARNING: Conditions requiring attention
- ERROR: Errors affecting functionality

**Rationale**:
- Standard HA logging is sufficient
- No special requirements beyond HA standards
- Test coverage is implementation concern, not spec

---

## ✅ Specification Validation Checklist

- [x] All user stories defined and prioritized (P1, P2, P3)
- [x] All functional requirements specified (FR-3.1-001 to FR-3.2-016)
- [x] Success criteria are measurable and technology-agnostic
- [x] Edge cases identified and documented
- [x] Trip lifecycle clarified (punctual vs recurrent, cancel vs delete)
- [x] Logging requirements specified (HA standards)
- [x] Error states differentiated (nominal vs error)
- [x] Assumptions clearly stated
- [x] Research notes completed for all clarifications
- [x] No implementation details in specification
- [x] Milestone 3.1 included and prioritized before 3.2
- [x] Milestone 2 confirmed as complete
- [x] Control panel requirement specified
- [x] max_deferrable_loads confirmed as manual input
- [x] emhass_planning_horizon confirmed as manual input
- [x] YAML snippet approach rejected in favor of control panel

## 📋 Ready for Next Phase

**Status**: ✅ READY FOR `/speckit.plan`

**Next Step**: Generate implementation plan with tasks for:
1. Milestone 3.1 (UX improvements) - 1-2 days
2. Milestone 3.2 (EMHASS integration) - 11-17 days

**Total Estimated Effort**: 12-19 days

---

## ✅ Final Clarification Answers

### 1. Charging Sensor Failure - Config Flow
**Answer**: ERROR BLOQUEANTE - No permitir avanzar si el sensor de carga no está en funcionamiento. El sensor debe estar operativo para configurar el vehículo.

### 2. Charging Sensor Failure - Trip Management
**Answer**: ERROR BLOQUEANTE - No permitir guardar el viaje si el sensor de carga no está en funcionamiento. Validación crítica antes de guardar.

### 3. Charging Sensor Failure - Runtime
**Answer**: 
- No bloquear - Solo notificar al usuario para que comprueba manualmente
- Loguear como WARNING - De la forma habitual en HA
- Continuar operación - No detener el flujo por falla de sensor

### 4. Shell Command Approach
**Answer**: 
- NO ejecutamos el shell command - EMHASS ya lo tiene instalado el usuario
- Solo damos ejemplo - Proporcionamos variable/ejemplo de shell command que el usuario copia y pega
- Ya estaba claro - Esto no es ambiguo, el usuario configura EMHASS previamente

### 5. Power Profile Watts Meaning
**Answer**: 
- 0W = False/Null - No se está cargando
- Valor positivo = Potencia de carga - Ej: 3600W = cargando a 3.6kW
- Variable del shell command - Para las cargas aplazables en EMHASS

### 6. Testing Scope
**Answer**: 
- Tests típicos de código - Tests unitarios e integración normales
- NO tests absurdos - No testear si un cable soporta 6000W (fuera del alcance)
- Best practices - Seguir mejores prácticas de testing de código

### 7. Manual Input Fallback - Planning Horizon
**Answer**: 
- Usar config de EMHASS - Leer de `/home/malka/emhass/config/config.json`
- Campo en config_flow - Decir al usuario la ruta de su config.json
- Instalación final - El usuario final podrá tenerlo en otro lugar
- Fallback manual - Si no hay sensor, usar valor manual

### 8. Deferrables Schedule Structure
**Answer**: 
- Referencia implementación - Fijarse en la implementación actual en nuestro EMHASS
- Variable del shell command - Es una de las variables del shell command
- No especificar aquí - Verificar en implementación real

### 9. Notification Content Format
**Answer**: 
- Usuario elige canal - Canal/sensor/entidad de notificaciones en config_flow
- Texto creativo - El texto lo pongo yo (implementación)
- Flexible - Adaptarse al canal elegido

### 10. Notification Timing
**Answer**: 
- Cuando sean necesarias - En el momento oportuno según el contexto
- Sin timing específico - No definir horarios fijos

### 11. Shell Command Failure Handling
**Answer**: 
- EMHASS lo maneja - Esto es responsabilidad de EMHASS, no nuestra
- Verificar sensores - Podemos ver si el sensor de EMHASS incluyó las cargas aplazables
- Panel de control - Por cada viaje mostrar:
  - Carga aplazable enviada a EMHASS
  - Sensor de carga aplazable devuelto por EMHASS
- No bloquear - No detener operación por falla de shell command

### 12. Power Profile Calculation Errors
**Answer**: 
- No especificado - No se me ocurre edge case específico
- Dejar al desarrollador - El que implemente se fija si aparece alguno

### 13. Phase Dependency Order
**Answer**: 
- Orden lógico - Dependencias lógicas naturales
- Confío en tu criterio - Tú lo sabrás mejor que yo
- Secuencial donde sea necesario - Implementación ordenada

### 14-16. Performance Requirements
**Answer**: 
- Que fluya normal - Sin requerimientos específicos de performance
- Experiencia fluida - Que la UX sea fluida y responsiva

### 17-19. Logging Requirements
**Answer**: 
- Standard de HA - Seguir el estándar de logging de Home Assistant
- Niveles apropiados - DEBUG, INFO, WARNING, ERROR según contexto

### 20-24. Edge Cases
**Answer**: 
- No se me ocurre ninguno - No tengo edge cases específicos en mente
- Dejar al desarrollador - El que crea las tareas se fija si encuentra alguno
- O al implementar - El que implementa se fija si aparece alguno no previsto

### 25-26. Documentation Requirements
**Answer**: 
- Actualizar toda la documentación - Actualizar documentación actual existente
- Crear nueva documentación - Crear documentación nueva donde sea necesario
- Última parte de tareas - Es la última parte de las tareas
- Muy importante - Es importantísimo hacerlo completo

### 27-37. Additional Items
**Answer**: 
- No especificado - Items sin preguntas específicas
- Dejar a criterio - Decidir durante implementación
- Best practices - Seguir mejores prácticas

---

## 🎯 Key Decisions

### Blocking Validation
- ✅ Charging sensor **must** be functional in config flow
- ✅ Charging sensor **must** be functional when creating/editing trips
- ✅ Runtime failures → **notify only**, log warning, continue

### EMHASS Integration
- ✅ User configures EMHASS shell command (not us)
- ✅ We provide example, user copies/pastes
- ✅ We verify EMHASS sensors include our deferrable loads

### Testing Scope
- ✅ Normal code tests (unit, integration)
- ❌ No infrastructure/physical tests (cable capacity, etc.)

### Documentation
- ✅ Update existing documentation
- ✅ Create new documentation as needed
- ✅ Last phase of implementation

### Logging
- ✅ HA standard logging levels
- ✅ Appropriate for context

---

**Specification completed and validated with clarification answers**  
**Date**: 2026-03-17

