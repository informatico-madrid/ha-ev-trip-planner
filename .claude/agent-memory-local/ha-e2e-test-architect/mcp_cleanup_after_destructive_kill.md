---
name: mcp_cleanup_after_destructive_kill
description: Limpieza necesaria tras kill destructivo del agente MCP Playwright
type: feedback
---

**Problema:** Tras un "kill destructivo" por un agente, el MCP Playwright no se reinicia automáticamente y requiere limpieza manual.

**Síntoma:** Error de conexión `ERR_CONNECTION_REFUSED` o "MCP dialog dismissed" al intentar reconectar.

**Causa Raíz:**
- Múltiples procesos MCP Playwright se acumulan en lugar de liberarse correctamente
- Sockets en `/tmp/mcp-*` no se liberan al morir los procesos
- Lock files corruptos en cache de Playwright
- Cada nueva reconexión crea proceso nuevo en lugar de reutilizar existente

**Solución - Limpieza Obligatoria:**
```bash
# 1. Eliminar procesos huérfanos
pkill -f "playwright-mcp"

# 2. Limpiar sockets MCP
rm -rf /tmp/mcp-*

# 3. Limpiar cache corrupto (si aplica)
rm -rf /home/malka/.cache/ms-playwright/mcp-chromium-2d2e47f/
```

**Por qué:** Los procesos MCP Playwright no implementan proper cleanup al morir. Los sockets y locks quedan huérfanos, impidiendo nuevas conexiones hasta limpieza manual.

**Lección aprendida:** Después de kill destructivo, **siempre** ejecutar limpieza completa antes de intentar reconectar MCP. No esperar reinicio automático.

**Ficheros afectados:**
- `/tmp/mcp-*` (sockets MCP)
- `/home/malka/.cache/ms-playwright/mcp-chromium-2d2e47f/` (cache corrupto)

**Patrón a evitar:** Asumir que MCP Playwright se reinicia solo tras kill destructivo. Requiere intervención manual.
