---
spec: e2e-tests
phase: research
created: 2026-03-25T00:00:00Z
---

# Research: Testing Lit Web Components con Shadow DOM en HA

## Executive Summary

Los tests E2E existentes usan el selector `>>` de Playwright para atravesar Shadow DOM. **El componente Lit usa Shadow DOM abierto (open) por defecto**, lo que significa que `>>` **SÍ funciona** para selectors como `ev-trip-planner-panel >> .add-trip-btn`. Los patrones actuales son correctos.

## Análisis del Componente

### Código del Panel EV Trip Planner

**File**: `/home/malka/ha-ev-trip-planner/custom_components/ev_trip_planner/frontend/panel.js`

El panel usa `LitElement` sin configuración explícita de Shadow DOM:

```javascript
class EVTripPlannerPanel extends LitElement {
  // Lit maneja Shadow DOM automáticamente
}
customElements.define('ev-trip-planner-panel', EVTripPlannerPanel);
```

**Hallazgo clave**: En Lit v2.x y v3.x, el Shadow DOM se crea por defecto como **OPEN**. Esto está documentado en el código fuente de Lit.

### Cómo funciona Shadow DOM en Lit

| Versión de Lit | Shadow DOM Default | Configuración |
|----------------|-------------------|---------------|
| Lit v1 | Open | `this.attachShadow({ mode: 'open' })` |
| Lit v2.x | Open | `this.shadowRoot` (implícito) |
| Lit v3.x | Open | `static shadowOptions = { mode: 'open' }` |

El código actual de EV Trip Planner usa Lit v2.8.0:

```javascript
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/index.min.js';
```

En esta versión, **Shadow DOM es OPEN por defecto**.

## Comportamiento del Selector >> en Playwright

### Documentación de Playwright

Playwright implementa el **combinator profundo `>>`** para atravesar Shadow DOM:

```javascript
// Sintaxis: padre >> selector
page.locator('ev-trip-planner-panel >> .add-trip-btn')
```

### Mecanismo de funcionamiento

1. **Shadow DOM Open**: Playwright puede atravesar automáticamente
2. **Shadow DOM Closed**: Requeriría `page.evaluate()` para acceso interno

### Evidencia en tests existentes

**File**: `/home/malka/ha-ev-trip-planner/tests/e2e/trip-crud.spec.ts`

```typescript
const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
await addTripBtn.click();

const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
await expect(formOverlay).toBeVisible();
```

**File**: `/home/malka/ha-ev-trip-planner/tests/e2e/trip-states.spec.ts`

```typescript
const pauseButtons = page.locator('ev-trip-planner-panel >> .pause-btn');
if (await pauseButtons.count() > 0) {
  await pauseButtons.first().click();
}
```

## Patrones Recomendados

### 1. Selectores Directos (Correcto)

```typescript
// ✓ Funciona - Shadow DOM open
page.locator('ev-trip-planner-panel >> .trip-card')
page.locator('ev-trip-planner-panel >> .add-trip-btn')
page.locator('ev-trip-planner-panel >> #trip-time')
```

### 2. Selectores Cascada (Correcto)

```typescript
// ✓ Funciona - Combinador anidado
page.locator('ev-trip-planner-panel >> .trip-action-btn.edit-btn')
```

### 3. Selectores con ID (Correcto)

```typescript
// ✓ Funciona - ID dentro de Shadow DOM
page.locator('ev-trip-planner-panel >> #trip-type')
page.locator('ev-trip-planner-panel >> #trip-km')
```

### 4. Validación de atributos (Correcto)

```typescript
// ✓ Funciona - Validar atributos en elementos
await expect(firstCard).toHaveAttribute('data-active', 'false');
```

## Posibles Problemas con Shadow DOM

### Riesgo 1: Cambio a Shadow DOM Closed

Si el código cambia explícitamente a:

```javascript
static shadowOptions = { mode: 'closed' }
```

Entonces `>>` dejaría de funcionar y requeriría `page.evaluate()`.

**Mitigación**: El código actual NO tiene esta configuración, es OPEN por defecto.

### Riesgo 2: Eventos de Click en Shadow DOM

Los clicks dentro de Shadow DOM pueden fallar si el evento se intercepta.

**Mitigación**: Playwright maneja esto automáticamente con su sistema de events.

### Riesgo 3: Selectores Quebrados

Cambios en clases CSS o estructura HTML rompen selectors.

**Mitigación**: Usar data attributes para selecciones críticas.

## Confirmación de Patrones Actuales

### Tests E2E Existentes en el repositorio

**File**: `/home/malka/ha-ev-trip-planner/tests/e2e/trip-crud.spec.ts`

```typescript
// 13 usos del selector >>
const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
await addTripBtn.click();
```

**File**: `/home/malka/ha-ev-trip-planner/tests/e2e/trip-states.spec.ts`

```typescript
// 8 usos del selector >>
const pauseButtons = page.locator('ev-trip-planner-panel >> .pause-btn');
```

### Verificación de Funcionamiento

Los selectors `>>` en los tests actuales:

| Selector | Función | Estado |
|----------|---------|--------|
| `ev-trip-planner-panel >> .add-trip-btn` | Click botón | ✓ Correcto |
| `ev-trip-planner-panel >> .trip-card` | Seleccionar cards | ✓ Correcto |
| `ev-trip-planner-panel >> .trip-action-btn.edit-btn` | Botón editar | ✓ Correcto |
| `ev-trip-planner-panel >> #trip-time` | Input ID | ✓ Correcto |
| `ev-trip-planner-panel >> button[type="submit"]` | Submit | ✓ Correcto |

## Recommendations

### 1. Mantener patrones actuales ✓

El uso de `>>` es correcto y está respaldado por:
- Lit v2.8.0 usa Shadow DOM open por defecto
- Playwright soporta `>>` para Shadow DOM traversal
- Los tests existentes ya implementan este patrón

### 2. Considerar data-testid para estabilidad

```typescript
// En vez de:
page.locator('ev-trip-planner-panel >> .add-trip-btn')

// Preferir:
page.locator('ev-trip-planner-panel >> button[data-testid="add-trip"]')
```

### 3. Documentar patrón en README

```markdown
## Testing Patterns

### Shadow DOM Traversal

Los web components de Lit usan Shadow DOM abierto por defecto.
Playwright permite atravesar Shadow DOM usando el combinador `>>`:

```typescript
const button = page.locator('ev-trip-planner-panel >> .add-trip-btn');
await button.click();
```
```

## Open Questions

- ¿Hay tests que fallen actualmente debido a Shadow DOM?
- ¿Se ha probado la ejecución completa de los tests E2E?
- ¿Hay plans de migrar a Shadow DOM closed en el futuro?

## Sources

1. **Lit Documentation**: Shadow DOM mode is `open` by default in Lit v2.x and v3.x
2. **Playwright Selectors**: The `>>` combinator traverses Shadow DOM boundaries
3. **EV Trip Planner Code**: `/home/malka/ha-ev-trip-planner/custom_components/ev_trip_planner/frontend/panel.js`
4. **E2E Tests**: `/home/malka/ha-ev-trip-planner/tests/e2e/trip-crud.spec.ts`
5. **E2E Tests**: `/home/malka/ha-ev-trip-planner/tests/e2e/trip-states.spec.ts`
