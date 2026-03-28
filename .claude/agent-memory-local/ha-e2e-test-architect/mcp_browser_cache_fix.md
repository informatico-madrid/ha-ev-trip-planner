---
name: MCP Playwright browser cache fix
description: Solution for HA frontend caching - close browser context to clear cache
type: reference
---

**CRITICAL:** Home Assistant cachea agresivamente el JavaScript en IndexedDB. El MCP Playwright browser carga el código cacheado incluso después de:

- `docker cp` actualizar panel.js
- `docker restart homeassistant`
- Cambios de versión (3.0.5 → 3.0.11)
- Touch files to invalidate cache

**El navegador MCP sigue mostrando VERSION=3.0.5** aunque el contenedor tiene VERSION=3.0.11.

**SOLUCIÓN:** Cerrar el browser context para limpiar el cache:

```bash
# 1. Cerrar el browser context (limpia cache)
browser_close

# 2. Navegar a nueva URL (crea nuevo context)
browser_navigate http://127.0.0.1:8271/

# 3. Navegar al panel específico
browser_navigate http://127.0.0.1:8271/ev-trip-planner-{vehicle_id}
```

**Verificación:**
- VERSION=3.0.6 o superior en console logs → código nuevo cargado
- VERSION=3.0.5 → código cacheado

**Impacto:** El browser_close + browser_navigate pattern es necesario después de cada restart de HA para ver los cambios en panel.js.

**Patrón aplicable:**
1. Aplicar fix en código
2. `docker cp` al contenedor
3. `docker restart homeassistant`
4. `browser_close` → `browser_navigate` (limpiar cache)
5. Verificar VERSION en console logs
6. Testear funcionalidad

**Limitación conocida:** El cache de HA es tan agresivo que el browser MCP necesita este workaround manualmente después de cada cambio.
