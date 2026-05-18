#!/usr/bin/env python3
"""
Simulación paso a paso del cálculo de def_total_hours
con los valores REALES del vehículo en staging.

Fecha: 2026-05-15 19:43 UTC
"""

import math
from datetime import datetime, timedelta, timezone

# =============================================================================
# DATOS DE STAGING (confirmados)
# =============================================================================

print("=" * 80)
print("SIMULACIÓN: Cálculo de def_total_hours con datos REALES de staging")
print("=" * 80)
print()

# --- Parámetros de configuración (ConfigEntry Options) ---
print("=== 1. PARÁMETROS DE CONFIGURACIÓN ===")
battery_capacity_kwh = 28.0          # From options.battery_capacity_kwh
charging_power_kw = 3.4              # From options.charging_power_kw
kwh_per_km = 0.18                    # From options.kwh_per_km
safety_margin_percent = 10           # From options.safety_margin_percent
t_base = 24.0                        # From options.t_base
print(f"  battery_capacity_kwh: {battery_capacity_kwh}")
print(f"  charging_power_kw: {charging_power_kw}")
print(f"  kwh_per_km: {kwh_per_km}")
print(f"  safety_margin_percent: {safety_margin_percent}%")
print(f"  t_base: {t_base}")
print()

# --- Estado actual de sensores ---
print("=== 2. ESTADO ACTUAL DE SENSORES ===")
soc_current = 65.0                   # sensor.ev_battery_soc = 65
soh_current = 94.0                   # sensor.ev_health_soh = 94
charging_sim = "off"                 # input_boolean.ev_charging_sim = off
print(f"  SOC actual: {soc_current}%")
print(f"  SOH actual: {soh_current}%")
print(f"  Charging sim: {charging_sim}")
print()

# --- Viajes recurrentes ---
print("=== 3. VIAJES RECURRENTEs ===")
trips = [
    {
        "id": "rec_5_xeqnmt",
        "tipo": "recurrente",
        "dia_semana": "0",          # JS getDay: 0=Domingo
        "hora": "09:40",
        "km": 31.0,
        "kwh": 5.4,
        "activo": True,
    },
    {
        "id": "rec_1_fy4pfk",
        "tipo": "recurrente",
        "dia_semana": "1",          # JS getDay: 1=Lunes
        "hora": "21:40",
        "km": 30.0,
        "kwh": 5.4,
        "activo": True,
    },
]
for trip in trips:
    print(f"  {trip['id']}: dia={trip['dia_semana']} (JS getDay), hora={trip['hora']}, km={trip['km']}, kwh={trip['kwh']}")
print()

# --- Momento actual ---
print("=== 4. MOMENTO ACTUAL ===")
now = datetime(2026, 5, 15, 19, 43, 0, tzinfo=timezone.utc)
print(f"  now: {now.isoformat()}")
print(f"  Día: {now.strftime('%A')}")
print()

# =============================================================================
# PASO 1: Calcular deadlines de los viajes
# =============================================================================

print("=" * 80)
print("PASO 1: Calcular deadlines (próximas fechas de viaje)")
print("=" * 80)

def js_getday_to_internal(day_str: str) -> int:
    """Convert JS getDay format to internal Monday=0 format."""
    js_day = int(day_str)
    return (js_day - 1) % 7

def get_next_occurrence(day_index: int, time_str: str, from_dt: datetime) -> datetime:
    """Get next occurrence of a day/time from now."""
    # day_index: 0=Monday, 6=Sunday (internal format)
    hours, minutes = map(int, time_str.split(':'))
    
    delta_days = day_index - from_dt.weekday()
    if delta_days < 0:
        delta_days += 7
    
    result = from_dt.replace(hour=hours, minute=minutes, second=0, microsecond=0) + timedelta(days=delta_days)
    return result

DAYS_OF_WEEK = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]

deadlines = []
for trip in trips:
    js_day = int(trip['dia_semana'])
    internal_day = js_getday_to_internal(trip['dia_semana'])
    next_dt = get_next_occurrence(internal_day, trip['hora'], now)
    
    print(f"  {trip['id']}:")
    print(f"    JS getDay: {js_day} -> internal: {internal_day} ({DAYS_OF_WEEK[internal_day]})")
    print(f"    hora: {trip['hora']}")
    print(f"    next_occurrence: {next_dt.isoformat()}")
    
    hours_until = (next_dt - now).total_seconds() / 3600
    print(f"    horas_hasta_viaje: {hours_until:.2f}h")
    print()
    
    deadlines.append({
        "trip": trip,
        "deadline_dt": next_dt,
        "hours_until": hours_until,
        "internal_day": internal_day,
    })

# Sort by deadline
deadlines.sort(key=lambda x: x['deadline_dt'])
print("  Trips ordenados por deadline:")
for d in deadlines:
    print(f"    {d['trip']['id']}: {d['deadline_dt'].isoformat()} ({d['hours_until']:.2f}h)")
print()

# =============================================================================
# PASO 2: Calcular energía necesaria para cada viaje (calculate_energy_needed)
# =============================================================================

print("=" * 80)
print("PASO 2: Calcular energía necesaria (calculate_energy_needed)")
print("=" * 80)

DEFAULT_SOC_BASE = 35.0
DEFAULT_SAFETY_MARGIN = 10

for d in deadlines:
    trip = d['trip']
    kwh_trip = trip.get('kwh', 0.0)
    
    # Energía mínima de seguridad que debe quedar DESPUÉS del viaje
    energia_seguridad = (safety_margin_percent / 100.0) * battery_capacity_kwh
    print(f"  {trip['id']}:")
    print(f"    energia_viaje: {kwh_trip} kWh")
    print(f"    energia_seguridad: ({safety_margin_percent}/100) × {battery_capacity_kwh} = {energia_seguridad:.2f} kWh")
    
    # Energía total necesaria = viaje + margen seguridad post-viaje
    energia_objetivo = kwh_trip + energia_seguridad
    print(f"    energia_objetivo: {kwh_trip} + {energia_seguridad:.2f} = {energia_objetivo:.2f} kWh")
    
    # Energía actual en batería
    energia_actual = (soc_current / 100.0) * battery_capacity_kwh
    print(f"    energia_actual: ({soc_current}/100) × {battery_capacity_kwh} = {energia_actual:.2f} kWh")
    
    # Proactive charging trigger
    if energia_actual >= energia_objetivo:
        energia_necesaria = kwh_trip
        print(f"    energia_actual >= energia_objetivo → energia_necesaria = energia_viaje = {energia_necesaria} kWh")
    else:
        energia_necesaria = max(0.0, energia_objetivo - energia_actual)
        print(f"    energia_actual < energia_objetivo → energia_necesaria = {energia_objetivo:.2f} - {energia_actual:.2f} = {energia_necesaria:.2f} kWh")
    
    # Clamp
    energia_necesaria = min(energia_necesaria, battery_capacity_kwh)
    
    # Horas de carga
    if charging_power_kw > 0:
        horas_carga = energia_necesaria / charging_power_kw
    else:
        horas_carga = 0
    
    horas_carga_ceil = math.ceil(horas_carga) if horas_carga > 0 else 0
    print(f"    horas_carga: {energia_necesaria} / {charging_power_kw} = {horas_carga:.4f}")
    print(f"    horas_carga_necesarias (ceil): {horas_carga_ceil}")
    print()
    
    d['energia_necesaria'] = energia_necesaria
    d['horas_carga_necesarias'] = horas_carga_ceil

# =============================================================================
# PASO 3: Calcular SOC capping dinámico (calculate_dynamic_soc_limit)
# =============================================================================

print("=" * 80)
print("PASO 3: Calcular SOC capping dinámico (calculate_dynamic_soc_limit)")
print("=" * 80)

for d in deadlines:
    trip = d['trip']
    t_hours = d['hours_until']
    
    # SOC after trip
    trip_kwh = trip.get('kwh', 0.0)
    soc_after = max(0.0, soc_current - (trip_kwh / battery_capacity_kwh) * 100.0)
    print(f"  {trip['id']}:")
    print(f"    t_hours (horas hasta viaje): {t_hours:.2f}h")
    print(f"    soc_after (SOC post-viaje): {soc_current} - ({trip_kwh}/{battery_capacity_kwh} × 100) = {soc_after:.2f}%")
    
    # Risk calculation
    risk = t_hours * (soc_after - DEFAULT_SOC_BASE) / 65.0
    print(f"    risk: {t_hours:.2f} × ({soc_after:.2f} - {DEFAULT_SOC_BASE}) / 65 = {risk:.4f}")
    
    if risk <= 0:
        soc_cap = 100.0
        print("    risk <= 0 → soc_cap = 100.0 (no risk)")
    else:
        limit = DEFAULT_SOC_BASE + 65.0 * (1.0 / (1.0 + risk / t_base))
        soc_cap = max(35.0, min(100.0, limit))
        print(f"    limit: {DEFAULT_SOC_BASE} + 65 × (1 / (1 + {risk:.4f}/{t_base}))")
        print(f"    limit: {DEFAULT_SOC_BASE} + 65 × (1 / {1 + risk/t_base:.4f})")
        print(f"    limit: {DEFAULT_SOC_BASE} + 65 × {1/(1 + risk/t_base):.4f}")
        print(f"    limit: {DEFAULT_SOC_BASE} + {65/(1 + risk/t_base):.4f} = {limit:.4f}")
        print(f"    soc_cap: max(35, min(100, {limit:.4f})) = {soc_cap:.2f}%")
    
    print(f"    soc_cap FINAL: {soc_cap:.2f}%")
    print()
    
    d['soc_after'] = soc_after
    d['risk'] = risk
    d['soc_cap'] = soc_cap

# =============================================================================
# PASO 4: Aplicar SOC capping a total_hours
# =============================================================================

print("=" * 80)
print("PASO 4: Aplicar SOC capping a total_hours")
print("=" * 80)

for d in deadlines:
    trip = d['trip']
    soc_cap = d['soc_cap']
    
    print(f"  {trip['id']}:")
    print(f"    soc_cap: {soc_cap:.2f}%")
    print(f"    soc_current: {soc_current}%")
    
    # Check if capping applies
    if soc_cap < 100.0 and soc_current < 100.0:
        current_energy = (soc_current / 100.0) * battery_capacity_kwh
        max_energy = (soc_cap / 100.0) * battery_capacity_kwh
        capped_energy = max(0.0, max_energy - current_energy)
        capped_hours = capped_energy / charging_power_kw if charging_power_kw > 0 else 0.0
        total_hours = math.ceil(capped_hours) if capped_hours > 0 else 0
        
        print("    soc_cap < 100 AND soc_current < 100 → APPLY CAPPING")
        print(f"    current_energy: ({soc_current}/100) × {battery_capacity_kwh} = {current_energy:.2f} kWh")
        print(f"    max_energy: ({soc_cap:.2f}/100) × {battery_capacity_kwh} = {max_energy:.2f} kWh")
        print(f"    capped_energy: max(0, {max_energy:.2f} - {current_energy:.2f}) = {capped_energy:.2f} kWh")
        print(f"    capped_hours: {capped_energy:.2f} / {charging_power_kw} = {capped_hours:.4f}")
        print(f"    total_hours (ceil): {total_hours}")
    else:
        total_hours = d['horas_carga_necesarias']
        print("    NO APPLY CAPPING (soc_cap >= 100 OR soc_current >= 100)")
        print(f"    total_hours = horas_carga_necesarias = {total_hours}")
    
    print()
    d['total_hours_after_cap'] = total_hours

# =============================================================================
# PASO 5: Deficit propagation
# =============================================================================

print("=" * 80)
print("PASO 5: Deficit propagation (calculate_hours_deficit_propagation)")
print("=" * 80)

# Build windows for deficit propagation
windows = []
total_hours_list = []

for d in deadlines:
    trip = d['trip']
    hours_until = d['hours_until']
    horas_carga = d['horas_carga_necesarias']
    
    # ventana_horas = available charging window
    # For simplicity, assume window = hours until departure (hora_regreso = now)
    ventana_horas = hours_until
    
    print(f"  {trip['id']}:")
    print(f"    ventana_horas (available): {ventana_horas:.2f}h")
    print(f"    horas_carga_necesarias: {horas_carga}")
    print(f"    total_hours_after_cap: {d['total_hours_after_cap']}")
    
    windows.append({
        "ventana_horas": ventana_horas,
        "horas_carga_necesarias": horas_carga,
    })
    total_hours_list.append(d['total_hours_after_cap'])

# Walk backward from last trip to first
print()
print("  Walking backward (last to first)...")

# Initial values
adjusted_total_hours = list(total_hours_list)

for i in range(len(windows) - 1, -1, -1):
    w = windows[i]
    trip_id = deadlines[i]['trip']['id']
    
    ventana_horas = w['ventana_horas']
    horas_carga_necesarias = w['horas_carga_necesarias']
    def_total_hours = adjusted_total_hours[i]
    
    print(f"    Processing {trip_id} (index {i}):")
    print(f"      ventana_horas: {ventana_horas:.2f}")
    print(f"      horas_carga_necesarias: {horas_carga_necesarias}")
    print(f"      def_total_hours (current): {def_total_hours}")
    
    # Calculate deficit
    # If window is not enough for charging, propagate deficit to previous trip
    if ventana_horas < horas_carga_necesarias:
        deficit = horas_carga_necesarias - ventana_horas
        print(f"      VENTANA INSUFICIENTE: {ventana_horas:.2f} < {horas_carga_necesarias}")
        print(f"      deficit: {ventana_horas:.2f} - {horas_carga_necesarias} = {deficit:.2f}")
    else:
        deficit = 0
        spare = ventana_horas - def_total_hours
        print(f"      VENTANA SUFICIENTE: {ventana_horas:.2f} >= {horas_carga_necesarias}")
        print(f"      spare capacity: {ventana_horas:.2f} - {def_total_hours} = {spare:.2f}")
    
    adjusted_total_hours[i] = def_total_hours

print()
print("  === RESULTADO FINAL ===")
for i, d in enumerate(deadlines):
    trip_id = d['trip']['id']
    final_hours = adjusted_total_hours[i]
    print(f"    {trip_id}: def_total_hours = {final_hours}")

print()
print("=" * 80)
print("RESUMEN COMPLETO")
print("=" * 80)
for i, d in enumerate(deadlines):
    print(f"\n  Viaje {i+1}: {d['trip']['id']}")
    print(f"    Deadline: {d['deadline_dt'].isoformat()}")
    print(f"    Horas hasta viaje: {d['hours_until']:.2f}h")
    print(f"    SOC post-viaje: {d['soc_after']:.2f}%")
    print(f"    SOC cap: {d['soc_cap']:.2f}%")
    print(f"    Horas carga necesarias (sin cap): {d['horas_carga_necesarias']}")
    print(f"    Horas carga (con cap): {d['total_hours_after_cap']}")

print()
print("  def_total_hours esperado por el sensor EMHASS:")
for i, d in enumerate(deadlines):
    print(f"    {d['trip']['id']}: {d['total_hours_after_cap']}")
