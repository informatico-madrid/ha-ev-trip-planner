#!/usr/bin/env python3
"""
Update T999 instructions in tasks.md to be more explicit about error handling
"""

import re
from pathlib import Path

tasks_file = Path("/home/malka/ha-ev-trip-planner/specs/019-panel-vehicle-crud/tasks.md")

# Read the file
content = tasks_file.read_text()

# New instructions for T999 error handling
new_t999_section = """## Phase Final: VERIFICACIÓN COMPLETA INTEGRADA

- [ ] T999 [VERIFY:BROWSER] Verificación Funcional Completa del Panel de Vehículo
  **Objetivo**: Verificar de forma integral y exhaustiva TODA la funcionalidad definida en spec.md para esta especificación. Esta tarea consolida todas las verificaciones de las User Stories en una sola tarea comprehensiva.
  
  **⚠️ CRÍTICO - Procedimiento en caso de ERROR DETECTADO**:
  
  Cuando encuentres un error durante la verificación, DEBES seguir ESTOS PASOS EXACTOS en orden:
  
  ### PASO 1: Identificar la(s) tarea(s) problemática(s)
  - Determinar exactamente qué US/task tiene el problema
  - Ejemplo: "T006-T007: Nombre del dispositivo incorrecto"
  
  ### PASO 2: Desmarcar la(s) tarea(s) usando herramientas MCP
  Usa **mcp-shell** para editar tasks.md directamente:
  ```bash
  # Cambia [x] por [ ] en la línea de la tarea problemática
  sed -i 's/- \\[x\\] T006/- [ ] T006/' specs/019-panel-vehicle-crud/tasks.md
  ```
  O usa Python si prefieres:
  ```python
  with open('specs/019-panel-vehicle-crud/tasks.md', 'r') as f:
      lines = f.readlines()
  # Busca la línea y cambia [x] por [ ]
  lines[i] = lines[i].replace('- [x]', '- [ ]')
  with open('specs/019-panel-vehicle-crud/tasks.md', 'w') as f:
      f.writelines(lines)
  ```
  
  ### PASO 3: Documentar el error EN LA MISMA LÍNEA de la tarea
  Añade inmediatamente después de la descripción de la tarea:
  ```markdown
  **ERROR DETECTADO**: [Descripción clara del error]
  - Paso donde falla: FASE X
  - Error específico: [detalles]
  - Logs relevantes: [copiar logs del contenedor o consola]
  - Análisis: [causa raíz sospechada]
  - Sugerencia: [qué revisar/corregir]
  ```
  
  ### PASO 4: Buscar y documentar logs del problema
  ```bash
  docker logs ha-ev-test --tail 100 | grep -i "error\\|warn" | tail -50
  ```
  Copia los logs relevantes y añádelos como comentario en la tarea.
  
  ### PASO 5: Analizar código fuente del core
  - Revisa panel.js, config_flow.py, sensor.py según corresponda
  - Compara lo esperado vs lo implementado
  - Documenta hallazgos en la tarea
  
  ### PASO 6: Emitir señal de estado
  Después de desmarcar y documentar, emite EXACTAMENTE esto:
  ```
  <promise>STATE_MISMATCH</promise>
  ```
  
  **NO continues hasta haber completado todos los pasos 1-6**.
  
  **EJEMPLO REAL DE LO QUE DEBES HACER**:
  ```
  ## Task T006-T007: Nombre de dispositivo
  
  - [ ] T006 [P] [US2] Modificar sensor.py device_info...
    **ERROR DETECTADO**: El nombre del dispositivo es "EV Trip Planner vehicle-name-123" 
    en lugar de "EV Trip Planner CochePrueba"
    - Paso donde falla: FASE 2
    - Error específico: device_info usa vehicle_id en lugar de vehicle_name
    - Logs: "device_info: Using vehicle_id instead of vehicle_name"
    - Análisis: check sensor.py line ~45, uses self.config.get('vehicle_id') 
    - Sugerencia: Cambiar a self.config.get('vehicle_name')
  
  <promise>STATE_MISMATCH</promise>
  ```
  
  #### PASOS DE VERIFICACIÓN (orden optimizado para máxima cobertura en mínimo tiempo):
"""

# Find and replace the section from "## Phase Final: VERIFICACIÓN COMPLETA INTEGRADA" to before "#### PASOS DE VERIFICACIÓN"
pattern = r'(## Phase Final: VERIFICACIÓN COMPLETA INTEGRADA\n\n.*?)(\n  #### PASOS DE VERIFICACIÓN)'
replacement = new_t999_section + r'\2'

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
tasks_file.write_text(new_content)
print("✓ Updated T999 instructions successfully!")
print(f"File: {tasks_file}")
