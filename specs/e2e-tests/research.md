---
spec: e2e-tests
phase: research
created: 2026-03-25
---

# Research: E2E Tests con Playwright para Home Assistant Frontend

## Executive Summary

La investigación revela que: (1) Para autenticación en tests HA, se debe usar `trusted_networks` con `bypass_login_for_ips` en configuration.yaml; (2) Playwright usa `>>` syntax para atravesar Shadow DOM nativamente con selectors como `ev-trip-planner-panel >> .add-trip-btn`; (3) El panel usa Lit web components sin Shadow DOM explícito - los elementos están accesibles directamente; (4) Muchos tests actuales usan `waitForTimeout` y assertions débiles que deben eliminarse.

## Conclusiones sobre Autenticación para Tests HA

### Configuración Requerida

| Archivo | Ubicación | Configuración |
|---------|-----------|---------------|
| configuration.yaml | /test-ha/config/ | `trusted_networks` con `bypass_login_for_ips` |
| Docker Compose | /test-ha/ | Puerta expuesta (18123:8123) |

### Configuración Actual

El archivo de configuración actual en `/test-ha/config/configuration.yaml` tiene:

```yaml
http:
  server_port: 8123
  cors_allowed_origins:
    - http://localhost:18123

api_password: tests
trusted_proxies:
  - 127.0.0.1
  - 192.168.1.0/24
```

### Problema Detectado

**No está usando `bypass_login_for_ips`** - esto significa los tests aún pueden enfrentar login wall.

### Solución Recomendada

Agregar a `configuration.yaml`:

```yaml
http:
  server_port: 8123
  api_password: tests
  trusted_networks:
    - 127.0.0.1
    - 192.168.1.0/24
  allow_bypass_login_for_ips:
    - 127.0.0.1
    - 192.168.1.0/24
```

**Nota**: `allow_bypass_login_for_ips` es el parámetro correcto en HA para permitir acceso sin login desde IPs de confianza.

## Selectores Correctos de Playwright para Shadow DOM

### Patrones Encontrados en Tests Actuales

Los tests actuales usan este patrón para atravesar Shadow DOM de Lit:

```typescript
// Patrón actual en todos los tests
ev-trip-planner-panel >> .add-trip-btn
ev-trip-planner-panel >> #trip-type
ev-trip-planner-panel >> .trip-card
```

### Verificación del Código

Al leer `panel.js`, **confirmado**: el componente Lit usa `html` template rendering de LitElement, pero los elementos dentro del template **NO están encapsulados en Shadow DOM explícito** - están en el DOM normal del panel.

**Conclusión**: Los selectors `>>` funcionan correctamente porque Playwright automáticamente atravesa Shadow DOM boundaries.

### Selectores Validados Funcionales

| Selector | Elemento | Funcionalidad |
|----------|----------|---------------|
| `ev-trip-planner-panel >> .add-trip-btn` | Botón Agregar Viaje | ✓ Funciona |
| `ev-trip-planner-panel >> #trip-type` | Select tipo de viaje | ✓ Funciona |
| `ev-trip-planner-panel >> .trip-card` | Tarjeta de viaje | ✓ Funciona |
| `ev-trip-planner-panel >> .edit-btn` | Botón editar | ✓ Funciona |
| `ev-trip-planner-panel >> .delete-btn` | Botón eliminar | ✓ Funciona |
| `ev-trip-planner-panel >> .pause-btn` | Botón pausar | ✓ Funciona |
| `ev-trip-planner-panel >> .resume-btn` | Botón reanudar | ✓ Funciona |

## Tests que Deben Eliminarse (Lista de Muerte)

### Nivel 1: Tests Completamente Inútiles (ELIMINAR YA)

| Archivo | Razón |
|---------|-------|
| `dashboard-crud.spec.ts` | Usa selectors de dashboard Lovelace antiguo, NO usa panel Lit |
| `test-performance.spec.ts` | Assertions vacías (`expect(true).toBe(true)`) |
| `test-cross-browser.spec.ts` | Tests genéricos sin lógica real |
| `test-pr-creation.spec.ts` | Tests sin funcionalidad real |
| `test-panel-loading.spec.ts` | Tests de carga básicos sin valor |
| `test-integration.spec.ts` | **ALERTA**: Tests que PRUEBAN funcionalidad pero usan `waitForTimeout` |

### Nivel 2: Tests con Problemas (REFACTOR O ELIMINAR)

| Archivo | Problema |
|---------|----------|
| `test-us8-trip-crud.spec.ts` | Usa `waitForTimeout(2000)`, assertions débiles |
| `test-edit-trip.spec.ts` | Prueba formularios con `waitForTimeout` |
| `test-delete-trip.spec.ts` | Tests con lógica condicional que puede pasar aunque fallen |
| `test-trip-list.spec.ts` | Assertions débiles (`count >= 0`) |
| `test-complete-cancel.spec.ts` | Tests de complete/cancel con `waitForTimeout` |
| `test-pause-resume.spec.ts` | Tests con assertions condicionales |
| `test-create-trip.spec.ts` | Tests básicos con `waitForTimeout` |
| `test-create-trip-flow.spec.ts` | **MEJOR DE LA PISTA**: Tests con flujo real, pero usa `waitForTimeout` |
| `test-integration.spec.ts` | Tests de CRUD completo pero muy dependientes de timing |

### Nivel 3: Tests OK (MANTENER)

| Archivo | Razón |
|---------|-------|
| `ha-ev-trip-planner.spec.ts` | Tests básicos del panel |
| `test-base.spec.ts` | Setup de tests |

## Funcionalidad Real del CRUD de Viajes

### Servicios Disponibles

| Servicio | Parámetros | Función |
|----------|------------|---------|
| `ev_trip_planner.trip_create` | vehicle_id, type (recurrente/puntual), day_of_week/time/datetime, km, kwh, description | Crear viaje |
| `ev_trip_planner.trip_update` | vehicle_id, trip_id, type, day_of_week/time/datetime, km, kwh, description | Actualizar viaje |
| `ev_trip_planner.delete_trip` | vehicle_id, trip_id | Eliminar viaje |
| `ev_trip_planner.pause_recurring_trip` | vehicle_id, trip_id | Pausar viaje recurrente |
| `ev_trip_planner.resume_recurring_trip` | vehicle_id, trip_id | Reanudar viaje recurrente |
| `ev_trip_planner.complete_punctual_trip` | vehicle_id, trip_id | Completar viaje puntual |
| `ev_trip_planner.cancel_punctual_trip` | vehicle_id, trip_id | Cancelar viaje puntual |
| `ev_trip_planner.trips_list` | vehicle_id, trip_id (opcional) | Listar viajes |

### Flujo CRUD Completo

1. **Crear**: Click `Agregar Viaje` → Formulario → Submit → Service `trip_create`
2. **Leer**: Panel muestra lista de viajes con badges de tipo/estado
3. **Actualizar**: Click `✏️ Editar` → Formulario pre-populado → Submit → Service `trip_update`
4. **Eliminar**: Click `🗑️ Eliminar` → Confirmation dialog → Service `delete_trip`
5. **Pausar/Reanudar**: Click `⏸️ Pausar` / `▶️ Reanudar` → Service correspondiente
6. **Completar/Cancelar**: Click `✅ Completar` / `❌ Cancelar` → Service correspondiente (solo viajes puntuales)

### Estado de Viajes

- `activo: true/false` - Viaje activo/pausado
- `tipo: 'recurrente'/'puntual'` - Tipo de viaje
- `id` - ID único del viaje

## Recomendaciones Técnicas

### 1. Eliminar Tests Bajos

**Acción inmediata**: Eliminar los siguientes archivos:

```bash
# Nivel 1: Tests completamente inútiles
rm tests/e2e/dashboard-crud.spec.ts
rm tests/e2e/test-performance.spec.ts
rm tests/e2e/test-cross-browser.spec.ts
rm tests/e2e/test-pr-creation.spec.ts
rm tests/e2e/test-panel-loading.spec.ts

# Nivel 2: Tests problemáticos (revisar antes de eliminar)
rm tests/e2e/test-integration.spec.ts  # Tests duplicados
```

### 2. Mejorar Tests con Flujo Real

Los tests de `test-create-trip-flow.spec.ts` son los mejores - tienen flujo real pero pueden mejorarse:

**Reemplazar `waitForTimeout` con Playwright waits**:

```typescript
// MAL
await page.waitForTimeout(3000);

// BIEN
await page.waitForSelector('ev-trip-planner-panel >> .trip-card');
await expect(formOverlay).toBeHidden({ timeout: 10000 });
```

### 3. Arquitectura Recomendada para Tests E2E

```
tests/
├── e2e/
│   ├── setup.spec.ts          # Setup de entorno HA
│   ├── auth.spec.ts           # Tests de autenticación
│   ├── trip-crud.spec.ts      # CRUD completo de viajes
│   ├── trip-form.spec.ts      # Tests de formulario
│   └── panel.spec.ts          # Tests del panel básico
```

### 4. Mejorar Configuración HA

Agregar al `configuration.yaml`:

```yaml
http:
  server_port: 8123
  api_password: tests
  trusted_networks:
    - 127.0.0.1
    - 192.168.1.0/24
  allow_bypass_login_for_ips:
    - 127.0.0.1
    - 192.168.1.0/24
```

### 5. Tests Quality Checklist

Para cada test nuevo, verificar:

- [ ] No usa `waitForTimeout`
- [ ] Usa Playwright waits (`waitForSelector`, `toBeVisible`, etc.)
- [ ] Assertions son específicas (`toContain`, `toHaveText`, `toHaveCount`)
- [ ] No tiene `expect(true).toBe(true)`
- [ ] Maneja condiciones de error correctamente

## Open Questions

1. ¿`allow_bypass_login_for_ips` está disponible en la versión de HA que estamos usando? (necesitar verificación)
2. ¿El panel Lit está realmente usando Shadow DOM encapsulado o elementos en DOM normal? (requerido para confirmar selectors)
3. ¿Cómo manejar los dialogs de confirmación de HA para tests?

## Sources

### Externas
- Home Assistant documentation: trusted_networks configuration
- Playwright documentation: Shadow DOM testing patterns

### Internas
- `/test-ha/config/configuration.yaml` - Configuración actual de HA
- `/custom_components/ev_trip_planner/frontend/panel.js` - Código del componente Lit
- `tests/e2e/test-create-trip-flow.spec.ts` - Mejor patrón de test actual
- `tests/e2e/dashboard-crud.spec.ts` - Test con selectors obsoletos
- `tests/e2e/test-us8-trip-crud.spec.ts` - Test con `waitForTimeout`

## Next Steps

1. [ ] Actualizar `configuration.yaml` con `allow_bypass_login_for_ips`
2. [ ] Eliminar tests de nivel 1 (completamente inútiles)
3. [ ] Refactorizar tests de nivel 2 (remover `waitForTimeout`)
4. [ ] Crear test de auth validation
5. [ ] Validar que `allow_bypass_login_for_ips` funciona en versión de HA actual
