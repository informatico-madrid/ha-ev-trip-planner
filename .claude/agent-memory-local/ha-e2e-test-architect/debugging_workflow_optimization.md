---
name: debugging_workflow_optimization
description: Metodología optimizada para debugging de issues de cache y respuesta en HA frontend
type: project
---

## Lecciones del Caso: Response Extraction Fix

### Problema del Cache de JS en HA

**Observación crítica:** Home Assistant cachea agresivamente el JavaScript. Los logs mostraban VERSION=3.0.1 incluso después de cambiar el código.

**Flujo correcto encontrado:**
1. Actualizar timestamp en panel.js (VERSION + timestamp único)
2. Reiniciar HA para forzar recarga del panel
3. Forzar hard reload en navegador (?v={timestamp} o Ctrl+Shift+R)
4. Verificar logs muestran VERSION correcta
5. Inspeccionar response real del servicio

### Lo que Debo Hacer en Futuras Sesiones

#### 1. Verificar Cache ANTES de Asumir

**Pattern a implementar:**
```javascript
// Al primer log de versión, verificar inmediatamente
// Si VERSION no coincide con lo que acabo de cambiar → cache activo
// → Forzar reload antes de continuar debugging
```

#### 2. Estructura de Response de HA - Conocimiento Previo

**Antes de implementar callService, verificar documentación:**
- `supports_response=SupportsResponse.NONE` → no hay response
- `supports_response=SupportsResponse.ONLY` → response en `response.response`
- `supports_response=SupportsResponse.EXPECTED` → response en `response.result`

**Fuentes de verdad:**
- `/usr/src/homeassistant/homeassistant/core.py` línea 2712-2810
- `/mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source/src/types.ts`

#### 3. Debug Flow Optimizado

```
┌─────────────────────────────────────────────────────┐
│ 1. Ver logs de versión (VERSION=3.0.x)              │
├─────────────────────────────────────────────────────┤
│ 2. Si VERSION != esperado → FORZAR RELOAD          │
├─────────────────────────────────────────────────────┤
│ 3. Inspeccionar response real del servicio         │
│    - console.log(response)                          │
│    - Verificar estructura: response.response vs    │
│      response.result                                │
├─────────────────────────────────────────────────────┤
│ 4. Corregir extracción según estructura real       │
├─────────────────────────────────────────────────────┤
│ 5. Verificar DOM renderizado con datos completos   │
└─────────────────────────────────────────────────────┘
```

### Checklist Preventiva para Future Sessions

Antes de implementar `callService`:

- [ ] Verificar `supports_response` en service registration
- [ ] Consultar frontend source para estructura del response
- [ ] Implementar logging del response completo
- [ ] Verificar VERSION/timestamp en logs
- [ ] Planear hard reload si se modifica panel.js

### Métricas de Eficiencia

**Tiempo perdido:** ~30 min debuggando cache
**Causa:** No verificar VERSION antes de asumir que el código nuevo está cargado
**Solución:** Verificar VERSION en primer log → si incorrecto, reiniciar inmediatamente

**Tiempo ganado en solución:** ~5 min
**Causa:** Conocimiento correcto de respuesta.response vs response.result
**Factor clave:** No asumir, verificar response real en consola

### Conocimiento Crítico para Próxima Sesión

1. **Cache de JS en HA:** Siempre verificar VERSION antes de continuar debugging
2. **Response structure:** SupportsResponse.ONLY usa `response.response`, no `response.result`
3. **Debug flow:** Logs → inspeccionar response real → corregir → verificar DOM
4. **Hard reload:** Si VERSION incorrecta, reiniciar HA inmediatamente

### Automatización Futura

**Script para verificar VERSION:**
```bash
# Extraer VERSION de panel.js
grep "VERSION=" custom_components/ev_trip_planner/frontend/panel.js | tail -1

# Comparar con lo que se espera
# Si mismatch → restart homeassistant
```

**Documentar en CLAUDE.md:**
- "Siempre verificar VERSION en logs antes de asumir código cargado"
- "SupportsResponse.ONLY → response.response, no result"