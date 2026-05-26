# Staging Vehicle Data Snapshot - 2026-05-16

## ⚠️ IMPORTANTE: Fuente de Datos

- **`ConfigEntry Data`** → NO USAR, contiene valores incorrectos/predeterminados
- **`ConfigEntry Options`** → USAR, contiene los valores reales configurados por el usuario

---

## Vehicle Configuration (ConfigEntry)

**Vehicle ID**: `mi_ev`  
**Entry ID**: `516A4963B0704404BD270C9849FF28EF`

### ConfigEntry Options (VALORES REALES CONFIGURADOS)
```json
{
  "battery_capacity_kwh": 28.0,
  "charging_power_kw": 3.4,
  "kwh_per_km": 0.18,
  "safety_margin_percent": 10,
  "soh_sensor": "sensor.ev_health_soh",
  "t_base": 24.0
}
```

### Vehicle Parameters Summary (from Options)
| Parameter | Value | Unit |
|-----------|-------|------|
| Battery Capacity | 28.0 | kWh |
| Charging Power | 3.4 | kW |
| Consumption | 0.18 | kWh/km |
| Safety Margin | 10 | % |
| SOH Sensor | `sensor.ev_health_soh` | % |
| Planning Horizon | 7 | days |

---

## Recurring Trips (5 trips)

### Trip 1: `rec_5_xeqnmt`
| Field | Value |
|-------|-------|
| ID | `rec_5_xeqnmt` |
| Tipo | recurrente |
| Día semana | 1 (Lunes) |
| Hora | 09:30 |
| Distancia | 31.0 km |
| Energía | 5.4 kWh |
| Descripción | (vacía) |
| Activo | true |

### Trip 2: `rec_1_fy4pfk`
| Field | Value |
|-------|-------|
| ID | `rec_1_fy4pfk` |
| Tipo | recurrente |
| Día semana | 3 (Miércoles) |
| Hora | 13:40 |
| Distancia | 30.0 km |
| Energía | 5.4 kWh |
| Descripción | (vacía) |
| Activo | true |

### Trip 3: `rec_2_6hgwk6`
| Field | Value |
|-------|-------|
| ID | `rec_2_6hgwk6` |
| Tipo | recurrente |
| Día semana | 4 (Jueves) |
| Hora | 09:40 |
| Distancia | 30.0 km |
| Energía | 5.7 kWh |
| Descripción | (vacía) |
| Activo | true |

### Trip 4: `rec_2_gh62hm`
| Field | Value |
|-------|-------|
| ID | `rec_2_gh62hm` |
| Tipo | recurrente |
| Día semana | 5 (Viernes) |
| Hora | 09:40 |
| Distancia | 30.0 km |
| Energía | 5.7 kWh |
| Descripción | (vacía) |
| Activo | true |

### Trip 5: `rec_6_c4ngiu`
| Field | Value |
|-------|-------|
| ID | `rec_6_c4ngiu` |
| Tipo | recurrente |
| Día semana | 6 (Sábado) |
| Hora | 11:50 |
| Distancia | 30.0 km |
| Energía | 5.4 kWh |
| Descripción | (vacía) |
| Activo | true |

---

## Trips Summary by Day

| Día | ID Trip | Hora | km | kWh |
|-----|---------|------|-----|-----|
| 1 (Lunes) | `rec_5_xeqnmt` | 09:30 | 31 | 5.4 |
| 3 (Miércoles) | `rec_1_fy4pfk` | 13:40 | 30 | 5.4 |
| 4 (Jueves) | `rec_2_6hgwk6` | 09:40 | 30 | 5.7 |
| 5 (Viernes) | `rec_2_gh62hm` | 09:40 | 30 | 5.7 |
| 6 (Sábado) | `rec_6_c4ngiu` | 11:50 | 30 | 5.4 |

**Missing days**: 0 (Domingo), 2 (Martes)

---

## Raw Storage Data

```json
{
  "version": 1,
  "minor_version": 1,
  "key": "ev_trip_planner_mi_ev",
  "data": {
    "trips": {},
    "recurring_trips": {
      "rec_5_xeqnmt": {
        "id": "rec_5_xeqnmt",
        "tipo": "recurrente",
        "dia_semana": "1",
        "hora": "09:30",
        "km": 31.0,
        "kwh": 5.4,
        "descripcion": "",
        "activo": true
      },
      "rec_1_fy4pfk": {
        "id": "rec_1_fy4pfk",
        "tipo": "recurrente",
        "dia_semana": "3",
        "hora": "13:40",
        "km": 30.0,
        "kwh": 5.4,
        "descripcion": "",
        "activo": true
      },
      "rec_2_6hgwk6": {
        "id": "rec_2_6hgwk6",
        "tipo": "recurrente",
        "dia_semana": "4",
        "hora": "09:40",
        "km": 30.0,
        "kwh": 5.7,
        "descripcion": "",
        "activo": true
      },
      "rec_2_gh62hm": {
        "id": "rec_2_gh62hm",
        "tipo": "recurrente",
        "dia_semana": "5",
        "hora": "09:40",
        "km": 30.0,
        "kwh": 5.7,
        "descripcion": "",
        "activo": true
      },
      "rec_6_c4ngiu": {
        "id": "rec_6_c4ngiu",
        "tipo": "recurrente",
        "dia_semana": "6",
        "hora": "11:50",
        "km": 30.0,
        "kwh": 5.4,
        "descripcion": "",
        "activo": true
      }
    },
    "punctual_trips": {},
    "last_update": "2026-05-16T08:59:32.575043"
  }
}
```

---

## Notes

- **No punctual trips** in the system currently
- Total weekly distance: 31 + 30 + 30 + 30 + 30 = 151 km
- Total weekly energy: 5.4 + 5.4 + 5.7 + 5.7 + 5.4 = 27.6 kWh