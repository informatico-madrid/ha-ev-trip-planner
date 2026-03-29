---
name: selector_modal_no_role
description: Usar clase del contenedor del modal para acotar getByRole cuando el modal no tiene role="dialog"
type: feedback
---

# Patrón: Selectores en modales sin role="dialog"

## Regla

Cuando un modal de Lit Elements NO tiene `role="dialog"`, revisar el código fuente del panel.js para encontrar la clase del contenedor del modal y usarla para acotar el selector:

```typescript
// ❌ INCORRECTO - Asumir que el modal tiene role="dialog"
const button = page.locator('[role="dialog"]').getByRole('button', { name: 'Crear Viaje' });

// ✅ CORRECTO - Usar la clase del overlay del panel.js
const button = page.locator('.trip-form-overlay').getByRole('button', { name: 'Crear Viaje' });
```

## Por qué

Los modales de Lit Elements (como los del EV Trip Planner) usan divs con clases específicas (ej: `.trip-form-overlay`) en lugar de roles semánticos. Playwright no puede encontrarlos con `getByRole('dialog')`.

## Cómo aplicar

1. **Revisar panel.js** para encontrar la estructura del modal:
   ```bash
   grep -n "trip-form-overlay\|trip-form-container" custom_components/*/frontend/panel.js
   ```

2. **Identificar la clase del contenedor** que envuelve el modal completo

3. **Acotar el selector** con esa clase:
   ```typescript
   page.locator('.CLASE_DEL_OVERLAY').getByRole('button', { name: 'Texto del botón' })
   ```

## Ejemplo real

En EV Trip Planner, el modal de creación/edición de viajes tiene esta estructura en panel.js:

```javascript
return html`
  <div class="trip-form-overlay">
    <div class="trip-form-container">
      <form @submit=${this._handleTripCreate}>
        ...
        <button type="submit" class="btn btn-primary">Crear Viaje</button>
      </form>
    </div>
  </div>
`;
```

El selector correcto es:
```typescript
const createButton = page.locator('.trip-form-overlay').getByRole('button', { name: 'Crear Viaje' });
```

## Impacto

Este patrón evita errores de "element(s) not found" cuando se asume que todos los modales tienen `role="dialog"`.

## Archivo de memoria

Este patrón aplica a modales que:
- No tienen `role="dialog"` o `role="alertdialog"`
- Usan clases específicas como `.trip-form-overlay`, `.modal-overlay`, `.dialog-overlay`
- Contienen formularios con botones de submit

**Ubicación:** `custom_components/*/frontend/panel.js` - buscar la clase del contenedor del modal.
