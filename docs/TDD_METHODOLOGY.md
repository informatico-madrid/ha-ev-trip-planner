# 🧪 Metodología TDD (Test-Driven Development) - EV Trip Planner

**ADN del Desarrollador**: Esta metodología es **OBLIGATORIA** y **NON-NEGOTIABLE**. Siempre que se reinicie el contexto, este documento debe ser leído primero.

---

## 📋 Principios Fundamentales

### 1. **RED → GREEN → REFACTOR**

**Fase RED**: Escribir tests que FALLAN primero
- Antes de escribir cualquier código de producción, escribir el test
- El test debe fallar inicialmente (verificar que el test es válido)
- Si el test pasa inmediatamente, algo está mal (test falso positivo)

**Fase GREEN**: Escribir el código mínimo para que el test PASE
- Implementar solo lo necesario para hacer pasar el test
- No pre-optimizar, no añadir funcionalidad extra
- Los tests deben pasar después de esta fase

**Fase REFACTOR**: Mejorar el código sin cambiar comportamiento
- Una vez que todos los tests pasan, refactorizar si es necesario
- Mantener todos los tests pasando durante el refactor
- Mejorar legibilidad, rendimiento, mantenibilidad

---

## 🎯 Ciclo de Desarrollo TDD (Obligatorio)

### Para CADA Funcionalidad Nueva:

```bash
# PASO 1: Escribir test (RED)
# - Crear archivo de test si no existe
# - Escribir test que describe la funcionalidad esperada
# - Ejecutar test y verificar que FALLA

pytest tests/test_nueva_funcionalidad.py -v
# Resultado esperado: FAILED (1 failed)

# PASO 2: Implementar código mínimo (GREEN)
# - Crear archivo de producción si no existe
# - Escribir el código MÍNIMO necesario
# - Ejecutar test y verificar que PASA

pytest tests/test_nueva_funcionalidad.py -v
# Resultado esperado: PASSED (1 passed)

# PASO 3: Refactorizar (REFACTOR)
# - Mejorar el código si es necesario
# - Verificar que todos los tests siguen pasando

pytest tests/ -v
# Resultado esperado: Todos los tests pasan

# PASO 4: Commit atómico
git add tests/test_nueva_funcionalidad.py custom_components/...
git commit -m "feat: [descripción] - TDD cycle complete"
```

---

## 📦 Estructura de Tests

### Organización de Archivos:

```
tests/
├── test_config_flow.py              # Tests del flujo de configuración
├── test_config_flow_milestone3.py   # Tests específicos de Milestone 3
├── test_trip_manager.py             # Tests de gestión de viajes
├── test_sensors.py                  # Tests de sensores
├── test_sensors_milestone3.py       # Tests de sensores de Milestone 3
├── test_emhass_adapter.py           # Tests del adaptador EMHASS
├── test_vehicle_controller.py       # Tests del controlador de vehículos
├── test_schedule_monitor.py         # Tests del monitor de schedules
├── test_presence_monitor.py         # Tests del monitor de presencia
├── test_integration.py              # Tests de integración E2E
└── conftest.py                      # Fixtures y configuración
```

### Convenciones de Nomenclatura:

- **Archivos de test**: `test_[modulo].py`
- **Funciones de test**: `async def test_[escenario]_[condicion]()`
- **Fixtures**: `@pytest.fixture` en `conftest.py`
- **Mocks**: Usar `MagicMock` y `AsyncMock` para dependencias externas

---

## 🔍 Tipos de Tests Requeridos

### 1. **Unit Tests** (Cobertura > 80%)

**Qué testear:**
- Lógica de negocio (cálculos, validaciones)
- Transformaciones de datos
- Manejo de errores y edge cases

**Ejemplo:**
```python
async def test_calculate_kwh_needed_valid_input(hass):
    """Test kWh calculation with valid distance and consumption."""
    # Arrange
    distance_km = 100
    consumption_kwh_per_km = 0.15
    
    # Act
    result = calculate_kwh_needed(distance_km, consumption_kwh_per_km)
    
    # Assert
    assert result == 15.0
```

### 2. **Integration Tests**

**Qué testear:**
- Interacción entre componentes
- Flujos completos (ej: crear viaje → publicar en EMHASS → activar carga)
- Comunicación con Home Assistant (services, states)

**Ejemplo:**
```python
async def test_trip_creation_triggers_emhass_publish(hass):
    """Test that creating a trip publishes to EMHASS."""
    # Arrange: Setup vehicle and trip manager
    
    # Act: Create trip via service call
    
    # Assert: Verify EMHASS sensor was created with correct attributes
```

### 3. **Config Flow Tests** (CRÍTICO)

**Qué testear:**
- Validación de entrada del usuario
- Transiciones entre pasos
- Manejo de errores (sensores no existen, formato inválido)
- Creación de entrada de configuración

**Ejemplo:**
```python
async def test_config_flow_invalid_sensor(hass):
    """Test config flow rejects non-existent sensor."""
    # Act: Submit config with invalid sensor entity
    
    # Assert: Error shown, flow doesn't advance
    assert result["errors"]["base"] == "sensor_not_found"
```

---

## ✅ Checklist TDD por Funcionalidad

Antes de marcar una tarea como completada, verificar:

- [ ] **Test escrito** (RED)
  - [ ] Test describe el comportamiento esperado
  - [ ] Test falla inicialmente (verificado)
  - [ ] Test cubre casos normales y edge cases

- [ ] **Código implementado** (GREEN)
  - [ ] Código mínimo para pasar el test
  - [ ] Test pasa después de implementación
  - [ ] No hay código muerto

- [ ] **Refactorización** (REFACTOR)
  - [ ] Código limpio y legible
  - [ ] Nombres descriptivos
  - [ ] Comentarios solo donde sea necesario
  - [ ] Todos los tests siguen pasando

- [ ] **Documentación**
  - [ ] Docstrings en funciones públicas
  - [ ] Comentarios en lógica compleja
  - [ ] README actualizado si es feature visible al usuario

- [ ] **Commit**
  - [ ] Mensaje claro: `feat/fix: descripción - TDD cycle`
  - [ ] Incluye archivos de test y producción
  - [ ] No incluye archivos temporales o de debug

---

## 🚨 Prohibiciones TDD (NO hacer)

❌ **NUNCA** escribir código de producción sin test previo
❌ **NUNCA** escribir tests después del código (no es TDD)
❌ **NUNCA** añadir funcionalidad que no esté en un test
❌ **NUNCA** hacer commit con tests fallando
❌ **NUNCA** borrar tests sin reemplazarlos con tests equivalentes
❌ **NUNCA** usar `time.sleep()` en tests (usar `asyncio.sleep(0)` o fixtures)

---

## 📊 Métricas de Calidad

### Cobertura Mínima Requerida:
- **Overall**: > 80%
- **Código crítico** (control de carga, schedules): > 90%
- **Config flow**: 100% (todos los caminos)

### Ejecución de Tests:
```bash
# Todos los tests
pytest tests/ -v --cov=custom_components/ev_trip_planner

# Tests específicos de Milestone 3
pytest tests/test_config_flow_milestone3.py tests/test_sensors_milestone3.py -v

# Tests con cobertura
pytest tests/ --cov=custom_components/ev_trip_planner --cov-report=html
```

---

## 🔄 Flujo de Trabajo Diario

### Al empezar a trabajar:

```bash
# 1. Verificar estado actual
git status

# 2. Ejecutar todos los tests para asegurar baseline verde
pytest tests/ -v
# Resultado: Todos los tests deben pasar

# 3. Si hay tests fallando, arreglarlos ANTES de añadir nueva funcionalidad
```

### Durante el desarrollo:

```bash
# 1. Escribir test (RED)
# ... editar tests/test_nueva_funcionalidad.py ...

# 2. Ejecutar test y verificar que falla
pytest tests/test_nueva_funcionalidad.py::test_nuevo_test -v
# Resultado: FAILED (esperado)

# 3. Implementar código (GREEN)
# ... editar custom_components/ev_trip_planner/...

# 4. Ejecutar test y verificar que pasa
pytest tests/test_nueva_funcionalidad.py::test_nuevo_test -v
# Resultado: PASSED (esperado)

# 5. Ejecutar TODOS los tests para evitar regresiones
pytest tests/ -v
# Resultado: Todos deben pasar

# 6. Refactorizar si es necesario (REFACTOR)
# ... mejorar código ...

# 7. Verificar tests siguen pasando
pytest tests/ -v
```

### Al finalizar:

```bash
# 1. Ver cobertura
pytest tests/ --cov=custom_components/ev_trip_planner --cov-report=term-missing

# 2. Commit atómico
git add tests/ custom_components/
git commit -m "feat: nueva funcionalidad - TDD cycle complete"

# 3. Push a feature branch
git push origin feature/nueva-funcionalidad
```

---

## 📚 Recursos y Ejemplos

### Ejemplos de Tests en el Proyecto:

- `tests/test_config_flow_milestone3.py` - Tests de config flow Milestone 3
- `tests/test_trip_manager.py` - Tests de gestión de viajes
- `tests/test_sensors.py` - Tests de sensores

### Patrones Comunes:

**Mock de Home Assistant:**
```python
@pytest.fixture
def hass():
    """Create mock Home Assistant instance."""
    hass = MagicMock()
    hass.states = MagicMock()
    hass.services = MagicMock()
    return hass
```

**Test de Servicio:**
```python
async def test_service_add_trip(hass):
    """Test add trip service."""
    # Arrange
    call = ServiceCall(domain=DOMAIN, service="add_recurring_trip", data={...})
    
    # Act
    await handle_add_recurring_trip(call)
    
    # Assert
    assert hass.states.get("sensor.test_trips") is not None
```

---

## 🎯 Recordatorio Final

**ESTA METODOLOGÍA ES TU ADN COMO DESARROLLADOR**

- No se trata de "escribir tests", se trata de "diseñar software a través de tests"
- Los tests son la especificación ejecutable del comportamiento esperado
- Si no hay test, la funcionalidad no existe (no importa si el código está escrito)
- **Siempre que reinicies tu contexto, lee este documento primero**

---

**Documento Version**: 1.0  
**Last Updated**: 2025-12-08  
**Status**: MANDATORY - Must be followed for all development