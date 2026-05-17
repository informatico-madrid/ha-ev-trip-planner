# REGLAS DE NEGOCIO — DOMINIO EV TRIP PLANNER

> **Documento de dominio para agentes IA** — Consulta este archivo para entender las reglas de negocio, cálculos, y comportamiento del sistema.
> **Tipo**: Cold memory (cargar bajo demanda cuando se necesitan detalles de dominio).
> **Creado**: 2026-05-14 | **Última actualización**: 2026-05-16

---

## Tabla de Contenidos

| # | Sección | Descripción |
|---|---------|-------------|
| 1 | [Acceso a Staging](#1-acceso-a-staging) | URLs y credenciales del entorno |
| 2 | [Glosario de Términos](#2-glosario-de-términos) | Definiciones de SOC, SOH, kWh, ventanas, etc. |
| 3 | [Parámetros de Vehículo](#3-parámetros-de-vehículo) | Configuración típica y capacidades |
| 4 | [Cálculos de Energía](#4-cálculos-de-energía) | Fórmulas para SOC, SOH, energía disponible |
| 5 | [Regla: Ventanas de Carga](#5-regla-ventanas-de-carga) | Cómo se calculan y comporta las ventanas |
| 6 | [Regla: Propagación de Déficit](#6-regla-propagación-de-déficit) | Déficit entre ventanas hacia atrás |
| 7 | [Regla: SOC Cap Dinámico](#7-regla-soc-cap-dinámico) | Limitación inteligente de carga |
| 8 | [EMHASS y Perfil Diferible](#8-emhass-y-perfil-diferible) | Integración con EMHASS |
| 9 | [Casos de Uso Documentados](#9-casos-de-uso-documentados) | Ejemplos reales del sistema |

---

## 1. Acceso a Staging

| Entorno | URL | Credenciales |
|---------|-----|--------------|
| **Staging** (Docker) | http://localhost:8124/ | admin / admin123 |
| **E2E** (tests) | http://localhost:8123/ | (sin auth) |

---

## 2. Glosario de Términos

| Término | Abreviatura | Definición |
|---------|-------------|------------|
| **State of Charge** | SOC | Porcentaje de energía actual en la batería (0-100%) |
| **State of Health** | SOH | Porcentaje de degradación de la batería respecto a fábrica (100% = nueva) |
| **Battery Capacity** | kWh | Capacidad total de la batería en kilovatios-hora |
| **Charging Window** | ventana | Período de tiempo disponible para cargar antes de un viaje |
| **Deficit** | déficit | Energía que falta por cargar en una ventana |
| **SOC Cap** | soc_cap | Límite máximo de SOC que el sistema permite cargar |
| **t_base** | t_base | Parámetro configurable (6-48h) que controla cuándo se aplica soc_cap |
| **EMHASS** | EMHASS | Sistema de optimización de energía de Home Assistant |
| **Deferrable Load** | carga diferible | Carga que puede programarse para ejecutarse en un momento específico |

### Constantes del Sistema

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `DEFAULT_SOC_BASE` | 35% | Sweet spot mínimo de la batería |
| `DEFAULT_T_BASE` | 24h | Valor por defecto para t_base |
| `MIN_T_BASE` | 6h | Valor mínimo para t_base |
| `MAX_T_BASE` | 48h | Valor máximo para t_base |
| `RETURN_BUFFER_HOURS` | 4h | Buffer entre salida de un viaje y carga del siguiente |

---

## 3. Parámetros de Vehículo

### Configuración Típica (Staging Vehicle 1)

| Parámetro | Valor | Unidad |
|-----------|-------|--------|
| `battery_capacity_kwh` | 28 | kWh |
| `state_of_health_percent` | 87 | % |
| `state_of_charge_percent` | 31 | % |
| `safety_margin_percent` | 10 | % |
| `charging_power_kw` | 3.4 | kW |
| `consumption_kwh_per_km` | 0.18 | kWh/km |
| `planning_horizon_days` | 7 | days |

### Estados del Vehículo

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `is_home` | `true` | El vehículo está en casa |
| `plugged_in` | `true` | Conectado al cargador |
| `charge_limit_soc` | 100 | Sin Dynamic SOC capping activo |

---

## 4. Cálculos de Energía

### Capacidad Real (Given SOH)

```
capacidad_real = battery_capacity_kwh × (soh_percent / 100)
```

### Energía Actual (Given SOC)

```
energia_actual = capacidad_real × (soc_percent / 100)
```

### Energía Disponible Segura (Given Safety Margin)

```
energia_segura = energia_actual × (1 - safety_margin_percent / 100)
```

### Energía para Viaje

```
energia_viaje = distancia_km × consumo_kwh_per_km
```

### SOC Post-Viaje

```
soc_post_viaje = (energia_actual - energia_viaje) / capacidad_real × 100
```

---

## 5. Regla: Ventanas de Carga

### Principio Fundamental

> La **ventana de carga** representa una **oportunidad**, no carga obligatoria. Indica el período disponible durante el cual el vehículo podría estar cargándose.

### Reglas de Comportamiento

| # | Regla | Descripción |
|---|-------|-------------|
| 5.1 | Carga efectiva vs Ventana | La carga efectiva se compacta al **final** de la ventana |
| 5.2 | Primer viaje en slot 0 | El primer viaje siempre empieza en el slot actual (ahora) |
| 5.3 | Ventana termina en salida | La ventana siempre termina en el slot de salida del viaje |
| 5.4 | Buffer entre viajes | Viajes 2+ empiezan con `return_buffer_hours = 4h` tras salida anterior |

### Fórmula de Ventana

```
ventana_horas = trip_departure_time - ahora
horas_carga_necesarias = energia_kwh / charging_power_kw  (redondeado arriba)
es_suficiente = ventana_horas >= horas_carga_necesarias
```

### Cálculo de EMHASS

| Parámetro EMHASS | Fórmula |
|-------------------|---------|
| `def_start_timestep` | Slot donde empieza la ventana |
| `def_end_timestep` | Slot donde termina (hora de salida) |
| `def_total_hours` | `ceil(kwh_necesarios / charging_power_kw)` |
| `charging_start` | `def_end_timestep - def_total_hours` |
| `charging_end` | `def_end_timestep` |

---

## 6. Regla: Propagación de Déficit

### Principio

Cuando una ventana de carga **no tiene suficiente capacidad** para cubrir la energía necesaria:

1. El déficit se propaga a la ventana inmediatamente **anterior**
2. Si esa ventana también tiene déficit, se propaga recursivamente hacia atrás
3. El límite es la **primera ventana de carga**
4. Si la primera ventana también tiene déficit: se carga lo máximo posible y se **acepta el déficit restante**

### Algoritmo

```
déficit(Ventana_i) = max(0, energía_necesaria(Ventana_i) - capacidad_disponible(Ventana_i))

SI déficit(Ventana_i) > 0 ENTONCES:
    déficit(Ventana_{i-1}) += déficit(Ventana_i)
```

### Casos de Borde

| Caso | Comportamiento |
|------|-----------------|
| Una sola ventana con déficit | Se carga lo máximo posible y se acepta déficit |
| Todas las ventanas con déficit | La primera ventana absorbe todo lo que puede |
| Sin déficit | El plan se completa sin problemas |

---

## 7. Regla: SOC Cap Dinámico

### Problema que Resuelve

Evitar que la batería se cargue a un SOC innecesariamente alto cuando el próximo viaje no lo requiere.

### Principio

> **No cargar de más:** Si con el 70% SOC actual el vehículo ya tiene suficiente energía para el próximo viaje, no tiene sentido cargar al 100%.

### Fórmula

```
risk = t_hours × (soc_post_trip - 35) / 65
SI risk <= 0: soc_cap = 100.0  # Batería por debajo del sweet spot
soc_cap = 35 + 65 × (1 / (1 + risk / t_base))
# soc_cap clampado al rango [35.0, 100.0]
```

### Parámetros

| Parámetro | ¿Configurable? | Descripción |
|-----------|----------------|-------------|
| `t_base` | ✅ **SÍ** | Ventana de referencia (6-48h, default 24). Controla cuándo se aplica el cap. |
| `t_hours` | ❌ NO | Horas hasta el próximo viaje |
| `soc_post_trip` | ❌ NO | SOC proyectado después del viaje |
| 35 (`DEFAULT_SOC_BASE`) | ❌ NO | Constante interna = sweet spot mínimo |

### Efecto de t_base

| t_base | Efecto |
|--------|--------|
| **6h** | Modo agresivo: caps más estrictos, menos carga permitida |
| **24h** | Balance entre protección y flexibilidad |
| **48h** | Modo relajado: permite más tiempo a alto SOC |

### Comportamiento del soc_cap

| t_hours | soc_cap | Efecto |
|---------|---------|--------|
| 0 (inmediato) | ~100% | Carga completa |
| 6h | ~95% | Carga casi completa |
| 24h | ~80% | Carga moderada |
| 72h | ~60% | Carga mínima necesaria |
| 168h (7 días) | ~35% | Solo mínimo para cubrir viaje |

### Casos de Borde

| Caso | Comportamiento |
|------|----------------|
| Viaje inmediato | soc_cap = 100% |
| SOC post-viaje < 35% | soc_cap = 100% directamente |
| t_base = 6h | Caps muy estrictos |
| t_base = 48h | Caps relajados |
| SOC actual > soc_cap | No se permite carga adicional |

---

## 8. EMHASS y Perfil Diferible

### Concepto

El perfil diferible es un array de **168 slots** (7 días × 24 horas) que indica cuándo y cuánto debe cargar el vehículo.

### Estructura del Perfil

```
Posición:  0 ... 44 | 45  46  47  48  49  50 | 51 ... 167
Valor:     0.0      | 7400 7400 7400 7400 7400 | 0.0
                      ^^^^^^^^^^^^^^^^^^^^^^^^
                      Solo 6 slots con carga
```

### Parámetros Clave

| Parámetro | Descripción |
|-----------|-------------|
| `def_total_hours` | Horas efectivas de carga |
| `p_deferrable_nom` | Potencia nominal de carga (kW × soc_cap/100) |
| `soc_cap` | Límite dinámico de SOC para este viaje |

---

## 9. Casos de Uso Documentados

### Caso 1: Viaje de 30km con SOC bajo

**Situación:** Vehículo con SOC 31%, viaje de 30km en ~11 horas.

**Problema:** SOC post-viaje sería 8.82% (por debajo del safety margin del 10%).

**Solución:** El sistema detecta que necesita cargar 0.65 kWh extra y planifica la ventana accordingly.

### Caso 2: SOC Cap que Limita Carga

**Situación:** Vehículo al 75% SOC, viaje de 50km en 24h.

**Resultado:** `soc_cap ≈ 81.93%` — el sistema solo permite cargar hasta ese nivel.

### Caso 3: Viaje a 3 días con déficit

**Situación:** Vehículo con 50% SOC, viaje de 200km en 72h.

**Resultado:** `soc_post_trip < 0` → `risk <= 0` → `soc_cap = 100%` (se necesita toda la carga posible).

---

## Referencias

| Archivo | Descripción |
|---------|-------------|
| [`calculations/core.py`](custom_components/ev_trip_planner/calculations/core.py) | `calculate_dynamic_soc_limit()` — fórmula de SOC cap |
| [`calculations/windows.py`](custom_components/ev_trip_planner/calculations/windows.py) | `calculate_charging_window_pure()` — cálculo de ventanas |
| [`const.py`](custom_components/ev_trip_planner/const.py) | Constantes del sistema |
| [`translations/`](custom_components/ev_trip_planner/translations/) | Traducciones español/inglés |

---

## Acceso a Staging

**URL:** http://localhost:8124/
**Credenciales:** admin / admin123

---

## Vehículo 1: Configuración Original (Staging)

### Parámetros Fijos (ConfigEntry)

| Parámetro | Valor | Unidad |
|-----------|-------|--------|
| `battery_capacity_kwh` | 28 | kWh |
| `state_of_health_percent` | 87 | % |
| `state_of_charge_percent` | 31 | % |
| `safety_margin_percent` | 10 | % |
| `charging_power_kw` | 3.4 | kW |
| `consumption_kwh_per_km` | 0.18 | kWh/km |
| `planning_horizon_days` | 7 | days |

### Estado Inicial

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `is_home` | `true` | El vehículo está en casa (presencia detectada) |
| `plugged_in` | `true` | El vehículo está conectado al cargador |
| `charge_limit_soc` | 100 | Límite de carga (por defecto, sin Dynamic SOC capping activo) |

---

## Cálculos Derivados (Vehículo 1)

### 1. Capacidad Total de Batería (Given SOH)

```
battery_capacity_kwh × (state_of_health_percent / 100)
= 28 × 0.87
= 24.36 kWh
```

**Capacidad real de la batería** considerando la degradación (SOH = 87%):
- Batería física: 28 kWh
- Capacidad utilizable máxima: **24.36 kWh**

### 2. Capacidad Total Útil (Given SOC)

```
battery_capacity_kwh × (state_of_health_percent / 100) × (state_of_charge_percent / 100)
= 28 × 0.87 × 0.31
= 7.5516 kWh
```

**Capacidad actual disponible en el battery** (SOC = 31%):
- Batería física: 28 kWh
- Capacidad degradada: 24.36 kWh
- SOC actual: 31%
- **Energía actual: 7.55 kWh**

### 3. Capacidad Disponible Segura (Given Safety Margin)

```
[ battery_capacity_kwh × (state_of_health_percent / 100) × (state_of_charge_percent / 100) ]
×
[ 1 - (safety_margin_percent / 100) ]
= 7.5516 × (1 - 0.10)
= 7.5516 × 0.90
= 6.79644 kWh
```

**Capacidad disponible para uso sin bajar del mínimo de seguridad**:
- Safety margin: 10%
- Mínimo SOC práctico: 31% - 10% = 21%
- **Energía utilizable segura: 6.80 kWh**

---

## Resumen de Capacidades (Vehículo 1)

| Métrica | Valor | Cálculo |
|---------|-------|---------|
| **Capacidad nominal** | 28 kWh | (battery_capacity_kwh) |
| **Capacidad real (SOH)** | 24.36 kWh | 28 × 0.87 |
| **Energía actual (SOC)** | 7.55 kWh | 24.36 × 0.31 |
| **Energía mínima segura** | 6.80 kWh | 7.55 × 0.90 |
| **Energía no utilizable** | 0.75 kWh | 7.55 - 6.80 |

---

## Constraints de Carga (Vehículo 1)

### Potencia de Carga

| Parámetro | Valor |
|-----------|-------|
| `charging_power_kw` | 3.4 kW |
| `charging_power_w` | 3400 W |

### Tiempo para cargar 1 kWh

```
1000 / charging_power_kw = 1000 / 3.4 = 294.12 minutos/kWh
```

### Tiempo para cargar de 0% a 100% (28 kWh)

```
28 kWh / 3.4 kW = 8.24 horas
```

### Tiempo para cargar de 31% SOC actual a 100%

```
(28 × 0.69) / 3.4 = 19.32 / 3.4 = 5.68 horas
```

---

## Viaje 1 (Vehículo 1): 30km a las 9:40 (Asumiendo hora actual ~22:50)

### Datos del Viaje

| Parámetro | Valor |
|-----------|-------|
| Hora actual | ~22:50 |
| Hora de salida | 09:40 |
| Distancia | 30 km |
| Consumo | 0.18 kWh/km |

### Cálculos de Energía

```
Energía para el viaje = 30 km × 0.18 kWh/km = 5.4 kWh

Energía actual = 7.55 kWh (SOC 31%)
Energía post-viaje = 7.55 - 5.4 = 2.15 kWh
SOC post-viaje = 2.15 / 24.36 × 100 = 8.82% ← ⚠️ BAJO MÍNIMO
```

**⚠️ PROBLEMA:** Con SOC actual 31%, después del viaje de 30km el SOC sería solo 8.82%, por debajo del safety margin.

### Energía Necesaria para Estar "Seguro"

```
Energía mínima post-viaje = battery_capacity × safety_margin_percent
= 28 kWh × 0.10 = 2.8 kWh (mínimo absoluto)

Pero también necesitamos energía para el viaje:
Energía total = energia_viaje + energia_minima
= 5.4 + 2.8 = 8.2 kWh
```

**Necesitamos cargar:** 8.2 - 7.55 = **0.65 kWh extra** sobre la energía actual.

### Tiempo de Carga Necesario

```
Potencia carga = 3.4 kW = 3400 W

Tiempo para 0.65 kWh = 0.65 / 3.4 = 0.19 horas = 11.5 minutos
Tiempo para 8.2 kWh = 8.2 / 3.4 = 2.41 horas
```

**Si queremos cargar solo lo justo (8.2 kWh):** ~2.4 horas

---

### Análisis: Lo que calcula el código actual

#### Función: `calculate_charging_window_pure()`

Ubicación: [`calculations/windows.py:102-179`](custom_components/ev_trip_planner/calculations/windows.py:102)

**Propósito:** Calcula la ventana de carga disponible y si es suficiente.

**Inputs para Viaje 1:**

| Input | Valor | Fuente |
|-------|-------|--------|
| `trip_departure_time` | 09:40 | Trip departure |
| `hora_regreso` | ~22:50 | Ahora (hora actual) |
| `soc_actual` | 31% | **NO SE USA en este cálculo** |
| `charging_power_kw` | 3.4 kW | ConfigEntry |
| `energia_kwh` | 5.4 kWh | 30km × 0.18 |

**Cálculo paso a paso:**

```
1. inicio_ventana = hora_regreso = 22:50
2. fin_ventana = trip_departure_time = 09:40

3. ventana_horas = fin_ventana - inicio_ventana
   = 09:40 - 22:50 (pasando midnight)
   = 10 horas + 50 minutos
   = 10.83 horas

4. kwh_necesarios = energia_kwh = 5.4 kWh

5. horas_carga_necesarias = kwh_necesarios / charging_power_kw
   = 5.4 / 3.4
   = 1.59 horas → ceil() = 2 horas

6. es_suficiente = ventana_horas >= horas_carga_necesarias
   = 10.83 >= 1.59
   = True ✅
```

**Output del código:**

```python
{
    "ventana_horas": 10.83,        # Horas disponibles para cargar
    "kwh_necesarios": 5.4,         # Energía necesaria para el viaje
    "horas_carga_necesarias": 2,   # Horas necesarias (ceil de 1.59)
    "inicio_ventana": 22:50,       # Cuándo empieza la ventana
    "fin_ventana": 09:40,           # Cuándo termina (hora de salida)
    "es_suficiente": True          # ¿Cabe la carga en la ventana?
}
```

---

#### ⚠️ Lo que el código NO calcula (en esta función)

1. **SOC post-viaje**: No calcula qué SOC tendrás después del viaje
2. **Safety margin violado**: No verifica si quedas por debajo del 10%
3. **Carga completa vs parcial**: Solo verifica si `kwh_necesarios` cabe en la ventana

#### Lo que SÍ hace el código

- Dice "es_suficiente: True" porque 10.83 horas > 1.59 horas
- Pero no dice que después del viaje el SOC será 8.82% (por debajo del safety margin)

---

## Vehículo 2: Test Vehicle (Unit Test)

> **Fuente:** [`tests/integration/test_p_deferrable_matrix_slots.py`](tests/integration/test_p_deferrable_matrix_slots.py)
> Configuración usada para verificar el bug fix de `p_deferrable_matrix`.

### Parámetros Fijos (ConfigEntry)

| Parámetro | Valor | Unidad |
|-----------|-------|--------|
| `vehicle_name` | test_vehicle | - |
| `battery_capacity_kwh` | 50.0 | kWh |
| `kwh_per_km` | 0.18 | kWh/km |
| `planning_horizon_days` | 7 | days (168 slots) |
| `charging_power_kw` | 7.4 | kW |

**EMHASS adapter:** `None` (usa path fallback de `coordinator._generate_mock_emhass_params`)

### Viaje del Vehículo 2: 200km en 51 horas

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `id` | trip_1 | Un solo viaje |
| `status` | active | Viaje activo |
| `tipo` | punctual | Viaje puntual (no recurrente) |
| `datetime` | now + 51h | Salida dentro de 51 horas |
| `kwh` | 44.4 | 6h × 7.4 kW = 44.4 kWh |
| `km` | 200 | Distancia del viaje |

### Parámetros EMHASS Esperados

| Parámetro | Valor | Cálculo |
|-----------|-------|---------|
| `def_start_timestep` | 0 | Ventana empieza ahora (coche en casa) |
| `def_end_timestep` | 51 | Viaje sale en 51 horas |
| `def_total_hours` | 6 | ceil(44.4 / 7.4) = 6 |
| `charging_start` | 45 | 51 - 6 = 45 |
| `charging_end` | 51 | = def_end_timestep |
| `non_zero_count` | 6 | Solo 6 slots de carga |
| `power_watts` | 7400.0 | 7.4 kW × 1000 |

### Estructura de p_deferrable_matrix

```
Posición:  0 .............. 44 | 45  46  47  48  49  50 | 51 .............. 167
Valor:     0.0             0.0 | 7400                7400 | 0.0              0.0
                                ^^^^^^^^^^^^^^^^^^^^^^^^
                                Solo 6 slots con carga
                                (últimas 6 horas antes de salir)
```

### Assertions Verificadas

| # | Assertion | Qué verifica |
|---|---|---|
| 1 | `def_start == 0` | La ventana de carga empieza en hora 0 (coche en casa ahora) |
| 2 | `def_end == 51` | La ventana termina en hora 51 (salida del viaje) |
| 3 | `def_total == 6` | Se necesitan 6 horas de carga |
| 4a | `row[0..44] == 0` | Las 45 posiciones **ANTES** de `charging_start` son 0 |
| 4b | `row[45..50] == 7400.0` | Las 6 posiciones **EN** la ventana tienen potencia de carga |
| 4c | `row[51..167] == 0` | Las 117 posiciones **DESPUÉS** de `charging_end` son 0 |

---

## Reglas de Negocio: Ventanas de Carga

> **Fuente:** [`calculations/`](custom_components/ev_trip_planner/calculations/) — dominio central del sistema de planificación de carga para vehículos eléctricos.

### 1. Ventana de carga ≠ Carga efectiva

La **ventana de carga** representa una **oportunidad de carga**, no carga que efectivamente ocurrirá. Indica el período de tiempo disponible durante el cual un vehículo podría estar cargándose, pero no garantiza que se utilice toda esa ventana.

### 2. La carga efectiva se compacta al final de la ventana

La carga efectiva **siempre se coloca en las últimas horas disponibles** de la ventana. Esto es determinista:

> **Ejemplo:** Si la ventana de carga empieza en el slot `0` y termina en el slot `9` (ventana de 9 horas), y se necesitan 3 horas de carga efectiva, entonces esas 3 horas se asignan a los slots `7`, `8` y `9` (las 3 últimas).

Este patrón asegura que el vehículo se carga lo más tarde posible dentro de la ventana, maximizando la flexibilidad y permitiendo que se aprovechen oportunidades de carga que puedan surgir más cerca de la hora de salida.

### 3. El primer viaje siempre empieza en `0` (ahora)

La ventana de carga del **primer viaje** siempre empieza en el slot `0`, que representa el momento actual. Esto refleja que el primer viaje es la carga inmediata: no hay ventana previa, el vehículo está conectado ahora.

### 4. La ventana siempre termina en el slot de salida del viaje

La ventana de carga **siempre termina en el slot que coincide con la hora de salida** del viaje. La salida actúa como el deadline absoluto: la carga debe completarse antes de ese momento, y el último slot de la ventana es exactamente el slot de salida.

### 5. El segundo viaje y posteriores empiezan con buffer tras la salida del anterior

La ventana de carga de los viajes **2, 3, 4...** empieza en la hora de salida del viaje anterior **+ `return_buffer_hours`** (constante de 4 horas).

> **Ejemplo:** Si el viaje 1 sale a las 08:00, la ventana de carga del viaje 2 empieza a las 12:00 (08:00 + 4h de buffer). El fin de esa ventana es la hora de salida del viaje 2.

Este buffer representa el tiempo mínimo necesario entre que un viaje termina (sale) y el siguiente viaje puede comenzar a cargar — el vehículo está en ruta durante ese lapse.

### 6. El sensor EMHASS publish profile compacta carga al final de la ventana

El sensor `ev_trip_planner_mi_ev_emhass_perfil_diferible_mi_ev` debe tener en su atributo **`matrix`** las posiciones de carga distribuidas así:

- **Cada posición de carga activa** (valor = `potencia_carga_coche_kw`) representa **una hora de carga efectiva**.
- **Todas las posiciones activas se colocan en las últimas slots** de la ventana de carga.
- **El número de posiciones activas** debe ser igual a `horas_carga_necesarias`.
- **Todas las posiciones restantes** (las que no son activas) deben ser **0**.

> **Ejemplo:** Ventana de 9 slots (0-8), `horas_carga_necesarias = 3`, `charging_power_kw = 7.4`.
> Resultado: `[0, 0, 0, 0, 0, 7.4, 7.4, 7.4, 7.4]` — las 3 posiciones finales activas (slots 5, 6, 7 con 7.4 cada una, 0 en el resto).

---

## CASO DE USO: Vehículo en Staging — Datos Reales Actuales

> **Fuente:** Entorno de Staging (Docker, puerto :8124)
> **Fecha de recuperación:** 2026-05-15
> **Contenedor:** `ha-staging` (Up 44+ minutos)
> **URL:** http://localhost:8124/
> **Credenciales:** admin / admin123

### Configuración del Vehículo en Staging

**Nombre del vehículo:** Mi EV
**Entry ID:** `516A4963B0704404BD270C9849FF28EF`

#### Parámetros de Configuración (ConfigEntry Options)

| Parámetro | Valor | Unidad |
|-----------|-------|--------|
| `battery_capacity_kwh` | 28.0 | kWh |
| `charging_power_kw` | 3.4 | kW |
| `kwh_per_km` | 0.18 | kWh/km |
| `safety_margin_percent` | 10 | % |
| `t_base` | 24.0 | horas |

#### Sensores de Estado Actual (Valores en Base de Datos)

| Entidad | Valor Actual | Descripción |
|---------|--------------|-------------|
| `input_number.ev_soc` | 65.0 | SOC configurado (input) |
| `input_number.ev_soh` | 94.0 | SOH configurado (input) |
| `sensor.ev_battery_soc` | 65 | SOC real (template sensor) ← usado por el componente |
| `sensor.ev_health_soh` | 94 | SOH real (template sensor) |
| `input_boolean.ev_charging_sim` | off | Conectado al cargador |
| `sensor.ev_charging_status` | off | Estado de carga |

#### Estado Original del Vehículo (Configuración Inicial Documentada)

| Parámetro | Valor Original | Unidad |
|-----------|----------------|--------|
| `battery_capacity_kwh` | 28 | kWh |
| `state_of_health_percent` | 87 | % |
| `state_of_charge_percent` | 31 | % |
| `safety_margin_percent` | 10 | % |
| `charging_power_kw` | 3.4 | kW |
| `consumption_kwh_per_km` | 0.18 | kWh/km |
| `planning_horizon_days` | 7 | días |

### Viajes Recurrentes Definidos

El sistema tiene **2 viajes recurrentes** activos y **0 viajes puntuales**.

#### Viaje Recurrente 1: `rec_5_xeqnmt` — Domingo, 09:40, 31 km

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `id` | rec_5_xeqnmt | ID interno |
| `tipo` | recurrente | Se repite semanalmente |
| `dia_semana` | "0" | Domingo (formato JS getDay: 0=Domingo) → índice interno 6 |
| `hora` | 09:40 | Hora de salida |
| `km` | 31.0 | Distancia del viaje |
| `kwh` | 5.4 | Energía necesaria (31 × 0.18 ≈ 5.58, redondeado a 5.4) |
| `activo` | true | Viaje activo |
| `descripcion` | — | Sin descripción |

**Estado actual en sensor:** `recurrente`
**EMHASS Index sensor:** `sensor.ev_trip_planner_mi_ev_emhass_index_for_rec_5_xeqnmt`

#### Viaje Recurrente 2: `rec_1_fy4pfk` — Lunes, 21:40, 30 km

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `id` | rec_1_fy4pfk | ID interno |
| `tipo` | recurrente | Se repite semanalmente |
| `dia_semana` | "1" | Lunes (formato JS getDay: 1=Lunes) → índice interno 0 |
| `hora` | 21:40 | Hora de salida |
| `km` | 30.0 | Distancia del viaje |
| `kwh` | 5.4 | Energía necesaria (30 × 0.18 = 5.4) |
| `activo` | true | Viaje activo |
| `descripcion` | — | Sin descripción |

**Estado actual en sensor:** `recurrente`
**EMHASS Index sensor:** `sensor.ev_trip_planner_mi_ev_emhass_index_for_rec_1_fy4pfk`

### Resumen del Planificador (Sensores Actuales)

| Entidad | Valor | Descripción |
|---------|-------|-------------|
| `sensor.ev_trip_planner_mi_ev_ev_trip_planner_recurring_trips_count` | 2 | Viajes recurrentes activos |
| `sensor.ev_trip_planner_mi_ev_ev_trip_planner_punctual_trips_count` | 0 | Viajes puntuales |
| `sensor.ev_trip_planner_mi_ev_ev_trip_planner_trips_list` | `['rec_5_xeqnmt', 'rec_1_fy4pfk']` | Lista de viajes |
| `sensor.ev_trip_planner_mi_ev_ev_trip_planner_next_trip` | rec_5_xeqnmt | Próximo viaje (Domingo 09:40) |
| `sensor.ev_trip_planner_mi_ev_ev_trip_planner_next_deadline` | unknown | Próximo deadline (no calculado) |
| `sensor.ev_trip_planner_mi_ev_ev_trip_planner_hours_needed_today` | 0.0 | Horas de carga necesarias hoy |
| `sensor.ev_trip_planner_mi_ev_ev_trip_planner_kwh_needed_today` | 0.0 | kWh necesarios hoy |
| `sensor.ev_trip_planner_mi_ev_emhass_perfil_diferible_mi_ev` | ready | Estado del perfil EMHASS |

### Diagrama Semanal de Viajes

```
Semaña Tipo: Viajes Recurrentes en Staging

Domingo dia 0 (JS getDay=0):
  09:40 → Viaje rec_5_xeqnmt (31 km, 5.4 kWh)

Lunes dia 1 (JS getDay=1):
  21:40 → Viaje rec_1_fy4pfk (30 km, 5.4 kWh)

Martes a Sábado:
  Sin viajes definidos
```

**Patrón semanal:**
- **Domingo 09:40:** Viaje de 31 km (trabajo/mañana) — `dia_semana: "0"` (JS getDay)
- **Lunes 21:40:** Viaje de 30 km (noche/regreso) — `dia_semana: "1"` (JS getDay)
- **Martes a Sábado:** Sin viajes definidos

### Cálculos Derivados con Datos Actuales de Staging

#### Con SOC real del sensor (65%) y SOH (94%):

```
Capacidad real (SOH 94%) = 28 × 0.94 = 26.32 kWh
Energía actual (SOC 65%) = 26.32 × 0.65 = 17.11 kWh
Energía segura (margin 10%) = 17.11 × 0.90 = 15.40 kWh
Mínimo absoluto (10%) = 28 × 0.10 = 2.8 kWh
```

#### Rango estimado calculado:

> El rango estimado correcto se calcula así:
>
> ```
> Rango = Energía actual / consumo_kwh_per_km
>       = (capacidad_real × SOC) / consumo
>       = (26.32 × 0.65) / 0.18
>       = 17.11 / 0.18
>       = 95.06 km
> ```
>
> El valor de **95 km** es el rango estimado REAL con SOC=65% y SOH=94%.

```
Rango estimado real = 95 km
```

#### Energía necesaria para cada viaje:

| Viaje | Distancia | Energía | Energía post-viaje | SOC post-viaje (aprox) | ¿Seguro? |
|-------|-----------|---------|-------------------|------------------------|----------|
| rec_5_xeqnmt | 31 km | 5.4 kWh | 17.11 - 5.4 = 11.71 kWh | ~44.5% | ✅ SÍ |
| rec_1_fy4pfk | 30 km | 5.4 kWh | Depende de carga previa | Depende de carga | Depende |

**Análisis:** Con SOC actual del 65%, el vehículo tiene suficiente energía para ambos viajes sin quedar por debajo del safety margin.

#### Tiempo de carga necesario:

```
Para 5.4 kWh a 3.4 kW = 5.4 / 3.4 = 1.59 horas ≈ 1 hora 35 minutos
```

#### Ventana de carga para rec_5_xeqnmt (Domingo 09:40):

> **Momento actual:** Viernes 15 de mayo de 2026, 19:43

```
Viernes 19:43 → Domingo 09:40 = 37h 57m = 37.95 horas
  - Horas necesarias: ceil(5.4 / 3.4) = 2 horas
  - es_suficiente: 37.95 >= 2 = True ✅

Hay suficiente tiempo de carga disponible (37.95 horas vs 2 horas necesarias).
```

#### Ventana de carga para rec_1_fy4pfk (Lunes 21:40):

```
Viernes 19:43 → Lunes 21:40 = 73h 57m = 73.95 horas
  - Horas necesarias: ceil(5.4 / 3.4) = 2 horas
  - es_suficiente: 73.95 >= 2 = True ✅

Hay suficiente tiempo de carga disponible (73.95 horas vs 2 horas necesarias).
```

### Fuentes de Datos

| Fuente | Archivo/Entidad | Uso |
|--------|-----------------|-----|
| Config Entry | `.storage/core.config_entries` | Configuración del vehículo (`soc_sensor: sensor.ev_battery_soc`) |
| Viajes | `.storage/ev_trip_planner_mi_ev` | Viajes recurrentes y puntuales |
| Sensores | `.storage/core.restore_state` | Valores actuales de sensores |
| Entidades | `.storage/core.entity_registry` | Registro de entidades del componente |
| Configuration | `configuration.yaml` (contenedor) | input_number + template sensors |

## Regla de Negocio: Cálculo de Deadline para Viajes Recurrentes en el Día Actual

### Problema Detectado (Bug m404-saturday-deadline)

Cuando el día actual coincide con el día del viaje recurrente (ej: hoy es sábado y el viaje es sábado), el sistema debe verificar si la hora del viaje ya ha pasado o no:

- **Si la hora del viaje NO ha pasado aún**: el deadline es HOY (el viaje es el "próximo" en la cola)
- **Si la hora del viaje YA ha pasado**: el deadline es la próxima semana (el viaje se mueve al final de la serie)

### Implementación

Función: [`_calculate_deadline()`](custom_components/ev_trip_planner/emhass/load_publisher.py:271) en `load_publisher.py`

```python
# Cuando target_day == now_day (mismo día de la semana)
if delta_days == 0:
    if deadline_today < now:
        delta_days = 7  # Hora ya pasó → siguiente semana
    # else: hora no ha pasado → delta_days = 0, deadline es HOY
```

### Impacto en el Sensor EMHASS

El sensor EMHASS (`ev_trip_planner_mi_ev_emhass_perfil_diferible_mi_ev`) ordena los viajes por `def_start_timestep`. Si el viaje de HOY tiene un deadline de la próxima semana (`def_start_timestep ≈ 168`), aparecerá **ÚLTIMO** en lugar de **PRIMERO**.

Con el fix correcto:
- Trip de sábado a las 11:50 con ahora = 09:26 → `def_start_timestep ≈ 2.4` (primer viaje)
- El EMHASS optimiza la carga para el viaje más próximo primero

### Test de Verificación

Archivo: [`tests/integration/test_saturday_deadline_bug.py`](tests/integration/test_saturday_deadline_bug.py)

```python
# Cuando hoy es sábado 09:26 y el trip es sábado 11:50
# El deadline debe ser HOY (no next Saturday)
assert hours_until_deadline < 24  # ~2.4 horas, no ~170 horas
```

---

## Regla de Negocio: Propagación del Déficit entre Ventanas de Carga

### Problema que Resuelve

Cuando una ventana de carga **no tiene suficiente capacidad** para cubrir la energía necesaria (déficit), es necesario determinar cómo se cubre ese déficit.

### Regla: Propagación Recursiva Hacia Ventanas Anteriores

Cuando existe déficit en una ventana de carga:

1. **El déficit se propaga a la ventana inmediatamente anterior** (la ventana de carga del viaje previo en la cadena)
2. **Si la ventana anterior también tiene déficit**, el déficit剩余 se propaga a la siguiente ventana anterior
3. **El proceso se repite** de forma recursiva hacia atrás, ventana por ventana
4. **El límite es la primera ventana de carga** (primer viaje en la cadena temporal)

### Comportamiento en la Primera Ventana

Si la **primera ventana de carga** también tiene déficit después de toda la propagación:

- Se carga **todo lo que la ventana permita** (carga máxima posible)
- **El déficit restante se acepta** como estado final del plan
- No hay más ventanas hacia las cuales propagar

### Ejemplo Ilustrativo

```
Ventana 1 (viaje más lejano) ──deficit──► Ventana 2 ──deficit──► Ventana 3 (próximo viaje)
     │                                │                              │
     │◄────── propagación ───────────┘                              │
     │                                                              │
     └──────────────────── deficit final ──────────────────────────►│
                                                                       │
                                                          (si hay déficit, se acepta)
```

### Implementación Esperada

| Paso | Acción |
|------|--------|
| 1 | Calcular déficit de la ventana N |
| 2 | Si déficit > 0, propagar a ventana N-1 |
| 3 | Recalcular capacidad disponible en ventana N-1 |
| 4 | Si nuevo déficit > 0, propagar a ventana N-2 |
| 5 | Repetir hasta ventana 1 |
| 6 | En ventana 1, cargar lo máximo posible y aceptar déficit restante |

### Notación Formal

```
déficit(Ventana_i) = max(0, energía_necesaria(Ventana_i) - capacidad_disponible(Ventana_i))

déficit(Ventana_i) > 0 → déficit(Ventana_{i-1}) += déficit(Ventana_i)
```

### Casos de Borde

| Caso | Comportamiento |
|------|----------------|
| Una sola ventana con déficit | Se carga lo máximo posible y se acepta el déficit |
| Todas las ventanas con déficit acumulado | La primera ventana absorbe todo lo que puede |
| Sin déficit en ninguna ventana | El plan se completa sin problemas |

---

## Regla de Negocio: SOC Cap Dinámico (Dynamic SOC Capping)

### Problema que Resuelve

Evitar que la batería se cargue a un SOC innecesariamente alto cuando el próximo viaje no lo requiere. La batería solo debe cargarse lo suficiente para cubrir el viaje más próximo, minimizando ciclos de carga y desgaste.

### Principio Fundamental

> **No cargar de más:** Si con el 70% SOC actual el vehículo ya tiene suficiente energía para el próximo viaje, no tiene sentido cargar al 100%.

### Fórmula de Cálculo

```
risk = t_hours * (soc_post_trip - 35) / 65
if risk <= 0: return 100.0  # Batería por debajo del sweet spot — sin riesgo
soc_cap = 35 + 65 * (1 / (1 + risk / t_base))
# soc_cap clampado siempre al rango [35.0, 100.0]
```

### Parámetros

| Parámetro | ¿Configurable? | Descripción |
|-----------|----------------|-------------|
| `t_base` | ✅ **SÍ** (usuario) | Ventana de referencia para el cálculo de riesgo. Rango: **6-48 horas** (default: 24). |
| `t_hours` | ❌ NO (interno) | Horas hasta el próximo viaje. |
| `soc_post_trip` | ❌ NO (interno) | SOC proyectado después del viaje (calculado: SOC actual - energía del viaje). |
| 35 (`DEFAULT_SOC_BASE`) | ❌ NO (constante) | Sweet spot mínimo de la batería (35%). Valor fijo interno. |
| `risk` | ❌ NO (calculado) | Factor de riesgo intermedia. No configurable. |
| `soc_cap` | ❌ NO (resultado) | Límite máximo de SOC permitido. Resultado en rango [35%, 100%]. |

### ¿Qué es `t_base` y por qué 6-48 horas?

`t_base` define **cuánto tiempo estás dispuesto a mantener la batería a alto SOC antes de que sea perjudicial**. Es un "factor de paciencia" que controla cuándo el sistema empieza a limitar la carga.

| t_base | Comportamiento |
|--------|----------------|
| **6 horas** | 🏃 **Modo agresivo**: Si la batería está a alto SOC más de 6 horas, se aplica un cap más estricto. Útil si sales siempre pronto. |
| **24 horas** (default) | ⚖️ **Modo equilibrado**: Balance entre no cargar de más y tener flexibilidad. |
| **48 horas** | 🐢 **Modo relajado**: Permite mantener la batería a alto SOC por casi 2 días sin restricción. |

**Analogía:** Imagina que `t_base` es como el tiempo que estás dispuesto a esperar antes de cargar el teléfono. Si tienes t_base=6h y lo pones a charger a las 10pm para un viaje a las 8am (10h de espera), el sistema sees que la batería estará a alto SOC por más de 6h → aplica un cap más bajo para proteger la batería. Con t_base=48h, esas 10h son menos problemáticas y se permite cargar más.

### Comportamiento del soc_cap

| t_hours (horas hasta viaje) | risk | soc_cap | Efecto |
|----------------------------|------|---------|--------|
| 0 (viaje inmediato) | ~0 | ~100% | Carga completa permitida |
| 6 | bajo | alto (ej: 95%) | Carga casi completa |
| 24 | medio | medio (ej: 80%) | Carga moderada |
| 72 | alto | bajo (ej: 60%) | Carga mínima necesaria |
| 168 (7 días) | muy alto | ~35% | Solo mínimo para cubrir viaje |

### Ejemplo Illustrativo 1: Viaje Corto Inmediato

**Datos de entrada:**
- Batería: 50 kWh
- SOC actual: 50% → 25 kWh disponibles
- Viaje: 5 km (consumo 0.18 kWh/km)
- Energía para viaje: 5 × 0.18 = 0.9 kWh
- SOC post-viaje: (25 - 0.9) / 50 × 100 = 48.2%
- t_hours: 0.5 (30 minutos hasta el viaje)
- t_base: 24 horas (default)

**Cálculo:**
```
risk = 0.5 * (48.2 - 35) / 65 = 0.5 * 13.2 / 65 = 0.1015
# risk > 0, aplicamos fórmula completa
soc_cap = 35 + 65 * (1 / (1 + 0.1015 / 24))
soc_cap = 35 + 65 * (1 / (1 + 0.00423))
soc_cap = 35 + 65 * 0.9958
soc_cap ≈ 99.7%  →  redondeado a 100%
```

**Resultado:** Viaje muy próximo → soc_cap ≈ 100% → se permite cargar casi todo lo que la ventana permita.

---

### Ejemplo Illustrativo 2: Viaje Largo en 3 días

**Datos de entrada:**
- Batería: 50 kWh
- SOC actual: 50% → 25 kWh disponibles
- Viaje: 200 km (consumo 0.18 kWh/km)
- Energía para viaje: 200 × 0.18 = 36 kWh
- SOC post-viaje: (25 - 36) / 50 × 100 = -22% (físicamente imposible → se trata como 0%)
- t_hours: 72 (3 días)
- t_base: 24 horas

**Cálculo:**
```
risk = 72 * (0 - 35) / 65 = 72 * (-35) / 65 = -38.77
# risk <= 0 → retorna 100.0 directamente (batería por debajo del sweet spot)
soc_cap = 100%
```

**Resultado:** Déficit de energía → soc_cap = 100% (no hay capping que aplicar, se necesita toda la carga posible).

---

### Ejemplo Illustrativo 3: Viaje Moderado en 48 horas

**Datos de entrada:**
- Batería: 60 kWh
- SOC actual: 65% → 39 kWh disponibles
- Viaje: 150 km → 27 kWh necesarios
- SOC post-viaje: (39 - 27) / 60 × 100 = 20%
- t_hours: 48
- t_base: 24

**Cálculo:**
```
risk = 48 * (20 - 35) / 65 = 48 * (-15) / 65 = -11.08
# risk <= 0 → retorna 100.0
soc_cap = 100%
```

**Energía a cargar:**
```
kWh_a_cargar = (soc_cap - soc_actual) / 100 * capacidad
kWh_a_cargar = (100 - 65) / 100 * 60 = 21 kWh
```

**Resultado:** SOC post-viaje bajo → risk negativo → soc_cap = 100% → se permite carga completa.

---

### Ejemplo Illustrativo 4: Viaje que NO requiere carga completa

**Datos de entrada:**
- Batería: 60 kWh
- SOC actual: 75% → 45 kWh disponibles
- Viaje: 50 km → 9 kWh necesarios
- SOC post-viaje: (45 - 9) / 60 × 100 = 60%
- t_hours: 24
- t_base: 24

**Cálculo:**
```
risk = 24 * (60 - 35) / 65 = 24 * 25 / 65 = 9.23
# risk > 0, aplicamos fórmula completa
soc_cap = 35 + 65 * (1 / (1 + 9.23 / 24))
soc_cap = 35 + 65 * (1 / (1 + 0.385))
soc_cap = 35 + 65 * 0.722
soc_cap = 81.93%
```

**Interpretación:**
- SOC actual: 75%
- soc_cap: 81.93%
- El sistema SOLO permitirá cargar hasta el 81.93%
- Energía a cargar: (81.93 - 75) / 100 × 60 = 4.16 kWh

**Resultado:** Con SOC 75% y viaje en 24h, no es necesario cargar al 100%. El cap dinámico evita sobrecargar.

---

### Relación entre soc_cap y energía de carga

```
P_deferrable_nom = charging_power_kw * (soc_cap / 100)
def_total_hours = kwh_necesarios / charging_power_kw * (soc_cap / 100)
```

| Parameter | Con soc_cap = 100% | Con soc_cap = 81.93% |
|-----------|--------------------|-----------------------|
| `P_deferrable_nom` | 7.4 kW | 6.06 kW |
| `def_total_hours` | 1.5 h | 1.23 h |

---

### Casos de Borde

| Caso | Comportamiento |
|------|----------------|
| Viaje inmediato (t_hours ≈ 0) | risk ≈ 0 → soc_cap = 100%, carga completa |
| SOC post-viaje < 35% | risk negativo → soc_cap = 100% directamente |
| Viaje a 7 días (168h) | soc_cap → 35% (mínimo clamped) |
| SOC actual > soc_cap | No se permite carga adicional |
| t_base = 6h (muy pequeño) | Caps más estrictos, menos carga permitida |
| t_base = 48h (muy grande) | Caps más relajados, más carga permitida |
| Sin viajes definidos | El sistema no aplica soc_cap dinámico |
