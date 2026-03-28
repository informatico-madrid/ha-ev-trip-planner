---
name: playwright_mcp_lock_file_issue
description: Bloqueo de Playwright MCP por lock file corrupto en cache directory
type: feedback
---

**Problema encontrado:** El MCP Playwright fallaba con `ERR_CONNECTION_REFUSED` porque el lock file en `/home/malka/.cache/ms-playwright/mcp-chromium-2d2e47f/` estaba corrupto.

**Síntoma:** El navegador no se conectaba y aparecían errores de conexión rechazada.

**Solución:** Eliminar el lock file corrupto:
```bash
rm -rf /home/malka/.cache/ms-playwright/mcp-chromium-2d2e47f/
```

**Por qué:** Playwright MCP guarda un lock file para evitar múltiples instancias del mismo navegador. Si el proceso anterior muere sin liberar el lock, queda un archivo corrupto que impide crear nuevas instancias.

**Lección aprendida:** Cuando Playwright MCP falla repentinamente con errores de conexión, verificar y limpiar el cache de Playwright antes de intentar reiniciar.

**Ficheros afectados:** /home/malka/.cache/ms-playwright/mcp-chromium-2d2e47f/ (directorio completo)