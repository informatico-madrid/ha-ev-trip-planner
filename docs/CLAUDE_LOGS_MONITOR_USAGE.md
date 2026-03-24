# Claude Logs Monitor - Guía de Uso

## 📋 Descripción

Script de monitoreo de logs de Claude para capturar herramientas y respuestas en tiempo real. **Versión segura** que evita bloqueos del servidor.

## ⚠️ Cambios Importantes (vs versión anterior)

| Problema Anterior | Solución Nueva |
|------------------|----------------|
| Procesaba TODOS los logs históricos | Solo procesa logs desde fecha especificada |
| Podía bloquear el servidor | Filtrado por fecha + límites de seguridad |
| Sin control de tamaño | Rotación automática de logs (máx 10MB) |
| Sin persistencia de posición | Marcador de posición para no re-procesar |
| Sin límites | Máximo 1000 líneas por sesión |

## 🚀 Uso Rápido

### Ver logs de hoy (por defecto)
```bash
cd /home/malka/ha-ev-trip-planner/.ralph
./claude_logs_monitor.sh
```

### Ver logs desde una fecha específica
```bash
# Logs de esta semana
./claude_logs_monitor.sh --since "2026-03-17"

# Logs de hace 3 días
./claude_logs_monitor.sh --since "$(date -d '3 days ago' +%Y-%m-%d)"
```

### Especificar directorio de logs
```bash
./claude_logs_monitor.sh "2026-03-24" "/path/to/custom/logs/dir"
```

## 🔧 Configuración

### Variables ajustables

```bash
MAX_LOG_SIZE="10M"           # Tamaño máximo antes de rotar
MAX_LINES_PER_SESSION=1000   # Límite de líneas por sesión
SINCE_DATE="${1:-$(date +%Y-%m-%d)}"  # Fecha por defecto: hoy
```

### Archivos generados

- `logs/claude_tool_logs.log` - Logs principales
- `logs/claude_tool_logs.log.marker` - Posiciones de procesamiento
- `logs/claude_tool_logs.log.*` - Logs rotados (backup automático)

## 📊 Formato de Salida

Cada línea sigue este formato:

```
[YYYY-MM-DD HH:MM:SS] [session-id] MSG_TYPE: tool_type
[YYYY-MM-DD HH:MM:SS] [session-id] TOOL: tool_name (id: xxxxxxxxxx)
[YYYY-MM-DD HH:MM:SS] [session-id] INPUT: {...}
[YYYY-MM-DD HH:MM:SS] [session-id] STDOUT: {...}
[YYYY-MM-DD HH:MM:SS] [session-id] THINKING: {...}
[YYYY-MM-DD HH:MM:SS] [session-id] STOP_REASON: done
```

## 🔍 Consultas Útiles

### Buscar logs de una herramienta específica
```bash
grep "TOOL: ExecuteCommandLine" logs/claude_tool_logs.log
```

### Buscar logs de una sesión específica
```bash
grep "session-id-aqui" logs/claude_tool_logs.log
```

### Ver últimas líneas
```bash
tail -f logs/claude_tool_logs.log
```

### Contar herramientas usadas
```bash
grep "TOOL:" logs/claude_tool_logs.log | cut -d':' -f3 | sort | uniq -c | sort -rn
```

## 🛡️ Características de Seguridad

1. ✅ **Filtrado por fecha**: Solo procesa archivos nuevos/modificados después de la fecha especificada
2. ✅ **Marcador de posición**: No re-procesa logs antiguos
3. ✅ **Rotación automática**: Los logs se rotan cuando alcanzan 10MB
4. ✅ **Límites de procesamiento**: Máximo 1000 líneas por sesión
5. ✅ **Procesamiento asíncrono**: Hasta 5 procesos simultáneos
6. ✅ **Validación de archivos**: Solo procesa JSONL válidos

## 🐛 Troubleshooting

### El script no procesa nada
- Verificar que la fecha sea correcta: `./claude_logs_monitor.sh --help`
- Comprobar directorio de logs: `$HOME/.claude/projects`
- Verificar permisos de lectura

### Los logs son muy grandes
- Revisar configuración: `MAX_LOG_SIZE="10M"`
- Usar filtro de fecha más estricto
- Limpiar logs rotados manualmente

### Error de memoria
- Reducir `MAX_LINES_PER_SESSION`
- Aumentar intervalo entre procesos
- Usar fechas más específicas

## 📝 Ejemplos Avanzados

### Monitoreo continuo con tail
```bash
./claude_logs_monitor.sh && tail -f logs/claude_tool_logs.log
```

### Exportar logs a JSON
```bash
grep "INPUT:" logs/claude_tool_logs.log | jq -s '.' > logs/claude_tools.json
```

### Generar reporte diario
```bash
#!/bin/bash
# En crontab: 0 8 * * *
cd /home/malka/ha-ev-trip-planner/.ralph
./claude_logs_monitor.sh "$(date -d yesterday +%Y-%m-%d)"
echo "=== Reporte $(date) ===" >> logs/report.txt
grep "STOP_REASON" logs/claude_tool_logs.log >> logs/report.txt
```

## 🔄 Migración desde Versión Antigua

El backup del script original está disponible como:
```
claude_logs_monitor.sh.backup
```

Si necesitas revertir temporalmente:
```bash
mv claude_logs_monitor.sh.backup claude_logs_monitor.sh
```

## 📞 Soporte

Para problemas o sugerencias, revisar:
- Logs de error: `stderr`
- Estado del proceso: `ps aux | grep claude_logs_monitor`
- Archivo de posiciones: `logs/claude_tool_logs.log.marker`

---

**Fecha de actualización**: 2026-03-24  
**Versión**: 2.0 (Segura)
