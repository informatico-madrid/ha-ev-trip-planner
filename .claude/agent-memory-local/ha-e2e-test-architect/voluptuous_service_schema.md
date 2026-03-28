---
name: voluptuous_service_schema
description: Reglas de voluptuous para schemas de servicios en Home Assistant
type: feedback
---

## Regla: `return_response` NO debe estar en el schema del servicio

**Regla:** El parámetro `return_response` es un parámetro de la **llamada** del servicio, NO un parámetro del schema del servicio. Nunca debe incluirse en `vol.Schema()` del backend.

**Error común:**
```python
# ❌ INCORRECTO - return_response NO pertenece al schema
trip_list_schema = vol.Schema({
    vol.Required("vehicle_id"): str,
    vol.Optional("return_response"): bool,  # ← ERROR!
})
```

**Código correcto:**
```python
# ✅ CORRECTO - Solo los parámetros reales del servicio
trip_list_schema = vol.Schema({
    vol.Required("vehicle_id"): str,
})
```

**Explicación técnica:**

### Voluptuous constants para control de extra keys:
```python
vol.PREVENT_EXTRA = 0  # Por defecto - rechaza keys adicionales
vol.ALLOW_EXTRA = 1    # Permite keys adicionales
vol.REMOVE_EXTRA = 2   # Elimina keys adicionales
```

### En HA Core (`config_validation.py`):
```python
# Línea 1423 - BASE_ENTITY_SCHEMA usa PREVENT_EXTRA
BASE_ENTITY_SCHEMA = _make_entity_service_schema({}, vol.PREVENT_EXTRA)

# Línea 1427 - make_entity_service_schema por defecto usa PREVENT_EXTRA
def make_entity_service_schema(
    schema: dict | None, *, extra: int = vol.PREVENT_EXTRA
) -> VolSchemaType:
```

### Flujo de llamada del servicio:

1. **Backend (Python):** Define schema con parámetros reales del servicio
2. **Frontend (JS):** Llama con `{ return_response: true }` como tercer parámetro
3. **Core de HA:** Separa `return_response` del schema y lo procesa como parámetro de control

### Ejemplo completo:

**Backend (`__init__.py`):**
```python
from homeassistant.core import SupportsResponse
import voluptuous as vol

# Schema con solo parámetros reales
trip_list_schema = vol.Schema({
    vol.Required("vehicle_id"): str,
})

# Registro con soporte de respuesta
hass.services.async_register(
    DOMAIN,
    "trip_list",
    handle_trip_list,
    schema=trip_list_schema,
    supports_response=SupportsResponse.ONLY,  # ← Indica que el servicio devuelve datos
)
```

**Frontend (`panel.js`):**
```javascript
// Llamada con return_response como tercer parámetro
const response = await this._hass.callService(
    'ev_trip_planner',
    'trip_list',
    { vehicle_id: this._vehicleId },
    { return_response: true }  // ← Parámetro de la llamada, NO del schema
);
```

**Core de HA (`core.py`):**
```python
async def async_call(
    self,
    domain: str,
    service: str,
    service_data: dict[str, Any] | None = None,
    blocking: bool = False,
    context: Context | None = None,
    target: dict[str, Any] | None = None,
    return_response: bool = False,  # ← Parámetro separado del schema
) -> ServiceResponse:
```

**Validación del core:**
```python
# Si el servicio está registrado con SupportsResponse.ONLY
if handler.supports_response is SupportsResponse.ONLY:
    if not return_response:
        raise ServiceValidationError(
            translation_key="service_lacks_response_request",
            translation_placeholders={"return_response": "return_response=True"}
        )
```

**Por qué ocurre este error:**
- Los desarrolladores confunden el schema del servicio con los parámetros de llamada
- `return_response` es un mecanismo de control del framework, no un dato del servicio
- El schema debe definir SOLO los parámetros de datos que el servicio acepta

**Cómo verificar:**
1. Si recibes `extra keys not allowed @ data['target']['return_response']`
2. Revisa tu schema - si tiene `return_response`, elimínalo
3. El servicio debe estar registrado con `supports_response=SupportsResponse.ONLY`
4. El frontend debe llamar con `{ return_response: true }`

**Referencias:**
- HA Core: `/usr/src/homeassistant/homeassistant/helpers/config_validation.py` líneas 1423-1435
- HA Core: `/usr/src/homeassistant/homeassistant/core.py` línea 2712-2810
- Voluptuous: `vol.PREVENT_EXTRA`, `vol.ALLOW_EXTRA`, `vol.REMOVE_EXTRA`
