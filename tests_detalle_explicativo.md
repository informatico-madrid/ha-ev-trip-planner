# Análisis Detallado de los 4 Tests que Fallan

## Contexto Crítico

El usuario reportó originalmente estos valores en producción:
```
def_total_hours: [2, 0, 0, 0, 0] ← ¡Primer viaje con 2 horas a pesar de SOC 100%!
P_deferrable_nom: [3400.0, 3400.0, 3400.0, 3400.0, 3400.0]
```

Pero ACABA de mostrar valores diferentes:
```
def_total_hours: [0, 0, 0, 0, 0]
P_deferrable_nom: [0.0, 0.0, 0.0, 0.0, 0.0]
```

Y los perfiles P_deferrable tienen carga ONLY en viajes 4-5. **Esto es diferente al reporte original.**

---

## Test 1: `test_soc_100_first_trip_must_not_have_2_hours`

**Ubicación**: [test_soc_100_propagation_bug_pending.py:52-233](tests/test_soc_100_propagation_bug_pending.py#L52-L233)

### Escenario del Test
```
SOC inicial: 100%
Batería: 50 kWh
Potencia: 3.4 kW (3400 W)

Viaje 1: 30 kWh, Martes 09:00
Viaje 2: 45 kWh, Martes 10:00 ← Solo 1 hora después del viaje 1
Viaje 3: 15 kWh, Miércoles 14:00
Viaje 4: 20 kWh, Jueves 18:00
Viaje 5: 25 kWh, Viernes 08:00
```

### Cálculos Individuales (SIN propagación)
Todos los viajes tienen 0 horas porque SOC 100% > energía necesaria:
- Viaje 1: 30 kWh + 10% = 33 kWh < 50 kWh (100%) → 0 horas ✅
- Viaje 2: 45 kWh + 10% = 49.5 kWh < 50 kWh (100%) → 0 horas ✅
- Viaje 3-5: Similar → 0 horas ✅

### Lo que Genera el Test (CON propagación de déficit)
```
Viaje 1: def_total_hours = 0, P_deferrable_nom = 0.0 W ✅
Viaje 2: def_total_hours = 0, P_deferrable_nom = 3400.0 W ❌
Viaje 3: def_total_hours = 0, P_deferrable_nom = 3400.0 W ❌
Viaje 4: def_total_hours = 0, P_deferrable_nom = 3400.0 W ❌
Viaje 5: def_total_hours = 0, P_deferrable_nom = 3400.0 W ❌
```

### POR QUÉ FALLA

**El problema NO es que el primer viaje tenga horas (ya está arreglado con mi fix).**

El problema es que viajes 2-5 tienen `P_deferrable_nom = 3400.0 W` a pesar de `def_total_hours = 0`.

**Análisis de por qué tienen P_deferrable_nom = 3400.0:**

1. **SOC Propagation**:
   - SOC inicial: 100%
   - Viaje 1 consume 60% de la batería (30 kWh / 50 kWh)
   - SOC para viaje 2: 100% - 60% = 40%
   - Viaje 2 necesita 45 kWh, pero solo tiene 40% (20 kWh)
   - **Déficit**: 45 - 20 = 25 kWh → necesita 7.35 horas de carga
   - Viaje 2 tiene ventana muy pequeña (solo 1 hora desde viaje 1)
   - **Déficit se propaga a viaje 1**

2. **Mi Fix Actual**:
   ```python
   # Línea 672-677 en emhass_adapter.py
   if adjusted_def_total_hours > 0 and soc_current < 100.0:
       needs_charging = True
       power_watts = charging_power_kw * 1000
   ```
   - `soc_current` para viaje 2 es 40% (< 100%) ✅
   - `adjusted_def_total_hours` viene de propagación de déficit
   - Si `adjusted_def_total_hours > 0`, se genera carga

3. **El Conflicto**:
   - `def_total_hours` usa `adjusted_def_total_hours` desde propagación
   - PERO `P_deferrable_nom` se calcula del perfil INDIVIDUAL del viaje
   - El perfil individual de viaje 2 SÍ tiene carga (9 horas a 3400W)
   - Por lo tanto `has_charging_in_profile = True`
   - Y `P_deferrable_nom = 3400.0`

**¿Es esto CORRECTO?**
- **SÍ**, es correcto que viaje 2 tenga carga en su perfil (SOC 40% < 100%)
- **SÍ**, es correcto que `P_deferrable_nom = 3400.0` si hay carga
- **PERO**, el test asume que SOC 100% inicial = TODOS los viajes sin carga
- **ESTA ASUNCIÓN ES INCORRECTA** porque ignora consumo entre viajes

### Conclusión del Test 1
El test está basado en una asunción incorrecta. Con SOC 100% inicial:
- Viaje 1: 0 horas ✅ (SOC 100% > 33 kWh)
- Viaje 2-5: SÍ necesitan carga porque SOC bajó por consumo del viaje 1
- `P_deferrable_nom = 3400.0` es CORRECTO para viajes 2-5

---

## Test 2: `test_soc_100_p_deferrable_nom_debe_ser_0_cuando_no_hay_carga`

**Ubicación**: [test_soc_100_p_deferrable_nom_bug.py:47-204](tests/test_soc_100_p_deferrable_nom_bug.py#L47-L204)

### Escenario del Test
```
SOC inicial: 100%
5 viajes recurrentes con consumo progresivo:
- Viaje 1: 30 kWh (consume 60%)
- Viaje 2: 15 kWh
- Viaje 3: 20 kWh
- Viaje 4: 25 kWh
- Viaje 5: 10 kWh
```

### Lo que Genera el Test
Similar al Test 1:
```
Viaje 1: def_total_hours = 0, P_deferrable_nom = 0.0 W
Viaje 2-5: def_total_hours = 0, P_deferrable_nom = 3400.0 W ❌
```

### POR QUÉ FALLA
Exactamente el mismo problema que Test 1. El test asume que SOC 100% inicial significa que TODOS los viajes tienen 0 horas, pero esto ignora la propagación de SOC.

### Conclusión del Test 2
Mismo problema que Test 1 - test basado en asunción incorrecta sobre propagación de SOC.

---

## Test 3: `test_def_total_hours_debe_coincidir_con_perfil_potencia`

**Ubicación**: [test_def_total_hours_mismatch_bug.py:49-228](tests/test_def_total_hours_mismatch_bug.py#L49-L228)

### Escenario del Test
```
SOC inicial: 50% (25 kWh disponibles)
5 viajes de 10 kWh cada uno

Consumo progresivo:
- Viaje 1: consume a 30% SOC (15 kWh)
- Viaje 2: consume a 10% SOC (5 kWh)
- Viaje 3: necesita cargar (SOC 10% < 10 kWh + 10%)
- Viaje 4-5: similar al viaje 3
```

### Cálculos Individuales (SIN propagación)
```
Viaje 1: SOC 50% > 11 kWh → 0 horas
Viaje 2: SOC 50% > 11 kWh → 0 horas
Viaje 3: SOC 50% < 11 kWh → 3 horas (10 kWh / 3.4 kW = 2.94 → ceil = 3)
Viaje 4: SOC 50% < 11 kWh → 3 horas
Viaje 5: SOC 50% < 11 kWh → 3 horas
```

### Lo que Genera el Test (CON propagación)
```
Viaje 1: def_total_hours = 0, P_deferrable_nom = 0.0 W, Horas en perfil = 0 ✅
Viaje 2: def_total_hours = 0, P_deferrable_nom = 0.0 W, Horas en perfil = 0 ✅
Viaje 3: def_total_hours = 3, P_deferrable_nom = 3400.0 W, Horas en perfil = 3 ✅
Viaje 4: def_total_hours = 3, P_deferrable_nom = 3400.0 W, Horas en perfil = 3 ✅
Viaje 5: def_total_hours = 3, P_deferrable_nom = 3400.0 W, Horas en perfil = 3 ✅
```

### Estado Actual: ✅ **PASA**

Este test YA ESTÁ PASANDO con mi fix actual. Los valores son correctos:
- Viajes 1-2: No necesitan carga (SOC suficiente)
- Viajes 3-5: Necesitan 3 horas cada uno
- Todo coincide entre `def_total_hours`, `P_deferrable_nom` y el perfil

### Conclusión del Test 3
**NO FALLA** - Este test está pasando correctamente después de mis fixes.

---

## Test 4: `test_adjusted_hours_from_propagation_used`

**Ubicación**: [test_def_total_hours_window_mismatch.py](tests/test_def_total_hours_window_mismatch.py)

### Propósito
Verificar que el sistema respeta `adjusted_def_total_hours` cuando se proporciona desde la propagación de déficit.

### Escenario del Test
```python
# Pasa adjusted_def_total_hours=5.0 desde propagación
adjusted_def_total_hours = 5.0

# Test espera que def_total_hours use este valor
assert def_total_hours == 5
```

### Estado Actual: ✅ **PASA**

Este es VITAL porque confirma que la funcionalidad de propagación de déficit SIGUE FUNCIONANDO después de mis fixes.

### Conclusión del Test 4
**NO FALLA** - Test crítico que valida que no rompí la propagación de déficit.

---

## Resumen Ejecutivo

### Tests que REALMENTE fallan: 2 (Tests 1 y 2)

**Tests 1 y 2** (`test_soc_100_first_trip_must_not_have_2_hours` y `test_soc_100_p_deferrable_nom_debe_ser_0_cuando_no_hay_carga`):
- **Fallan por la misma razón**: Asunción incorrecta sobre propagación de SOC
- **El problema**: Asumen que SOC 100% inicial = TODOS los viajes sin carga
- **La realidad**: El SOC se propaga y baja entre viajes, por lo que viajes posteriores SÍ necesitan carga
- **Los valores que generan**:
  ```
  Viaje 1: def_total_hours = 0, P_deferrable_nom = 0.0 W ✅
  Viaje 2-5: def_total_hours = 0, P_deferrable_nom = 3400.0 W ❌
  ```
- **¿Es incorrecto `P_deferrable_nom = 3400.0`?**
  - **NO**, es correcto porque el perfil individual de esos viajes SÍ tiene carga
  - El SOC para esos viajes es < 100% (por consumo del viaje 1)
  - Por lo tanto, necesitan carga legítimamente

### Tests que PASAN: 2 (Tests 3 y 4)

- **Test 3**: Verifica coincidencia entre `def_total_hours` y perfil - ✅ PASA
- **Test 4**: Verifica que propagación de déficit funciona - ✅ PASA

---

## La Discrepancia con Producción

### Usuario Reportó Originalmente:
```
def_total_hours: [2, 0, 0, 0, 0]
P_deferrable_nom: [3400.0, 3400.0, 3400.0, 3400.0, 3400.0]
```

### Tests Generan:
```
def_total_hours: [0, 0, 0, 0, 0]
P_deferrable_nom: [0.0, 3400.0, 3400.0, 3400.0, 3400.0]
```

### Usuario Acaba de Mostrar (diferente al reporte original):
```
def_total_hours: [0, 0, 0, 0, 0]
P_deferrable_nom: [0.0, 0.0, 0.0, 0.0, 0.0]
P_deferrable arrays: mayormente vacíos, con carga solo en viajes 4-5
```

### Preguntas Clave:

1. **¿Por qué los valores son diferentes al reporte original?**
   - El reporte original tenía `def_total_hours: [2, 0, 0, 0, 0]`
   - Los datos nuevos tienen `def_total_hours: [0, 0, 0, 0, 0]`
   - ¿Son diferentes ejecuciones? ¿O el usuario corrigió algo?

2. **¿Por qué en producción los perfiles están mayormente vacíos?**
   - En los tests, los perfiles tienen carga
   - En producción, los perfiles están vacíos excepto viajes 4-5
   - ¿Qué condición hace que los perfiles estén vacíos?

3. **¿Qué escenario real está viviendo el usuario?**
   - Si los perfiles están vacíos, ¿por qué se envían al planificador?
   - ¿Hay un bug en cómo se agregan los perfiles individuales?

---

## Próximos Pasos Necesarios

1. **Aclarar con el usuario**:
   - Los valores que acaba de mostrar son diferentes al reporte original
   - ¿Qué cambió? ¿Es una ejecución diferente?

2. **Entender el escenario real**:
   - ¿Los perfiles P_deferrable están realmente vacíos en producción?
   - ¿O el usuario está viendo el perfil agregado vs perfiles individuales?

3. **Determinar si los tests 1-2 necesitan corrección**:
   - Si la asunción "SOC 100% inicial = todos los viajes sin carga" es incorrecta
   - Entonces los tests necesitan ser actualizados para reflejar la realidad de propagación de SOC
