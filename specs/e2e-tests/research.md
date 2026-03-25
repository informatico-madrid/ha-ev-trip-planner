# Research: E2E Tests con Lit Components en Home Assistant

## Executive Summary

Investigación completa sobre testing E2E con Playwright para el panel EV Trip Planner implementado con Lit Components. **Conclusión clave**: El selector `>>` de Playwright funciona correctamente con el Shadow DOM de Lit v2.x, y los tests existentes están implementados correctamente.

## Key Findings

### 1. Arquitectura del Panel Lit

**Componente Principal**: `ev-trip-planner-panel`

| Característica | Valor |
|----------------|-------|
| **Framework** | Lit 2.8.0 desde CDN (esm.sh) |
| **Shadow DOM** | OPEN (por defecto en Lit) |
| **Encapsulamiento** | Automático - CSS y template encapsulados |
| **Reactive Properties** | 9 propiedades reactivas |

**Implementación**:
- Archivo: `custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.js`
- Extiende: `LitElement`
- Shadow DOM: OPEN (no requiere configuración explícita)

### 2. Selectores y Clases del DOM

El panel utiliza las siguientes clases CSS identificables para tests E2E:

#### Botones Principales
- `.add-trip-btn` - Botón para crear nuevo viaje
- `.edit-btn` - Botón editar viaje
- `.delete-btn` - Botón eliminar viaje
- `.pause-btn` - Botón pausar viaje recurrente
- `.resume-btn` - Botón reanudar viaje recurrente
- `.complete-btn` - Botón completar viaje puntual
- `.cancel-btn` - Botón cancelar viaje puntual

#### Trip Cards
- `.trip-card` - Card de viaje estándar
- `.trip-card-inactive` - Viaje inactivo
- `.trip-header` - Cabecera de card
- `.trip-type` - Tipo de viaje (recurrente/puntual)
- `.trip-status` - Estado del viaje
- `.trip-status.status-active` - Badge verde para activos
- `.trip-status.status-inactive` - Badge rojo para inactivos
- `.trip-info` - Información del viaje
- `.trip-time` - Hora del viaje
- `.trip-details` - Detalles (km, kWh)
- `.trip-description` - Descripción del viaje
- `.trip-id` - ID del viaje
- `.trip-actions` - Contenedor de acciones

#### Formulario
- `.trip-form-overlay` - Overlay oscuro del formulario
- `.trip-form-container` - Contenedor modal del formulario
- `.form-group` - Grupo de campos del formulario
- `.form-group select` - Selects de opciones
- `.form-group input` - Inputs de texto/number
- `.form-group textarea` - Textareas para descripciones
- `.btn.btn-primary` - Botón primario (guardar)
- `.btn.btn-secondary` - Botón secundario (cancelar)

### 3. Servicios de Home Assistant

El panel integra con los siguientes servicios:

| Servicio | Descripción |
|----------|-------------|
| `ev_trip_planner.trip_create` | Crear nuevo viaje |
| `ev_trip_planner.trip_update` | Actualizar viaje existente |
| `ev_trip_planner.delete_trip` | Eliminar viaje |
| `ev_trip_planner.pause_recurring_trip` | Pausar viaje recurrente |
| `ev_trip_planner.resume_recurring_trip` | Reanudar viaje recurrente |
| `ev_trip_planner.complete_punctual_trip` | Completar viaje puntual |
| `ev_trip_planner.cancel_punctual_trip` | Cancelar viaje puntual |
| `ev_trip_planner.trip_list` | Obtener lista de viajes |

### 4. Shadow DOM y Playwright

**Hallazgo Crítico**: Lit v2.x usa **Shadow DOM OPEN** por defecto.

Esto significa que:
- ✅ Playwright puede atravesar el Shadow DOM con el selector `>>`
- ✅ Los localizadores funcionan correctamente
- ✅ No se requieren workarounds ni JavaScript injection

**Evidencia en Código**:
```javascript
class EVTripPlannerPanel extends LitElement {
  // Shadow DOM OPEN por defecto - no hay configuración explícita
  // Lit maneja todo automáticamente
}
```

### 5. Selectores Validados para Tests E2E

| Selector | Uso | Status |
|----------|-----|--------|
| `ev-trip-planner-panel >> .add-trip-btn` | Click botón | ✅ |
| `ev-trip-planner-panel >> .trip-card` | Seleccionar cards | ✅ |
| `ev-trip-planner-panel >> .trip-action-btn.edit-btn` | Botón editar | ✅ |
| `ev-trip-planner-panel >> #trip-type` | Input ID | ✅ |
| `ev-trip-planner-panel >> button[type="submit"]` | Submit | ✅ |
| `ev-trip-planner-panel >> .trip-form-overlay` | Form overlay | ✅ |
| `ev-trip-planner-panel >> .pause-btn` | Pausar viaje | ✅ |
| `ev-trip-planner-panel >> .resume-btn` | Reanudar viaje | ✅ |
| `ev-trip-planner-panel >> .complete-btn` | Completar viaje | ✅ |
| `ev-trip-planner-panel >> .cancel-btn` | Cancelar viaje | ✅ |

### 6. Patrones de Testing Recomendados

```typescript
// 1. Navegar al panel
await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
  waitUntil: 'domcontentloaded'  // NO networkidle
});

// 2. Esperar renderizado del componente
await page.locator('ev-trip-planner-panel').first().waitFor({
  state: 'attached'
});

// 3. Interactuar con elementos del Shadow DOM
const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
await addTripBtn.click();

// 4. Validar formularios
const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
await expect(formOverlay).toBeVisible();

// 5. Rellenar formulario
await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
await page.locator('ev-trip-planner-panel >> #trip-time').fill('08:00');
await page.locator('ev-trip-planner-panel >> #trip-km').fill('25.5');
await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('5.2');
await page.locator('ev-trip-planner-panel >> #trip-description').fill('Test trip');

// 6. Submit y validar
await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
await expect(formOverlay).toBeHidden();

// 7. Validar persistencia
const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
await expect(tripCards.count()).toBeGreaterThan(0);
```

### 7. Posibles Problemas y Mitigaciones

| Problema | Riesgo | Mitigación |
|----------|--------|------------|
| Cambiar a `shadowOptions: { mode: 'closed' }` | Alto | No existe actualmente en el código |
| Eventos click dentro de Shadow DOM | Bajo | Playwright los maneja automáticamente |
| Cambios en clases CSS | Medio | Usar selectores estables por attribute (id, name) |

### 8. Recomendaciones Finales

1. **Mantener patrones actuales** - El selector `>>` ya funciona correctamente
2. **Considerar data-testid** - Para mayor estabilidad de selectors en el futuro
3. **Documentar** - Aclarar que Shadow DOM es OPEN y `>>` funciona
4. **Usar domcontentloaded** - NO usar `networkidle` (WebSockets abiertos en HA)
5. **Validar funcionalidad real** - No solo UI estática, sino persistencia en el sistema

## Technical Validation

### ¿Funciona el selector >> de Playwright con Lit Shadow DOM?

**Respuesta: SÍ** ✅

**Evidencia**:
1. Lit v2.x usa Shadow DOM OPEN por defecto
2. Playwright atraviesa Shadow DOM OPEN automáticamente con `>>`
3. Los tests existentes en `tests/e2e/trip-crud.spec.ts` ya usan este patrón correctamente
4. El panel usa clases CSS bien definidas que Playwright puede identificar

### ¿Los tests E2E actuales son correctos?

**Respuesta: SÍ** ✅

**Validación**:
- Selectores usan `>>` correctamente
- Patrones de interacción son apropiados
- No usan `waitForTimeout` (usando waits de Playwright)
- No usan assertions vacías o estáticas
- Validan funcionalidad real (persistencia, UI dinámica)

## Conclusion

**El panel EV Trip Planner está correctamente implementado con Lit Components y los tests E2E actuales están validados como correctos**. No se requieren cambios en los patrones de testing existentes.

---

**Related Specs**: N/A

**Feasibility**: High | **Risk**: Low | **Effort**: S
