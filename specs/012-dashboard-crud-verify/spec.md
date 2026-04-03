# Feature Specification: Dashboard CRUD Verification and Deployment

**Feature Branch**: `[012-dashboard-crud-verify]`
**Created**: 2026-03-21
**Status**: Draft
**Input**: User description: "Crear spec nueva que se asegure que pasan todos los tests, la cobertura es correcta, y se despliega o instala el panel de control o dashboard de un coche cuando se agrega a través del configflow. En este panel de control deberían haber operaciones CRUD para viajes del coche. Esto en teoría ya está implementado en las specs anteriores pero por errores en homeassistant y fallos de despliegue no está funcionando. Al final de esta spec cuando esté implementada tengo que poder crear un coche, ir a su panel de control y hacer operaciones CRUD sobre los viajes de ese coche."

---

## User Scenarios & Testing (mandatory)

### User Story 1 - Complete Vehicle Setup and Full CRUD Dashboard (Priority: P1)

**Como** usuario que configura un vehículo eléctrico en EV Trip Planner
**Quiero** completar la configuración del vehículo, acceder a su dashboard y realizar operaciones CRUD completas sobre viajes
**Para** poder gestionar todos mis desplazamientos programados desde una interfaz visual integrada

**Por qué esta prioridad**: Esta es la feature COMPLETA. Sin CRUD de viajes, la integración no tiene valor. Incluye:
- Configuración de vehículo con configflow
- Dashboard automático en Lovelace
- CRUD completo: crear, leer, actualizar, eliminar viajes
- Todos los tests pasando con cobertura >=80%
- Validación: 0 errores críticos en logs, 100% tests passing

**Prueba independiente**: Completar todo el flujo:
1. Configurar vehículo con configflow
2. Verificar dashboard aparece en Lovelace
3. Crear un viaje desde el dashboard
4. Ver el viaje en la lista
5. Editar el viaje desde el dashboard
6. Eliminar el viaje desde el dashboard
7. Ejecutar todos los tests y verificar coverage >=80%
8. Verificar 0 errores críticos en logs

**Escenarios de aceptación**:

1. **Dado** que estoy en Home Assistant configurando EV Trip Planner, **cuando** agrego un nuevo vehículo con configflow, **entonces** el dashboard se crea automáticamente en el perfil Lovelace del usuario

2. **Dado** que el dashboard se creó, **cuando** navego a la sección de EV Trip Planner, **entonces** veo el dashboard con mi vehículo configurado

3. **Dado** que estoy en el dashboard del vehículo, **cuando** selecciono "Crear viaje", **entonces** se muestra un formulario con campos para origen, destino, fecha, hora y distancia estimada

4. **Dado** que estoy llenando el formulario de viaje, **cuando** ingreso todos los campos requeridos y guardo, **entonces** el viaje se persiste y aparece en la lista de viajes

5. **Dado** que tengo un viaje en la lista, **cuando** lo edito, **entonces** se abre el formulario con los valores actuales del viaje

6. **Dado** que estoy editando un viaje, **cuando** modifico los campos y guardo, **entonces** los cambios se persisten y reflejan en el dashboard

7. **Dado** que tengo un viaje, **cuando** selecciono "Eliminar", **entonces** se muestra confirmación y al confirmar el viaje se elimina

8. **Dado** que he completado la implementación, **cuando** ejecuto `pytest tests/ -v --cov=custom_components/ev_trip_planner`, **entonces** todos los tests pasan y coverage >=80%

9. **Dado** que he completado la implementación, **cuando** reviso los logs, **entonces** no hay errores CRÍTICOS relacionados con ev_trip_planner

---

### Edge Cases

- ¿Qué pasa cuando el usuario intenta crear un viaje con fecha pasada? → Debe mostrar error de validación
- ¿Qué pasa cuando el usuario intenta editar un viaje que ya está en el pasado? → Debe deshabilitar edición o mostrar warning
- ¿Qué pasa cuando hay múltiples vehículos configurados? → Dashboard independiente por vehicle_id
- ¿Qué pasa cuando el usuario cierra la sesión y vuelve a entrar? → Dashboard y viajes persisten
- ¿Qué pasa cuando hay un error de conexión con Home Assistant durante una operación CRUD? → Mostrar mensaje de error claro y mantener datos intactos
- ¿Qué pasa cuando el dashboard ya existe y se intenta crear de nuevo? → Agregar sufijo -2, -3, etc. o mostrar mensaje de warning

---

## Requirements (mandatory)

### Functional Requirements

**FR-001**: El sistema DEBE permitir configurar vehículos eléctricos a través del configflow de Home Assistant

**FR-002**: El sistema DEBE crear automáticamente un dashboard de Lovelace para cada vehículo configurado

**FR-003**: El dashboard DEBE mostrar operaciones CRUD completas para gestionar viajes programados

**FR-004**: El sistema DEBE crear entidades sensor en Home Assistant para cada viaje programado

**FR-005**: Las operaciones CRUD DEBN persistir los datos correctamente (crear, leer, actualizar, eliminar)

**FR-006**: El sistema DEBE pasar todas las pruebas automatizadas sin fallos

**FR-007**: El sistema DEBE mantener una cobertura de tests adecuada para la funcionalidad CRUD

**FR-008**: El sistema DEBE generar logs claros sin errores críticos durante la operación

**FR-009**: El sistema DEBE manejar errores de despliegue del dashboard con mensajes claros

**FR-010**: El sistema DEBE soportar múltiples vehículos con dashboards independientes

### Key Entities

- **Vehicle**: Representación de un vehículo eléctrico con sus propiedades (ID, nombre, capacidades, configuración)
- **Trip**: Viaje programado con sus atributos (origen, destino, fecha, hora, distancia, estado)
- **Dashboard**: Interfaz de usuario en Home Assistant Lovelace para gestionar vehículos y viajes
- **Sensor**: Entidad de Home Assistant que expone la información del vehículo y viajes

---

## Success Criteria (mandatory)

### Measurable Outcomes

**SC-001**: 100% de las pruebas automatizadas pasan al ejecutar el suite de tests (`pytest tests/ -v` returns 0 failures)

**SC-002**: La cobertura de código para la funcionalidad CRUD es ≥80% (`pytest --cov-report=term-missing`)

**SC-003**: El dashboard se despliega correctamente en el 100% de los intentos de configuración

**SC-004**: Todas las operaciones CRUD (create, read, update, delete) se ejecutan sin errores

**SC-005**: No hay errores CRÍTICOS en los logs de Home Assistant durante la operación (`grep -i "critical" /config/home-assistant.log` returns empty for ev_trip_planner)

**SC-006**: Los sensores correspondientes a viajes se crean y actualizan correctamente en Home Assistant

**SC-007**: El usuario puede completar el flujo completo de configuración de vehículo, dashboard y CRUD sobre viajes en menos de 5 minutos

---

## State Verification Plan

### Existence Check

Cómo probar que el cambio existe en el sistema real:

- [ ] Verificar que el componente está desplegado (buscar en /config/custom_components/ev_trip_planner)
- [ ] Verificar que las entidades existen (use homeassistant-ops skill to query /api/states)
- [ ] Verificar que el dashboard aparece en /api/lovelace
- [ ] Verificar que los servicios están disponibles (use homeassistant-ops skill to query /api/services)

### Effect Check

Cómo probar que el cambio funciona:

- [ ] Estado de entidad ≠ unavailable/unknown
- [ ] Log de HA muestra inicialización exitosa (buscar mensajes de éxito en logs)
- [ ] Servicios disponibles (use homeassistant-ops skill)
- [ ] Dashboard visible en interfaz de usuario
- [ ] Operaciones CRUD exitosas (crear viaje → aparece en dashboard → editar → actualizar → eliminar → desaparece)

### Reality Sensor Result

- STATE_MATCH = éxito real ✓
- STATE_MISMATCH = fallo real, tarea NO marcada [x]

---

## Dependencies

- pytest-homeassistant-custom-component
- Python 3.11+
- Home Assistant 2026.x
- Home Assistant Container (para pruebas de despliegue real)

---

## Assumptions

1. Home Assistant tiene el módulo de Lovelace disponible
2. El usuario tiene permisos para crear dashboards en su perfil
3. Los datos de los viajes se persisten en YAML (fallback para Container sin Storage API)
4. El configflow funciona correctamente con los datos del vehículo
5. El dashboard template está disponible en el componente

---

## Notes

Este spec se centra en la funcionalidad CRUD completa para viajes, asegurando que:
1. Todos los tests pasan
2. La cobertura de tests es adecuada
3. El dashboard se despliega correctamente
4. Las operaciones CRUD funcionan en Home Assistant real
