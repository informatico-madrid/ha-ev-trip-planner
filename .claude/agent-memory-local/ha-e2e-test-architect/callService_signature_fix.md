---
name: callService_signature_fix
description: Corrección de la firma de callService - de services.call a callService con parámetros correctos
type: feedback
---

## Problema Encontrado

El código estaba usando `this._hass.services.call` en lugar de `this._hass.callService` con la firma correcta.

## Firma CORRECTA (fuente de verdad)

**Archivo fuente:** `/mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source/src/state/connection-mixin.ts`

**Firma:**
```typescript
callService: async (
  domain,              // 1ro: string
  service,             // 2do: string
  serviceData,         // 3ro: object (opcional)
  target,              // 4to: object (opcional)
  notifyOnError = true, // 5to: boolean (default: true)
  returnResponse = false  // 6to: boolean (default: false)
) => { ... }
```

**También documentado en:** `/mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source/src/types.ts` línea 267-274

## Correcciones Aplicadas

### Antes (INCORRECTO):
```javascript
await this._hass.services.call('ev_trip_planner', 'trip_create', serviceData);
```

### Después (CORRECTO):
```javascript
// Use correct callService signature: (domain, service, serviceData, target, notifyOnError, returnResponse)
await this._hass.callService('ev_trip_planner', 'trip_create', serviceData);
```

## Llamadas Corregidas en panel.js

1. `_handleCreateTrip` - trip_create
2. `_getTripById` - trip_list con returnResponse (6to parámetro)
3. `_handleUpdateTrip` - trip_update
4. `_deleteTrip` - delete_trip
5. `_pauseTrip` - pause_recurring_trip
6. `_resumeTrip` - resume_recurring_trip
7. `_completeTrip` - complete_punctual_trip
8. `_cancelTrip` - cancel_punctual_trip

## Fuentes de Verdad

- **Frontend JS:** `/mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source/src/state/connection-mixin.ts`
- **Type Definition:** `/mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source/src/types.ts`
- **Backend Python:** `/usr/src/homeassistant/homeassistant/core.py` línea 2712-2810

## Lección

**Siempre investigar el código fuente original** antes de asumir la API. Nunca adivinar la firma de los métodos.

## Clon del Repositorio

Repositorio clonado disponible en: `/mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source/`

Usar este clon para investigar el código fuente original sin minificar de Home Assistant frontend.
