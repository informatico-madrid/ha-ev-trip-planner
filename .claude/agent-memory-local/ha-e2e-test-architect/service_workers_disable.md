---
name: service_workers_disable
description: Deshabilitar service workers en Playwright para evitar cacheo de JS en HA
type: feedback
---

**Regla:** Siempre configurar `serviceWorkers: 'disable'` en el playwright.config.ts para evitar que Service Workers cacheen el JavaScript en Home Assistant.

**Por qué:** Los Service Workers de HA interceptan las peticiones de red y cachean agresivamente el JavaScript. Esto hace que los cambios en panel.js no se reflejen inmediatamente en el navegador, incluso con `?v=timestamp` en la URL.

**Cómo aplicar:** En playwright.config.ts, configuración global:
```typescript
use: {
  // ... otras configuraciones
  serviceWorkers: 'disable',  // Deshabilitar SW para evitar cacheo de JS
  recordHar: {
    mode: 'records',
    content: 'attach'
  }
}
```

**Alternativa:** Si `serviceWorkers: 'disable'` no funciona, agregar un timestamp dinámico al URL del JS en el panel.py:
```python
cache_bust = str(int(time.time()))
module_url = f"/{DOMAIN.replace('_', '-')}/panel.js?v={cache_bust}"
```

**Verificación:** Buscar logs de VERSION/TIMESTAMP en la consola del navegador para confirmar que se carga el código nuevo.