---
name: timestamp_verification_rule
description: Regla obligatoria de actualizar timestamp en cada cambio de panel.js para verificar carga de código nuevo
type: feedback
---

**Regla:** Cada vez que editas panel.js, **DEBES** actualizar el timestamp en el log de versión para verificar que el código nuevo se está cargando.

**Por qué:** Home Assistant cachea agresivamente el JavaScript. Sin un timestamp único en el log, no hay forma de saber si el navegador está usando el código viejo o nuevo.

**Cómo aplicar:**
```javascript
// EN CADA CAMBIO EN panel.js, actualizar el timestamp:
console.log('EV Trip Planner Panel: Lit constructor called');
console.log('EV Trip Planner Panel: VERSION=3.0.1 TIMESTAMP=2026-03-27T11:26:00Z');
```

**Verificación:** Buscar ese log específico en la consola del navegador:
- ✅ Si aparece el timestamp actual → código nuevo cargado
- ❌ Si aparece timestamp antiguo → código cacheado, necesitas reiniciar HA o usar servidor de desarrollo

**Solución para evitar cacheo:**
1. Usar servidor de desarrollo frontend HA con HMR:
```bash
docker exec -it 6b61bccf171f python3 -m homeassistant script/develop
```

2. Forzar hot reload vía API REST:
```bash
docker exec 6b61bccf171f curl -s -X POST http://127.0.0.1:8123/api/config/config_entries/entry/[ENTRY_ID]/reload
```

**Nota:** El timestamp debe reflejar el momento exacto del cambio para que puedas identificar inmediatamente si estás viendo el código nuevo o el cacheado.
