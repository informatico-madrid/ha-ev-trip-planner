---
name: debugging_cache_busting
description: Forzar actualización de JS en HA con VERSION/TIMESTAMP logs y cache_headers=False
type: feedback
---

**Regla:** Siempre agregar un log de VERSION y TIMESTAMP en el constructor del panel.js para verificar que el código se actualizó correctamente.

**Por qué:** Home Assistant cachea agresivamente el JavaScript. Sin un log de version/timestamp, no hay forma de saber si el navegador está usando el código nuevo o cacheado.

**Cómo aplicar:**
1. Agregar en el constructor:
```javascript
console.log('EV Trip Planner Panel: VERSION=3.0.1 TIMESTAMP=2026-03-27T11:16:00Z');
```

2. Buscar ese log específico en la consola del navegador para verificar que se cargó el código nuevo

3. Usar parámetro en URL: `?v=timestamp` para forzar reload de la página

4. Si el JS no se actualiza, deshabilitar cache en __init__.py:
```python
cache_headers=False  # En lugar de True
```

5. Para forzar reload completo, reiniciar Home Assistant