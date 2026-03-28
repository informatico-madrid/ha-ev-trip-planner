---
name: frontend_development_hot_reload
description: Servidor de desarrollo frontend HA con HMR para evitar cacheo agresivo de JS
type: project
---

**Regla:** Cuando modifies JavaScript/TypeScript en componentes de HA, NO usar el servidor normal de producción porque cachea agresivamente. En su lugar, usar el servidor de desarrollo frontend con Hot Module Replacement (HMR).

**Por qué:** Home Assistant usa una caché muy agresiva para el JavaScript frontend. Los cambios en panel.js no se reflejan inmediatamente sin reiniciar HA completo, lo cual es muy lento.

**Cómo aplicar:**

1. **Ejecutar servidor de desarrollo frontend:**
```bash
docker exec -it 6b61bccf171f bash -c "cd /usr/src/homeassistant && python3 -m homeassistant script/develop"
```

Esto levanta un servidor de desarrollo dedicado exclusivamente a los componentes de UI. Con HMR, cualquier cambio en el código JavaScript se inyecta casi instantáneamente en el navegador.

2. **Forzar Hot Reload mediante API REST:**
```bash
docker exec 6b61bccf171f curl -s -X POST http://127.0.0.1:8123/api/config/config_entries/entry/[ENTRY_ID]/reload \
  -H "Content-Type: application/json"
```

Obtener ENTRY_ID desde `/config/.storage/core.config_entries`:
```bash
docker exec 6b61bccf171f cat /config/.storage/core.config_entries | python3 -c "import sys,json; data=json.load(sys.stdin); [print(e) for e in data.get('data',{}).get('entries',[]) if 'ev_trip_planner' in str(e)]"
```

3. **File Watcher automático (opcional):**
Usar `inotifywait` dentro del contenedor para monitorear cambios en `custom_components` y disparar el reload automáticamente:
```bash
inotifywait -m -r -e close_write custom_components/ | while read; do
  curl -X POST http://127.0.0.1:8123/api/config/config_entries/entry/[ENTRY_ID]/reload
done
```

**Nota:** El frontend modificado suele servirse en el puerto 8124 y se conecta al backend en 8123.

**Verificación:** Los logs del navegador mostrarán el timestamp de versión del código cargado:
```
EV Trip Planner Panel: VERSION=3.0.1 TIMESTAMP=2026-03-27T11:16:00Z
```