---
name: investigacion_core_api
description: Método para investigar parámetros de funciones del core de HA antes de usarlas
type: feedback
---

## Regla: Siempre investigar el código del core de HA antes de usar métodos del API

**Por qué:** Las firmas de las funciones en el frontend pueden ser wrappers que ocultan parámetros importantes. El código real está en el core de Python.

**Cómo aplicar:**

### Paso 1: Acceder al contenedor de HA
```bash
docker exec -it homeassistant /bin/bash
```

### Paso 2: Buscar el código en /usr/src/homeassistant/homeassistant
```bash
# Encontrar la función
grep -rn "def async_call" /usr/src/homeassistant/homeassistant/

# Leer la firma completa
grep -n "def async_call" /usr/src/homeassistant/homeassistant/core.py
sed -n '2712,2810p' /usr/src/homeassistant/homeassistant/core.py
```

### Paso 3: Analizar parámetros y validaciones
Buscar:
- Todos los parámetros de la función
- Validaciones que pueden lanzar errores
- Comentarios explicativos

### Paso 4: Documentar y aplicar
- Crear memoria con la investigación
- Actualizar código con los parámetros correctos
- Incluir comentarios explicativos

**Ejemplo real - error return_response:**
```
Error: service_lacks_response_request
Causa: Servicio con supports_response=SupportsResponse.ONLY llamado sin return_response: true
Investigación: core.py:2768-2780 muestra validación estricta
Solución: Añadir { return_response: true } al tercer parámetro
```

**Firma encontrada en core.py:2712:**
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

**Preguntas clave para investigar:**
1. ¿Qué parámetros tiene la función?
2. ¿Hay validaciones que puedan causar errores?
3. ¿Qué valores por defecto tienen los parámetros?
4. ¿Cuál es el comportamiento cuando no se pasa un parámetro?

**Lección:** No asumir que la API del frontend es igual a la del backend. El wrapper puede tener firmas diferentes.