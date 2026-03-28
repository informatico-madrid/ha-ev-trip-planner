---
name: voluptuous_investigation_results
description: Resultados de investigación del código de voluptuous en HA core
type: reference
---

## Investigación de Voluptuous en Home Assistant Core

### Fecha de Investigación
2026-03-28

### Archivos Investigados

#### 1. `/usr/src/homeassistant/homeassistant/helpers/config_validation.py`

**Funciones Clave:**

**make_entity_service_schema (líneas 1427-1435):**
```python
def make_entity_service_schema(
    schema: dict | None, *, extra: int = vol.PREVENT_EXTRA
) -> VolSchemaType:
    """Create an entity service schema."""
    if not schema and extra == vol.PREVENT_EXTRA:
        # If the schema is empty and we don't allow extra keys, we can return
        # the base schema and avoid compiling a new schema which is the case
        # for ~50% of services.
        return BASE_ENTITY_SCHEMA
    return _make_entity_service_schema(schema or {}, extra)
```

**Parámetros:**
- `schema`: dict | None - El schema del servicio
- `extra`: int - Control de keys adicionales (PREVENT_EXTRA por defecto)

**BASE_ENTITY_SCHEMA (línea 1423):**
```python
BASE_ENTITY_SCHEMA = _make_entity_service_schema({}, vol.PREVENT_EXTRA)
```

#### 2. `/usr/src/homeassistant/homeassistant/core.py`

**async_call method (líneas 2712-2810):**
```python
async def async_call(
    self,
    domain: str,
    service: str,
    service_data: dict[str, Any] | None = None,
    blocking: bool = False,
    context: Context | None = None,
    target: dict[str, Any] | None = None,
    return_response: bool = False,  # ← PARÁMETRO SEPARADO
) -> ServiceResponse:
```

**Validaciones (líneas 2768-2780):**
```python
if return_response:
    if not blocking:
        raise ServiceValidationError(...)
    if handler.supports_response is SupportsResponse.NONE:
        raise ServiceValidationError(...)
elif handler.supports_response is SupportsResponse.ONLY:
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="service_lacks_response_request",
        translation_placeholders={"return_response": "return_response=True"},
    )
```

### Constantes Voluptuous

```python
vol.PREVENT_EXTRA = 0  # Rechaza keys adicionales (por defecto)
vol.ALLOW_EXTRA = 1    # Permite keys adicionales
vol.REMOVE_EXTRA = 2   # Elimina keys adicionales
```

### Errores Encontrados y Corregidos

#### Error Original
```
No se pudo realizar la acción ev_trip_planner/trip_list.
extra keys not allowed @ data['target']['return_response']. Got True
```

#### Causa
El schema del servicio `trip_list` tenía `return_response` como un parámetro opcional:
```python
trip_list_schema = vol.Schema({
    vol.Required("vehicle_id"): str,
    vol.Optional("return_response"): bool,  # ← ERROR!
})
```

#### Corrección Aplicada
```python
trip_list_schema = vol.Schema({
    vol.Required("vehicle_id"): str,
})
```

### Conclusiones

1. **`return_response` NO es un parámetro del servicio** - Es un parámetro de control de la llamada
2. **El schema debe contener SOLO los parámetros reales del servicio**
3. **`vol.PREVENT_EXTRA` es el comportamiento por defecto** - Cualquier key adicional es rechazada
4. **El frontend pasa `return_response: true` como tercer parámetro a `callService`**
5. **El backend registra el servicio con `supports_response=SupportsResponse.ONLY`**

### Referencias

- **HA Core config_validation.py:** `/usr/src/homeassistant/homeassistant/helpers/config_validation.py`
- **HA Core core.py:** `/usr/src/homeassistant/homeassistant/core.py`
- **Voluptuous:** `/usr/local/lib/python3.14/site-packages/voluptuous/__init__.py`
