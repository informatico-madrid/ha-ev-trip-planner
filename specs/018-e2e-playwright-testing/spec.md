# Feature Specification: Navegación Manual con Playwright para Panel Nativo

**Feature Branch**: `018-e2e-playwright-testing`
**Created**: 2026-03-21
**Status**: Draft
**Input**: User description: "Navegar manualmente con Playwright a HA, crear vehículo, verificar panel nativo"

## Resumen Ejecutivo

El objetivo es navegar manualmente con Playwright browser automation a Home Assistant, crear un vehículo siguiendo el config flow, y verificar que el panel nativo es accesible. El proceso es iterativo: si el panel no es accesible, verificar logs de error, corregir y repetir hasta lograr el panel funcionando.

### Flujo de Trabajo

```
Playwright Browser Automation
    ↓
Navegar a http://$HA_URL:8123/
    ↓
Login con credenciales (malka / Darkpunk666/)
    ↓
Navegar a /config/integrations
    ↓
Agregar EV Trip Planner
    ↓
Configurar vehículo (nombre, entidades, etc.)
    ↓
Verificar panel en sidebar
    ↓
Navegar a /panel/ev-trip-planner-{vehicle-name}
    ↓
¿Panel accesible?
    ├─ Sí → ÉXITO ✓
    └─ No → Verificar logs → Corregir → Repetir
```

## User Scenarios & Testing

### User Story 1 - Crear vehículo mediante config flow con Playwright (Priority: P1)

**Como** desarrollador de EV Trip Planner,
**Quiero** navegar manualmente con Playwright a Home Assistant, loguearme, y crear un vehículo siguiendo el config flow,
**Para** probar que la integración se configura correctamente y crea el panel nativo.

**Why this priority**: Esta es la funcionalidad core - sin crear un vehículo no hay panel que verificar.

**Independent Test**:
- Ejecutar script de Playwright en headless mode
- Navegar a http://$HA_URL:8123/
- Loguearse con credenciales
- Navegar a integraciones
- Agregar EV Trip Planner
- Completar config flow con datos de vehículo
- Verificar que se completa sin errores

**Acceptance Scenarios**:

1. **Given** Home Assistant está accesible en http://$HA_URL:8123/, **When** ejecuto el script de Playwright, **Then** el script navega a la página de login

2. **Given** estoy en la página de login, **When** el script ingresa credenciales (malka / Darkpunk666/) y hace login, **Then** soy redirigido al dashboard de Home Assistant

3. **Given** estoy en el dashboard, **When** el script navega a /config/integrations, **Then** veo la lista de integraciones instaladas

4. **Given** estoy en la página de integraciones, **When** el script hace clic en "Integrar integración" y selecciono EV Trip Planner, **Then** aparece el formulario de configuración del vehículo

5. **Given** el formulario de configuración está visible, **When** el script llena los campos (nombre del vehículo, entidades de batería, carga, etc.) y hace clic en "Enviar", **Then** el vehículo se crea y aparece en la lista de integraciones

---

### User Story 2 - Verificar panel nativo accesible con Playwright (Priority: P1)

**Como** desarrollador,
**Quiero** navegar manualmente con Playwright al panel nativo del vehículo creado,
**Para** verificar que el panel aparece en el sidebar y es accesible.

**Why this priority**: Sin panel accesible, la funcionalidad no está completa.

**Independent Test**:
- Ejecutar script de Playwright
- Verificar que aparece un nuevo panel en el sidebar de HA
- Navegar al panel del vehículo
- Verificar que el panel carga y muestra información del vehículo
- Si no carga, verificar logs de error

**Acceptance Scenarios**:

1. **Given** el vehículo se creó correctamente, **When** el script verifica el sidebar, **Then** encuentra un nuevo panel con el nombre del vehículo

2. **Given** el panel está en el sidebar, **When** el script navega al panel, **Then** el panel se abre y muestra información del vehículo

3. **Given** el panel no carga, **When** el script verifica los logs, **Then** puede ver el error específico y reportarlo

---

### User Story 3 - Debugging y corrección iterativa (Priority: P2)

**Como** desarrollador,
**Quiero** verificar logs de error cuando el panel no es accesible, corregir el problema y reintentar,
**Para** iterar hasta lograr el panel funcionando correctamente.

**Why this priority**: El desarrollo de esta funcionalidad requiere múltiples iteraciones de prueba-corrección.

**Independent Test**:
- Ejecutar script de Playwright
- Si el panel no es accesible, verificar logs de HA y errores del navegador
- Corregir el problema en el código
- Reintentar desde el paso 1

**Acceptance Scenarios**:

1. **Given** el panel no es accesible, **When** el script verifica los logs de Home Assistant, **Then** puede ver el error específico (ej: panel no registrado, error de JavaScript, etc.)

2. **Given** identifico el error, **When** corrijo el código, **Then** puedo reintentar el flujo desde el inicio

3. **Given** el panel ahora es accesible, **When** el script navega a él, **Then** se muestra correctamente sin errores

---

### Edge Cases

- **Qué pasa cuando HA no está accesible**: El navegador reporta error de conexión
- **Qué pasa cuando el login falla**: El navegador muestra página de login nuevamente
- **Qué pasa cuando EV Trip Planner no aparece en integraciones**: Verificar si la integración está instalada correctamente
- **Qué pasa cuando el config flow falla**: Verificar logs de HA para ver el error
- **Qué pasa cuando el panel no aparece en sidebar**: Verificar si se registró correctamente, revisar logs
- **Qué pasa con nombres de vehículos con caracteres especiales**: El nombre del panel debe ser sanitizado correctamente
- **Qué pasa si ya existe un vehículo con el mismo nombre**: El config flow debe manejar el error de duplicado

## Requirements

### Functional Requirements

- **FR-001**: El sistema DEBE permitir navegar con Playwright a http://$HA_URL:8123/
- **FR-002**: El sistema DEBE permitir loguearse en Home Assistant con credenciales de usuario (malka / Darkpunk666/)
- **FR-003**: El sistema DEBE permitir navegar a /config/integrations
- **FR-004**: El sistema DEBE permitir agregar EV Trip Planner desde la lista de integraciones
- **FR-005**: El sistema DEBE permitir completar el config flow con datos de vehículo (nombre, entidades, etc.)
- **FR-006**: El sistema DEBE permitir verificar que aparece un panel en el sidebar después de crear el vehículo
- **FR-007**: El sistema DEBE permitir navegar al panel del vehículo (URL: /panel/ev-trip-planner-{vehicle-name})
- **FR-008**: El sistema DEBE permitir ver logs de Home Assistant para debugging
- **FR-009**: El sistema DEBE permitir identificar errores cuando el panel no es accesible
- **FR-010**: El sistema DEBE permitir iterar el proceso hasta lograr el panel accesible

### Key Entities

- **Navegación**: Acciones de Playwright (goto, click, fill, etc.)
- **Config Entry**: Entrada de configuración del vehículo en HA
- **Panel Config**: Configuración del panel nativo (url path, sidebar title, etc.)
- **Vehicle Entity**: Entidad del vehículo que se crea en HA
- **Logs**: Registros de HA para debugging

## Success Criteria

### Measurable Outcomes

- **SC-001**: Se puede navegar al panel del vehículo sin errores
- **SC-002**: El panel muestra información del vehículo correctamente
- **SC-003**: No hay errores en los logs de HA durante la creación del vehículo
- **SC-004**: El panel aparece en el sidebar después de crear el vehículo
- **SC-005**: El proceso se puede repetir hasta lograr el panel accesible (iteración exitosa)

## State Verification Plan

### Existence Check
Cómo probar que el cambio existe en el sistema:
- [ ] Verificar que el panel aparece en el sidebar de Home Assistant
- [ ] Verificar que el panel tiene el nombre correcto del vehículo
- [ ] Verificar que la URL del panel es accesible

### Effect Check
Cómo probar que el cambio funciona:
- [ ] Navegar al panel desde el sidebar
- [ ] Verificar que el panel carga sin errores
- [ ] Verificar que muestra información del vehículo
- [ ] Verificar que no hay errores en logs de HA

### Reality Sensor Result
- STATE_MATCH = panel accesible y funcionando ✓
- STATE_MISMATCH = panel no accesible, tarea NO marcada [x]

## Assumptions

1. Se asume que Home Assistant está ejecutándose en http://$HA_URL:8123/
2. Se asume que se tienen credenciales de acceso válidas (usuario: malka, contraseña: Darkpunk666/)
3. Se asume que Playwright puede usar Chromium en headless mode
4. Se asume que el usuario tiene permisos de administrador en Home Assistant
5. Se asume que EV Trip Planner está instalado en Home Assistant

## Technical Notes

### Herramientas de Navegación

Se usará Playwright para automatizar el navegador:

```javascript
const { chromium } = require('playwright');

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

// Navegar a HA
await page.goto('http://$HA_URL:8123/');

// Login
await page.fill('input[type="email"]', 'malka');
await page.fill('input[type="password"]', 'Darkpunk666/');
await page.click('button[type="submit"]');

// Navegar a integraciones
await page.goto('http://$HA_URL:8123/config/integrations');

// Agregar integración
await page.click('button:has-text("Integrar integración")');
await page.click('a:has-text("EV Trip Planner")');

// Completar config flow
await page.fill('input[name="name"]', 'Test Vehicle');
await page.click('button[type="submit"]');

// Verificar panel
const sidebarPanels = await page.$$('ha-side-nav-menu-item');
// Verificar si hay panel con nombre del vehículo

// Navegar al panel
await page.goto('http://$HA_URL:8123/panel/ev-trip-planner-test-vehicle');
```

### Depuración

- Ver logs de HA: Navegar a `/config/logs` o usar API
- Ver errores del navegador: `console.log` en el navegador
- Capturar screenshots: `page.screenshot()`
- Capturar videos: `video: on` en playwright config

## Clarifications

### Sesión 2026-03-21

- **Q: ¿Qué URL de Home Assistant se usa?**
  → **A: http://$HA_URL:8123/** (URL local del entorno de desarrollo)

- **Q: ¿Cómo se loguea Playwright?**
  → **A: Usando el formulario de login de HA (email: malka, password: Darkpunk666/)**

- **Q: ¿Qué pasa si el panel no se crea?**
  → **A: Verificar logs de HA, identificar error, corregir código, reintentar desde el inicio**

- **Q: ¿El proceso es manual o automatizado?**
  → **A: Automatizado con Playwright (navegador controlado por script en headless mode), pero es un proceso manual guiado, no un test E2E automatizado**

- **Q: ¿Cuántas iteraciones puede haber?**
  → **A: Las necesarias hasta lograr el panel accesible. Cada iteración sigue el mismo flujo: crear vehículo → verificar panel → corregir si falla.**
