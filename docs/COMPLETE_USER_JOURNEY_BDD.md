# Complete User Journey - BDD Approach for Home Assistant

## 🎯 Concepto Central

**Cada task debe simular el ciclo de vida COMPLETO del usuario en entorno REAL:**

```
Deploy → Register → Use → Verify → Complete
  (Taller) (Registro) (Martillo) (Verificar) (Terminar)
```

---

## 🔄 El Flujo Completo de 5 Pasos

### Paso 1: Deploy to Workshop (Cargar en el Taller)
**"Desplegar el martillo en el taller"**

```bash
# Copiar componente a HA
cp -r custom_components/ev_trip_planner /home/malka/homeassistant/custom_components/

# Verificar despliegue
# El agente usa [VERIFY:*] tags y emite STATE_MATCH
# El shell verifica STATE_MATCH si la tarea tiene [VERIFY:*]
```

**Qué verificar:**
- ✅ Componente copiado a `/config/custom_components/`
- ✅ `manifest.json` válido
- ✅ Archivos requeridos presentes
- ✅ Deployment verifier devuelve "DEPLOYED ✓"

---

### Paso 2: First-Time Registration (Registrar por Primera Vez)
**"Registrar el martillo por primera vez"**

```bash
# Crear config entry via REST API
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -d '{
    "domain": "ev_trip_planner",
    "title": "My EV Trip Planner",
    "data": {
      "account_id": "user_123",
      "vehicle_id": "tesla_model_3"
    }
  }' \
  http://192.168.1.100:8123/api/config/config_entries/post

# Verificar registro
curl http://192.168.1.100:8123/api/config/config_entries/entry | jq '.[] | select(.domain == "ev_trip_planner")'
```

**Qué verificar:**
- ✅ Config entry creado exitosamente
- ✅ Entry aparece en lista de entries
- ✅ Domain correcto: `ev_trip_planner`
- ✅ State: `loaded` o `setup_in_progress`

---

### Paso 3: Functional Usage (Usar el Martillo - Amartillar)
**"Usar el martillo para amartillar y reparar"**

```bash
# Test sensor reading
curl http://192.168.1.100:8123/api/states/sensor.ev_trip_distance
# Expected: {"entity_id":"sensor.ev_trip_distance","state":"125.5",...}

# Test service call
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -d '{"trip_id": "trip_001", "destination": "Madrid"}' \
  http://192.168.1.100:8123/api/services/ev_trip_planner/calculate_trip

# Test device control
curl http://192.168.1.100:8123/api/devices | jq '.[] | select(.manufacturer | contains("EV Trip"))'
```

**Qué verificar:**
- ✅ Sensors retornan valores numéricos válidos
- ✅ Services responden correctamente
- ✅ Devices aparecen en registry
- ✅ Entidades registradas con estados válidos

---

### Paso 4: Real Environment Verification (Probar en Taller)
**"Verificar que funciona en entorno real"**

```bash
# Check entity state is valid
STATE=$(curl -s http://192.168.1.100:8123/api/states/sensor.ev_trip_distance | jq -r '.state')
test "$STATE" != "unavailable" && test "$STATE" != "unknown" && echo "✓ Sensor working" || echo "✗ Sensor broken"

# Check logs for initialization
grep -i "ev-trip-planner initialized" /home/malka/homeassistant/home-assistant.log | tail -5

# Check config entries exist
CONFIG_ENTRIES=$(curl -s -H "Authorization: Bearer $HA_TOKEN" http://192.168.1.100:8123/api/config/config_entries/entry | jq '.[] | select(.domain == "ev_trip_planner") | length')
test "$CONFIG_ENTRIES" -gt 0 && echo "✓ Config entries exist" || echo "✗ No config entries"

# Check entities registered
ENTITIES=$(curl -s http://192.168.1.100:8123/api/states | jq '.[] | select(.entity_id | contains("ev_trip")) | length')
test "$ENTITIES" -gt 0 && echo "✓ Entities registered" || echo "✗ No entities"
```

**Qué verificar:**
- ✅ Estado de entidades no es "unavailable" ni "unknown"
- ✅ Logs muestran mensajes de inicialización
- ✅ Config entries existen y están activos
- ✅ Entidades registradas en sistema

---

### Paso 5: Only Then Mark Complete (Solo Entonces Marcar Terminado)
**"Solo entonces marcar como [x]"**

Mark task as [x] **ONLY IF ALL** of the following are true:
- ✅ Deployment verified: `DEPLOYED ✓`
- ✅ First-time registration successful
- ✅ Functional usage tested (sensors, services, devices work)
- ✅ Real environment verification passed
- ✅ All checks above return success

---

## 📋 Template para Cada Task

### Ejemplo: Task para Añadir Sensor de Distancia

```markdown
- [ ] T001: Implement trip distance sensor
  **Complete User Journey Required:**
  
  1. **Deploy**: 
     - Copy component to `/config/custom_components/`
     - Run [VERIFY:*] tags + STATE_MATCH → DEPLOYED ✓
  
  2. **Register**:
     - Create integration config entry
     - Verify entry appears in /api/config/config_entries
  
  3. **Use**:
     - Trigger trip calculation via service
     - Check sensor returns numeric value > 0
     - Verify sensor state is not "unavailable"
  
  4. **Verify**:
     - Sensor exists: curl /api/states/sensor.ev_trip_distance
     - State valid: test "$STATE" != "unavailable"
     - Logs show: grep "trip distance calculated"
     - Entity registered: curl /api/states | jq '.[] | select(.entity_id == "sensor.ev_trip_distance")'
  
  5. **Complete**:
     - Only if all 4 steps succeed → Mark [x]
```

---

## 🎯 Ejemplos Completos por Tipo de Feature

### 1. Sensor Feature

**Task:** Add EV trip distance sensor

**User Journey:**
```bash
# Step 1: Deploy
cp -r custom_components/ev_trip_planner /home/malka/homeassistant/custom_components/
python3 .ralph/scripts/[VERIFY:*] tags + STATE_MATCH ev_trip_planner

# Step 2: Register
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -d '{"domain": "ev_trip_planner", "title": "Test"}' \
  http://192.168.1.100:8123/api/config/config_entries/post

# Step 3: Use - Trigger trip and check sensor
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -d '{"origin": "Madrid", "destination": "Barcelona"}' \
  http://192.168.1.100:8123/api/services/ev_trip_planner/calculate_trip

sleep 5  # Wait for processing
STATE=$(curl -s http://192.168.1.100:8123/api/states/sensor.ev_trip_distance | jq -r '.state')
echo "Sensor state: $STATE"

# Step 4: Verify
test "$STATE" =~ ^[0-9]+\.?[0-9]*$ && echo "✓ Valid numeric state" || echo "✗ Invalid state"
grep -i "trip.*distance.*calculated" /home/malka/homeassistant/home-assistant.log | tail -3
curl http://192.168.1.100:8123/api/states | jq '.[] | select(.entity_id == "sensor.ev_trip_distance")'

# Step 5: Complete
# If all above pass → Mark [x]
```

### 2. Service Feature

**Task:** Add charging optimization service

**User Journey:**
```bash
# Step 1: Deploy
cp -r custom_components/ev_trip_planner /home/malka/homeassistant/custom_components/
python3 .ralph/scripts/[VERIFY:*] tags + STATE_MATCH ev_trip_planner

# Step 2: Register
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -d '{"domain": "ev_trip_planner", "title": "Charging Service"}' \
  http://192.168.1.100:8123/api/config/config_entries/post

# Step 3: Use - Call service
START_TIME=$(date +%s)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -d '{"vehicle": "tesla", "battery_level": 20}' \
  http://192.168.1.100:8123/api/services/ev_trip_planner/optimize_charging
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "Service response time: ${DURATION}s"

# Step 4: Verify
SERVICE_EXISTS=$(curl http://192.168.1.100:8123/api/services | jq '.[] | select(.domain == "ev_trip_planner" and .service == "optimize_charging")')
test -n "$SERVICE_EXISTS" && echo "✓ Service exists" || echo "✗ Service missing"

test "$DURATION" -lt 30 && echo "✓ Fast response (<30s)" || echo "✗ Slow response"

# Step 5: Complete
# If all above pass → Mark [x]
```

### 3. Device Feature

**Task:** Add vehicle device registry

**User Journey:**
```bash
# Step 1: Deploy
cp -r custom_components/ev_trip_planner /home/malka/homeassistant/custom_components/
python3 .ralph/scripts/[VERIFY:*] tags + STATE_MATCH ev_trip_planner

# Step 2: Register
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -d '{"domain": "ev_trip_planner", "title": "Vehicle Registry"}' \
  http://192.168.1.100:8123/api/config/config_entries/post

# Step 3: Use - Query device
curl http://192.168.1.100:8123/api/devices | jq '.[] | select(.manufacturer | contains("EV Trip"))'

# Step 4: Verify
DEVICE_COUNT=$(curl http://192.168.1.100:8123/api/devices | jq '.[] | select(.manufacturer | contains("EV Trip")) | length')
test "$DEVICE_COUNT" -gt 0 && echo "✓ Devices found ($DEVICE_COUNT)" || echo "✗ No devices"

# Check device entities
ENTITIES=$(curl http://192.168.1.100:8123/api/states | jq ".[] | select(.device_id != null) | length")
test "$ENTITIES" -gt 0 && echo "✓ Device entities exist ($ENTITIES)" || echo "✗ No device entities"

# Step 5: Complete
# If all above pass → Mark [x]
```

---

## 🔄 Integración con RalphLoop

El RalphLoop ejecuta automáticamente este flujo completo:

```
Task Implementation Complete → TASK_COMPLETE Signal
  ↓
Step 1: Deploy to Workshop
  python3 .ralph/scripts/[VERIFY:*] tags + STATE_MATCH <component>
  ↓ If NOT_DEPLOYED → Uncheck [ ] + Retry
  ↓ If DEPLOYED → Continue
  
Step 2: First-Time Registration
  curl -X POST ... /api/config/config_entries/post
  ↓ If Registration Failed → Uncheck [ ] + Retry
  ↓ If Success → Continue
  
Step 3: Functional Usage
  curl tests for sensors/services/devices
  ↓ If Tests Fail → Uncheck [ ] + Retry
  ↓ If Tests Pass → Continue
  
Step 4: Real Environment Verification
  Check states, logs, entities
  ↓ If Verifications Fail → Uncheck [ ] + Retry
  ↓ If All Pass → Mark [x] + Continue
```

---

## 📊 Checklist de Verificación Completa

Antes de marcar cualquier task como [x], verificar:

- [ ] **Deploy Verified**
  - [ ] Component copied to `/config/custom_components/`
  - [ ] `[VERIFY:*] tags + STATE_MATCH` returns "DEPLOYED ✓"

- [ ] **Registration Successful**
  - [ ] Config entry created via REST API
  - [ ] Entry appears in `/api/config/config_entries/entry`
  - [ ] Domain correct: `ev_trip_planner`

- [ ] **Functional Testing Passed**
  - [ ] Sensors return valid values (not "unavailable")
  - [ ] Services respond correctly
  - [ ] Devices appear in registry

- [ ] **Environment Verification**
  - [ ] Logs show initialization messages
  - [ ] Entities registered in system
  - [ ] Config entries active

- [ ] **All Checks Return Success**
  - [ ] No errors in deployment
  - [ ] No failures in registration
  - [ ] No issues in functional testing
  - [ ] No problems in environment verification

**Only if ALL boxes checked → Mark task as [x]**

---

## 💡 Principios Clave

1. **NUNCA** marcar [x] sin ejecutar los 5 pasos completos
2. **SIEMPRE** simular el flujo completo de uso real
3. **SIEMPRE** verificar en entorno REAL, no solo mocks
4. **SIEMPRE** incluir deploy, register, use, verify, complete
5. **SOLO** marcar [x] si todos los pasos pasan

---

## 🚀 Beneficios

- ✅ **Cero Falsos Positivos**: Ninguna task se marca como completada sin verificación REAL completa
- ✅ **Flujo Real Simulado**: Se prueba todo el ciclo de vida del usuario
- ✅ **Despliegue Incluido**: Cada task incluye su propio despliegue
- ✅ **Configuración Real**: Se prueba la configuración inicial
- ✅ **Uso Funcional**: Se prueban todas las funcionalidades
- ✅ **Verificación Total**: Todos los aspectos verificados en HA real

---

**Última Actualización**: 2026-03-20  
**Versión**: 1.0  
**Enfoque**: Complete User Journey BDD  
**Estado**: Listo para implementar
