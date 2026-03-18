# Ralph Loop - Pendiente

## Bugs a'arreglar

### 1. Soporte para modelo local (qwen)
- **Problema**: Qwen no genera output sustancial con `--dangerously-skip-permissions`
- **Síntoma**: Output de 1 byte cuando el prompt incluye tareas complejas
- **Solución propuesta**: 
  - Investigar configuración de permisos para qwen
  - O usar modelo de Anthropic como alternativa

### 2. Task ID (T???) no se muestra correctamente
- **Problema**: El script busca ID en la primera línea del checkbox
- **Síntoma**: Muestra "T???" en lugar de "T001"
- **Solución**: Modificar get_task_at_index para buscar ID en todo el body

### 3. Captura de output con modelos locales
- **Problema**: Con prompts largos (>1KB), el output se captura vacío
- **Causa**: Posiblemente streaming no controlado
- **Solución**: Implementar espera activa hasta tener >100 bytes estables

## Notas
- El problema principal es que qwen no funciona bien con --dangerously-skip-permissions
- Cuando funciona (modelos de Anthropic), los logs tienen contenido completo
- Considerar usar CLAUDE_MODEL environment variable para forzar modelo específico
