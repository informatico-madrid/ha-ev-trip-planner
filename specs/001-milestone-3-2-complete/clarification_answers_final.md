# Clarification Answers - Final

**Feature**: `001-milestone-3-2-complete`  
**Created**: 2026-03-17  
**Status**: ✅ All Clarifications Resolved

---

## 🔴 CRITICAL Clarifications

### 1. Charging Sensor Failure - CONFIG FLOW
**Question**: ¿Qué hacer si el sensor de carga falla en el config flow?  
**Answer**: **ERROR BLOQUEANTE** - No permitir avanzar si el sensor de carga no está en funcionamiento. El sensor debe estar operativo para configurar el vehículo.

### 2. Charging Sensor Failure - TRIP MANAGEMENT  
**Question**: ¿Qué hacer si el sensor de carga falla al crear/editar un viaje?
**Answer**: **ERROR BLOQUEANTE** - No permitir guardar el viaje si el sensor de carga no está en funcionamiento. Validación crítica antes de guardar.

### 3. Charging Sensor Failure - RUNTIME
**Question**: ¿Qué hacer si el sensor de carga falla al cargar el coche?
**Answer**: 
- **No bloquear** - Solo notificar al usuario para que comprueba manualmente
- **Loguear como WARNING** - De la forma habitual en HA
- **Continuar operación** - No detener el flujo por falla de sensor

### 4. Shell Command Approach
**Question**: ¿Cómo ejecutamos el shell command?
**Answer**: 
- **NO ejecutamos el shell command** - EMHASS ya lo tiene instalado el usuario
- **Solo damos ejemplo** - Proporcionamos variable/ejemplo de shell command que el usuario copia y pega
- **Ya estaba claro** - Esto no es ambiguo, el usuario configura EMHASS previamente

### 5. Power Profile Watts Meaning
**Question**: ¿Qué significan los valores en power_profile_watts?
**Answer**: 
- **0W = False/Null** - No se está cargando
- **Valor positivo = Potencia de carga** - Ej: 3600W = cargando a 3.6kW
- **Variable del shell command** - Para las cargas aplazables en EMHASS

### 6. Testing Scope
**Question**: ¿Qué exactamente se excluye de "no infrastructure tests"?
**Answer**: 
- **Tests típicos de código** - Tests unitarios e integración normales
- **NO tests absurdos** - No testear si un cable soporta 6000W (fuera del alcance)
- **Best practices** - Seguir mejores prácticas de testing de código

---

## 🟡 HIGH PRIORITY Clarifications

### 7. Manual Input Fallback - Planning Horizon
**Question**: ¿Qué hacer si el sensor de planificación no está disponible?
**Answer**: 
- **Usar config de EMHASS** - Leer de `$EMHASS_CONFIG_PATH/config.json`
- **Campo en config_flow** - Decir al usuario la ruta de su config.json
- **Instalación final** - El usuario final podrá tenerlo en otro lugar
- **Fallback manual** - Si no hay sensor, usar valor manual

### 8. Deferrables Schedule Structure
**Question**: ¿Cuál es la estructura exacta del array deferrables_schedule?
**Answer**: 
- **Referencia implementación** - Fijarse en la implementación actual en nuestro EMHASS
- **Variable del shell command** - Es una de las variables del shell command
- **No especificar aquí** - Verificar en implementación real

### 9. Notification Content Format
**Question**: ¿Qué formato debe tener el contenido de notificaciones?
**Answer**: 
- **Usuario elige canal** - Canal/sensor/entidad de notificaciones en config_flow
- **Texto creativo** - El texto lo pongo yo (implementación)
- **Flexible** - Adaptarse al canal elegido

### 10. Notification Timing
**Question**: ¿Cuándo deben enviarse las notificaciones?
**Answer**: 
- **Cuando sean necesarias** - En el momento oportuno según el contexto
- **Sin timing específico** - No definir horarios fijos

### 11. Shell Command Failure Handling
**Question**: ¿Qué hacer si el shell command falla?
**Answer**: 
- **EMHASS lo maneja** - Esto es responsabilidad de EMHASS, no nuestra
- **Verificar sensores** - Podemos ver si el sensor de EMHASS incluyó las cargas aplazables
- **Panel de control** - Por cada viaje mostrar:
  - Carga aplazable enviada a EMHASS
  - Sensor de carga aplazable devuelto por EMHASS
- **No bloquear** - No detener operación por falla de shell command

### 12. Power Profile Calculation Errors
**Question**: ¿Qué hacer si el cálculo de power profile falla?
**Answer**: 
- **No especificado** - No se me ocurre edge case específico
- **Dejar al desarrollador** - El que implemente se fija si aparece alguno

### 13. Phase Dependency Order
**Question**: ¿Cuál es el orden lógico de fases de implementación?
**Answer**: 
- **Orden lógico** - Dependencias lógicas naturales
- **Confío en tu criterio** - Tú lo sabrás mejor que yo
- **Secuencial donde sea necesario** - Implementación ordenada

---

## 🟢 MEDIUM/LOW Clarifications

### 14-16. Performance Requirements
**Question**: ¿Qué performance requirements definir?
**Answer**: 
- **Que fluya normal** - Sin requerimientos específicos de performance
- **Experiencia fluida** - Que la UX sea fluida y responsiva

### 17-19. Logging Requirements
**Question**: ¿Qué logging requirements definir?
**Answer**: 
- **Standard de HA** - Seguir el estándar de logging de Home Assistant
- **Niveles apropiados** - DEBUG, INFO, WARNING, ERROR según contexto

### 20-24. Edge Cases
**Question**: ¿Qué edge cases adicionales?
**Answer**: 
- **No se me ocurre ninguno** - No tengo edge cases específicos en mente
- **Dejar al desarrollador** - El que crea las tareas se fija si encuentra alguno
- **O al implementar** - El que implementa se fija si aparece alguno no previsto

### 25-26. Documentation Requirements
**Question**: ¿Qué documentation requirements?
**Answer**: 
- **Actualizar toda la documentación** - Actualizar documentación actual existente
- **Crear nueva documentación** - Crear documentación nueva donde sea necesario
- **Última parte de tareas** - Es la última parte de las tareas
- **Muy importante** - Es importantísimo hacerlo completo

### 27-37. Additional Items
**Question**: Otros items sin clarificar
**Answer**: 
- **No especificado** - Items sin preguntas específicas
- **Dejar a criterio** - Decidir durante implementación
- **Best practices** - Seguir mejores prácticas

---

## 📋 Summary

| Category | Count | Status |
|----------|-------|--------|
| CRITICAL | 6 | ✅ Resolved |
| HIGH | 7 | ✅ Resolved |
| MEDIUM/LOW | 24 | ✅ Resolved |
| **TOTAL** | **37** | **✅ All Resolved** |

---

## 🎯 Key Decisions

### Blocking Validation
- ✅ Charging sensor **must** be functional in config flow
- ✅ Charging sensor **must** be functional when creating/editing trips
- ✅ Runtime failures → **notify only**, log warning, continue

### EMHASS Integration
- ✅ User configures EMHASS shell command (not us)
- ✅ We provide example, user copies/pastes
- ✅ We verify EMHASS sensors include our deferrable loads

### Testing Scope
- ✅ Normal code tests (unit, integration)
- ❌ No infrastructure/physical tests (cable capacity, etc.)

### Documentation
- ✅ Update existing documentation
- ✅ Create new documentation as needed
- ✅ Last phase of implementation

### Logging
- ✅ HA standard logging levels
- ✅ Appropriate for context

---

**All clarifications resolved and ready for implementation.**
