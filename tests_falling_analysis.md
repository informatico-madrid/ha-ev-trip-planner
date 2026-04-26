# Análisis de Tests Fallando - 2026-04-26

## Tests que fallan (4 total)

### Test 1: `test_soc_100_first_trip_must_not_have_2_hours`

**Propósito**: Verificar que con SOC 100%, no se programa carga.

**Valores que genera**:
```
Viaje 1: def_total_hours = 0, P_deferrable_nom = 0.0 W
Viaje 2: def_total_hours = 0, P_deferrable_nom = 3400.0 W ❌
Viaje 3: def_total_hours = 0, P_deferrable_nom = 3400.0 W ❌
Viaje 4: def_total_hours = 0, P_deferrable_nom = 3400.0 W ❌
Viaje 5: def_total_hours = 0, P_deferrable_nom = 3400.0 W ❌
```

**Análisis del log**:
```
SOC inicial: 100%
Viaje 1: consume 60% (30 kWh + 10% de 50 kWh)
SOC para viaje 2: 40% (después de consumo del viaje 1)
Viaje 2: kwh=45 kWh, kwh_needed=30.00 (porque SOC=40%)
Perfil del viaje 2: 9 horas con 3400.0W
```

**Problema**: El test asume que con SOC 100% inicial, TODOS los viajes deben tener 0 horas.
**Realidad**: El SOC se propaga y baja entre viajes, por lo que viajes posteriores SÍ necesitan carga.

---

### Test 2: `test_soc_100_p_deferrable_nom_debe_ser_0_cuando_no_hay_carga`

**Propósito**: Verificar que P_deferrable_nom es 0.0 cuando no hay carga.

**Valores que genera**: (similar al Test 1)

---

### Test 3: `test_def_total_hours_debe_coincidir_con_perfil_potencia`

**Propósito**: Verificar que def_total_hours coincide con las horas de carga en el perfil.

**Valores que genera**:
```
Escenario: SOC 50% inicial, 5 viajes de 10 kWh cada

Viaje 1: def_total_hours = 0, P_deferrable_nom = 0.0 W, Horas en perfil = 0 ✅
Viaje 2: def_total_hours = 0, P_deferrable_nom = 0.0 W, Horas en perfil = 0 ✅
Viaje 3: def_total_hours = 3, P_deferrable_nom = 3400.0 W, Horas en perfil = 3 ✅
Viaje 4: def_total_hours = 3, P_deferrable_nom = 3400.0 W, Horas en perfil = 3 ✅
Viaje 5: def_total_hours = 3, P_deferrable_nom = 3400.0 W, Horas en perfil = 3 ✅
```

**Estado**: ❌ FALLA con 6 bugs detectados

**Problema**: El test detecta bugs donde def_total_hours o P_deferrable_nom no coinciden con el perfil.
Este era el bug que reportó el usuario.

---

### Test 4: `test_adjusted_hours_from_propagation_used` ✅ PASA

**Propósito**: Verificar que la propagación de déficit funciona correctamente.

**Valores que genera**:
```
adjusted_def_total_hours = 5.0
def_total_hours = 5 ✅
```

**Estado**: ✅ PASA (Este es VITAL porque prueba la funcionalidad de propagación)

---

## Análisis del Problema

### El usuario reporta:
```
def_total_hours: [0, 0, 0, 0, 0]
P_deferrable_nom: [0.0, 0.0, 0.0, 0.0, 0.0]
```

### Los Tests 1-2 muestran:
```
def_total_hours: [0, 0, 0, 0, 0]
P_deferrable_nom: [0.0, 3400.0, 3400.0, 3400.0, 3400.0]  ❌
```

### Diferencia clave:
- **Usuario**: TODOS los parámetros son 0
- **Tests 1-2**: def_total_hours=0, pero P_deferrable_nom tiene 3400.0

### El problema:
Mi fix actual usa `has_charging_in_profile` para decidir P_deferrable_nom.
El perfil individual de cada viaje SÍ tiene carga (por propagación de consumo),
por lo tanto P_deferrable_nom=3400.0.

Pero el usuario dice que en SU producción, P_deferrable_nom es 0.0 para todos.

### Pregunta clave:
¿Por qué en producción el perfil está vacío pero en los tests tiene carga?

**Hipótesis**: El usuario puede estar viendo el perfil AGREGADO final
(`self._cached_power_profile` que se calcula al final de `async_publish_all_deferrable_loads`),
no los perfiles individuales de cada viaje.

---

## Conclusión

Los Tests 1-2 están fallando porque muestran un escenario que mi fix actual genera:
- Viajes 2-5 con SOC < 100% (por consumo del viaje 1) tienen perfiles con carga
- Por lo tanto P_deferrable_nom=3400.0 (CORRECTO según mi fix)

Pero el usuario reporta que en producción P_deferrable_nom=0.0 para todos.

**Esto sugiere que hay una diferencia entre lo que generan los tests y lo que ve el usuario en producción.**

Posibles causas:
1. El usuario está viendo el perfil agregado, no los perfiles individuales
2. Hay una condición específica en producción que hace que los perfiles estén vacíos
3. Mi fix no está funcionando como esperaba en el escenario real del usuario

Necesito entender qué hace que el perfil esté vacío en producción pero lleno en los tests.
