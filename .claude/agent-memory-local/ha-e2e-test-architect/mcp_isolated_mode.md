---
name: MCP Playwright isolated mode configuration
description: MCP Playwright configuration with --isolated and --storage-state for cache clearing
type: reference
---

**CRITICAL FIX:** MCP Playwright browser cachea agresivamente el JS de HA. Solución: configurar `--isolated` y `--storage-state`.

**Archivo modificado:** `/home/malka/.claude/plugins/marketplaces/claude-plugins-official/external_plugins/playwright/.mcp.json`

**Configuración anterior:**
```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest"]
  }
}
```

**Configuración nueva:**
```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest", "--isolated", "--storage-state=/home/malka/.claude/projects/playwright-storage-state.json"]
  }
}
```

**Efecto:**
1. `--isolated` - Cada sesión inicia en perfil aislado, sin cache persistente
2. `--storage-state=/home/malka/.claude/projects/playwright-storage-state.json` - Estado guardado en ruta con permisos de Claude Code
3. `browser_close` cierra contexto completo, limpiando cache
4. `browser_navigate` crea nuevo contexto sin cache de HA

**Verificación:**
- VERSION=3.0.11+ en console logs = nuevo código cargado
- VERSION=3.0.5 = código cacheado (problema resuelto)

**Impacto:**
- MCP browser ahora carga código nuevo después de `docker restart homeassistant`
- No requiere workaround manual de cache
- Cada sesión es completamente aislada

**Nota:** El archivo `/tmp/playwright-storage-state.json` se limpia automáticamente al reiniciar el sistema.
