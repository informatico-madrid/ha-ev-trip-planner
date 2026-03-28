---
name: browser_loading_page_issue
description: Home Assistant muestra página de carga inicial que confunde al agente de Playwright
type: feedback
---

## Problema: Snapshot inicial muestra página de carga de HA

**Regla:** Cuando navegas a Home Assistant, el snapshot inicial muestra la página de carga ("Loading data", "Loading...") durante unos segundos. Esto puede confundir al agente y hacer parecer que el navegador no funciona.

**Por qué:** Home Assistant tarda unos segundos en cargar completamente después del login. Durante ese tiempo, el snapshot muestra:
- ProgressBar "Loading"
- Mensaje "Loading data"
- Logo de Open Home Foundation

**Cómo detectar esto:**
1. Navega a http://192.168.1.201:8124
2. El snapshot inicial muestra página de carga (normal, esperar 2-5 segundos)
3. Si ves "Loading data" o "Loading...", la página aún se está cargando
4. Toma otro snapshot después de esperar para ver el contenido real

**Solución:**
- Dar tiempo suficiente para que la página cargue completamente
- Tomar snapshots múltiples veces si es necesario
- No asumir que el navegador no funciona solo porque ve la página de carga

**Ejemplo de snapshot inicial vs final:**

**Inicial (página de carga):**
```yaml
- generic [ref=e2]:
  - img [ref=e3]
  - generic [ref=e7]:
    - progressbar "Loading" [ref=e10]
    - generic [ref=e13]: Loading data
  - img "Home Assistant is a project by the Open Home Foundation" [ref=e15]
```

**Final (después de cargar):**
```yaml
- button "Home" [ref=...]
- sidebar con integraciones
- panel principal
```

**Lección:** No confundir la página de carga normal de HA con un error de navegación. El agente debe esperar y tomar snapshots adicionales para ver el contenido real.