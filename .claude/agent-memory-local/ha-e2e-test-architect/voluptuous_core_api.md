---
name: voluptuous_core_api
description: API completa de voluptuous en Home Assistant - parámetros, constantes y uso correcto
type: reference
---

## Voluptuous en Home Assistant - Documentación Completa

### Versión usada
- **Voluptuous version:** 0.15.2
- **Ubicación:** `/usr/local/lib/python3.14/site-packages/voluptuous/__init__.py`

### Constantes de control de extra keys

```python
vol.PREVENT_EXTRA = 0   # Rechaza keys adicionales (por defecto)
vol.ALLOW_EXTRA = 1     # Permite keys adicionales
vol.REMOVE_EXTRA = 2    # Elimina keys adicionales
```

### Uso en Home Assistant Core

**Archivo:** `/usr/src/homeassistant/homeassistant/helpers/config_validation.py`

#### 1. BASE_ENTITY_SCHEMA (línea 1423)
```python
BASE_ENTITY_SCHEMA = _make_entity_service_schema({}, vol.PREVENT_EXTRA)
```
- Schema base para todos los servicios de entidades
- Usa `PREVENT_EXTRA` - rechaza cualquier key adicional

#### 2. make_entity_service_schema (líneas 1427-1435)
```python
def make_entity_service_schema(
    schema: dict | None, *, extra: int = vol.PREVENT_EXTRA
) -> VolSchemaType:
    """Create an entity service schema."""
    if not schema and extra == vol.PREVENT_EXTRA:
        # Si el schema está vacío y usamos PREVENT_EXTRA,
        # retornamos el schema base para optimizar
        return BASE_ENTITY_SCHEMA
    return _make_entity_service_schema(schema or {}, extra)
```

**Parámetros:**
- `schema`: dict | None - El schema del servicio
- `extra`: int - Control de keys adicionales (PREVENT_EXTRA por defecto)

**Importante:**
- El parámetro `extra` controla si se permiten keys adicionales
- Por defecto es `vol.PREVENT_EXTRA` (0)
- Esto significa que cualquier key no definida en el schema será rechazada

#### 3. PLATFORM_SCHEMA_BASE (línea 1310)
```python
PLATFORM_SCHEMA_BASE = PLATFORM_SCHEMA.extend({}, extra=vol.ALLOW_EXTRA)
```
- Permite keys adicionales para configuraciones de plataforma

### Esquema de Service Calls

**Flujo correcto:**

1. **Backend - Registro del servicio:**
```python
import voluptuous as vol
from homeassistant.core import SupportsResponse

# Schema con SOLO los parámetros reales del servicio
my_service_schema = vol.Schema({
    vol.Required("parameter1"): str,
    vol.Optional("parameter2"): int,
})

# Registro con soporte de respuesta
hass.services.async_register(
    DOMAIN,
    "my_service",
    my_handler,
    schema=my_service_schema,
    supports_response=SupportsResponse.ONLY,  # ← Parámetro de registro, no del schema
)
```

2. **Frontend - Llamada al servicio:**
```javascript
// Llamada con return_response como TERCER parámetro
const response = await this._hass.callService(
    'domain',
    'service',
    { parameter1: 'value', parameter2: 42 },  // ← service_data
    { return_response: true }                   // ← Opciones de llamada
);
```

3. **Core de HA - Procesamiento (core.py:2712-2810):**
```python
async def async_call(
    self,
    domain: str,
    service: str,
    service_data: dict[str, Any] | None = None,  # ← Parámetro 3
    blocking: bool = False,
    context: Context | None = None,
    target: dict[str, Any] | None = None,
    return_response: bool = False,  # ← Parámetro separado, NO en schema
) -> ServiceResponse:
```

### Validaciones en el Core

**Core de HA - core.py (líneas 2768-2780):**

```python
if return_response:
    if not blocking:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="service_should_be_blocking",
            translation_placeholders={
                "return_response": "return_response=True",
                "non_blocking_argument": "blocking=False",
            },
        )
    if handler.supports_response is SupportsResponse.NONE:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="service_does_not_support_response",
            translation_placeholders={
                "return_response": "return_response=True"
            },
        )
elif handler.supports_response is SupportsResponse.ONLY:
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="service_lacks_response_request",
        translation_placeholders={"return_response": "return_response=True"},
    )
```

### Errores Comunes

#### Error 1: `service_lacks_response_request`
**Causa:** Servicio registrado con `SupportsResponse.ONLY` pero llamado sin `return_response: true`

**Solución:**
```javascript
// ❌ INCORRECTO
await this._hass.callService('domain', 'service', { param: value });

// ✅ CORRECTO
await this._hass.callService('domain', 'service', { param: value }, { return_response: true });
```

#### Error 2: `extra keys not allowed @ data['target']['return_response']`
**Causa:** `return_response` incluido en el schema del servicio en lugar de en la llamada

**Solución:**
```python
# ❌ INCORRECTO - return_response en el schema
my_service_schema = vol.Schema({
    vol.Required("vehicle_id"): str,
    vol.Optional("return_response"): bool,  # ← ERROR!
})

# ✅ CORRECTO - solo parámetros reales
my_service_schema = vol.Schema({
    vol.Required("vehicle_id"): str,
})
```

### Uso de vol.Schema en HA

#### Pattern básico:
```python
import voluptuous as vol

# Schema con parámetros requeridos y opcionales
schema = vol.Schema({
    vol.Required("required_param"): str,
    vol.Optional("optional_param"): int,
})
```

#### Pattern con validadores:
```python
schema = vol.Schema({
    vol.Required("entity_id"): vol.All(
        vol.Lower,
        vol.EntitySelector(),
    ),
    vol.Optional("temperature"): vol.All(
        vol.Coerce(float),
        vol.Range(min=0, max=100),
    ),
})
```

#### Pattern con extra control:
```python
# Por defecto usa PREVENT_EXTRA
schema = vol.Schema({...})

# Permite extra keys
schema = vol.Schema({...}, extra=vol.ALLOW_EXTRA)

# Elimina extra keys
schema = vol.Schema({...}, extra=vol.REMOVE_EXTRA)
```

### Referencias

- **HA Core config_validation.py:** `/usr/src/homeassistant/homeassistant/helpers/config_validation.py`
- **HA Core core.py:** `/usr/src/homeassistant/homeassistant/core.py`
- **Voluptuous:** `/usr/local/lib/python3.14/site-packages/voluptuous/__init__.py`

### Resumen

1. `return_response` es un parámetro de la **llamada**, no del **schema**
2. El schema solo debe incluir los parámetros reales del servicio
3. `vol.PREVENT_EXTRA` es el comportamiento por defecto
4. `supports_response=SupportsResponse.ONLY` indica que el servicio devuelve datos
5. El frontend debe usar `{ return_response: true }` en la llamada del servicio
