---
name: MCP Playwright isolated mode - output style update
description: MCP Playwright browser cache fix applied via --isolated and --storage-state configuration
type: reference
---

**OUTPUT STYLE UPDATE:** MCP Playwright browser cache fix applied via configuration.

**Problem:** MCP Playwright cachea VERSION=3.0.5 aunque el contenedor HA tiene VERSION=3.0.11.

**Solution Applied:**

Archivo: `/home/malka/.claude/plugins/marketplaces/claude-plugins-official/external_plugins/playwright/.mcp.json`

```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest", "--isolated", "--storage-state=/tmp/playwright-storage-state.json"]
  }
}
```

**Efecto:**
1. `--isolated` - Cada sesión inicia en perfil aislado, sin cache persistente
2. `--storage-state=/tmp/playwright-storage-state.json` - Estado guardado en `/tmp` (efímero)
3. `browser_close` cierra contexto completo, limpiando cache
4. `browser_navigate` crea nuevo contexto sin cache de HA

**Verificación:**
- VERSION=3.0.11+ en console logs = nuevo código cargado
- VERSION=3.0.5 = código cacheado (problema resuelto)

**Impacto permanente:** El MCP browser ahora carga código nuevo después de `docker restart homeassistant` sin workaround manual.

**Nota:** El archivo `/tmp/playwright-storage-state.json` se limpia automáticamente al reiniciar el sistema.
