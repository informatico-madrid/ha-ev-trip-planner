---
name: response_extraction_fix
description: Corrección para extraer respuesta de servicios con SupportsResponse.ONLY de Home Assistant
type: feedback
---

## Problema Encontrado

Home Assistant con `supports_response=SupportsResponse.ONLY` envuelve la respuesta en `{response: {...}}` en lugar de `{result: {...}}`.

El frontend estaba buscando en `response.result` pero los datos estaban en `response.response`.

## Firma CORRECTA de callService Response

**Caso 1: Servicios sin respuesta o con SupportsResponse.FULL**
```javascript
const response = await this._hass.callService('domain', 'service', data);
// response = { result: {...datos} }
```

**Caso 2: Servicios con SupportsResponse.ONLY**
```javascript
const response = await this._hass.callService('domain', 'service', data, undefined, undefined, true);
// response = { response: {...datos} }
```

## Corrección Aplicada en panel.js

### Antes (INCORRECTO):
```javascript
let tripsData = response;
if (response && response.result) {
  tripsData = response.result;
}
```

### Después (CORRECTO):
```javascript
let tripsData = response;

// Home Assistant services with SupportsResponse.ONLY wrap response in {response: {...}}
if (response && response.response) {
  tripsData = response.response;
  console.log('Extracted from response.response:', JSON.stringify(tripsData, null, 2));
}
// Fallback to response.result for other service types
else if (response && response.result) {
  tripsData = response.result;
  console.log('Extracted from result:', JSON.stringify(tripsData, null, 2));
}
```

## Verificación de Éxito

**Logs del frontend:**
```
[LOG] EV Trip Planner Panel: Extracted from response.response
[LOG] EV Trip Planner Panel: tripsData.recurring_trips: [2 items]
[LOG] EV Trip Planner Panel: retrieved 2 recurring and 0 punctual trips
[LOG] EV Trip Planner Panel: Trips retrieved: 2
```

**DOM renderizado:**
- Viajes con hora, km, kWh, descripción completos
- Botones de editar/eliminar/pausar funcionando

## Lección

**Siempre verificar la estructura del response** cuando se usa `callService` con `returnResponse=true`. Home Assistant puede envolver en `response.response` o `response.result` dependiendo de la configuración del servicio.

## Fuentes de Verdad

- **HA Core:** `/usr/src/homeassistant/homeassistant/core.py` - `supports_response` parameter
- **Frontend Source:** `/mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source/src/types.ts` - ServiceCallResponse interface
