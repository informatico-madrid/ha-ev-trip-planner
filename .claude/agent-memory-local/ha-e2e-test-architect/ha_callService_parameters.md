---
name: ha_callService_parameters
description: Parámetros de callService en Home Assistant frontend y supports_response validation
type: feedback
---

## Regla: callService requiere return_response=true para servicios SupportsResponse.ONLY

**Regla:** Cuando un servicio de Home Assistant está registrado con `supports_response=SupportsResponse.ONLY`, la llamada frontend DEBE incluir `{ return_response: true }` como tercer parámetro en `callService`.

**Error sin esta regla:**
```
Validation error: The action requires responses and must be called with return_response=True
translation_key: 'service_lacks_response_request'
```

**Código del core de HA (core.py:2712-2810):**
```python
async def async_call(
    self,
    domain: str,
    service: str,
    service_data: dict[str, Any] | None = None,
    blocking: bool = False,
    context: Context | None = None,
    target: dict[str, Any] | None = None,
    return_response: bool = False,  # ← PARÁMETRO CRÍTICO
) -> ServiceResponse:
```

**Validación en el core:**
```python
elif handler.supports_response is SupportsResponse.ONLY:
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="service_lacks_response_request",
        translation_placeholders={"return_response": "return_response=True"},
    )
```

**Uso correcto en frontend JavaScript:**
```javascript
// Firma: callService(domain, service, serviceData, options)
// Donde options puede incluir: return_response: true

// ❌ INCORRECTO (causa error):
const response = await this._hass.callService('ev_trip_planner', 'trip_list', {
  vehicle_id: this._vehicleId,
});

// ✅ CORRECTO:
const response = await this._hass.callService('ev_trip_planner', 'trip_list', {
  vehicle_id: this._vehicleId,
}, { return_response: true });
```

**Por qué:** El parámetro `return_response` es necesario cuando:
1. El servicio está registrado con `supports_response=SupportsResponse.ONLY`
2. El servicio está registrado con `supports_response=SupportsResponse.EXPECTED` (opcional)
3. Quieres obtener el valor de retorno del servicio

**Cómo aplicar:**
1. Al registrar un servicio con `supports_response=SupportsResponse.ONLY`, documentar que el frontend DEBE usar `return_response: true`
2. Antes de llamar a `callService`, verificar la configuración del servicio en el backend
3. Si el servicio devuelve datos (no solo ejecuta acción), usar `return_response: true`
4. Incluir comentarios en el código explicando por qué se usa `return_response: true`

**Ejemplo de registro de servicio:**
```python
from homeassistant.core import SupportsResponse

hass.services.async_register(
    DOMAIN,
    "trip_list",
    handle_trip_list,
    schema=trip_list_schema,
    supports_response=SupportsResponse.ONLY,  # ← Requiere return_response: true
)
```

**Ejemplo de llamada frontend:**
```javascript
// VERSION=3.0.2 UNIQUE_LOG_ID=VTP-2026-03-28-RETURN-RESPONSE-FIX
console.log('Calling service with return_response=true (required for SupportsResponse.ONLY services)');
// Investigated HA core: async_call(domain, service, service_data, blocking, context, target, return_response)
// callService wrapper: callService(domain, service, serviceData, options) where options can include return_response
const response = await this._hass.callService('ev_trip_planner', 'trip_list', {
  vehicle_id: this._vehicleId,
}, { return_response: true });
```

**Investigación realizada:**
- Archivo: `/usr/src/homeassistant/homeassistant/core.py`
- Método: `async_call` (líneas 2712-2810)
- Parámetros: domain, service, service_data, blocking, context, target, return_response
- Validación: línea 2768-2780 para `SupportsResponse.ONLY`

**Lección aprendida:** Debes investigar el código del core de Home Assistant para entender los parámetros reales de las funciones, no asumir que la firma del frontend es la misma que la del backend.