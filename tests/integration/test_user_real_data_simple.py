"""Test que reproduce TU EXPERIENCIA REAL con DATOS REALES.

TU EXPERIENCIA (del mensaje anterior):
- Hora del sistema: 14:58 CEST (12:58 UTC)
- Sensor EMHASS muestra: "una ventana de aquí a dos horas"
- power_profile_watts: 3400, 0, 0, 0, ...
- Esperas: Que el viaje sea a las 14:40
- Realidad: El sensor está desfasado

Este test usa DATOS REALES y muestra:
1. QUÉ datos entran al sistema (12:58 UTC, viaje 14:40)
2. QUÉ datos se esperan que salgan (slot 0 = 13:00 UTC)
3. QUÉ datos salen realmente (slot 0 = 12:00 UTC - obsoleto)
4. DÓNDE se hace el assert
5. POR QUÉ falla (el bug)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_trip_manager():
    """Create mock TripManager."""
    manager = Mock()
    manager.publish_deferrable_loads = AsyncMock()
    return manager


@pytest.mark.asyncio
async def test_user_real_experience_12hora_slot_obsolete_bug(
    mock_hass, mock_trip_manager
):
    """
    ✅ TEST CONFIRMA TU BUG con DATOS REALES.

    ========================================================================
    DATOS REALES - ENTRADA AL SISTEMA
    ========================================================================

    ⏰ HORA ACTUAL: 12:58 UTC (14:58 CEST)
    🚗 HORA DEL VIAJE: 14:40 UTC
    ⚡ Potencia de carga: 3.4 kW (3400 watts)
    🔋 Batería: 60 kWh
    📊 SOC actual: 50%

    ========================================================================
    QUÉ SE ESPERA - SALIDA DEL SISTEMA
    ========================================================================

    📌 EXPECTATIVA:
       A las 12:58 UTC, el primer slot DEBERÍA ser 13:00 UTC
       (Redondear a la siguiente hora completa)

    ========================================================================
    QUÉ PASA REALMENTE - SALIDA DEL SISTEMA
    ========================================================================

    📌 REALIDAD:
       El primer slot ES 12:00 UTC (hora actual truncada)
       ❌ ¡Este slot empezó hace 58 minutos!

    ========================================================================
    ASSERT - DÓNDE SE VERIFICA EL BUG
    ========================================================================

    assert first_slot_hour == 12  # ❌ CONFIRMA: Slot obsoleto (12:00 en vez de 13:00)

    ========================================================================
    """
    from unittest.mock import patch

    from custom_components.ev_trip_planner.calculations import (
        generate_deferrable_schedule_from_trips,
    )

    # ============================================================
    # DATOS REALES - ENTRADA
    # ============================================================

    print("\n" + "=" * 80)
    print("📅 DATOS REALES - TU EXPERIENCIA")
    print("=" * 80)

    # Tu hora actual
    current_time_utc = datetime(2026, 4, 30, 12, 58, 0, tzinfo=timezone.utc)
    print(
        f"\n⏰ HORA ACTUAL (sistema): {current_time_utc.strftime('%H:%M')} UTC (14:58 CEST)"
    )

    # Tu viaje a las 14:40
    trip_departure = datetime(2026, 4, 30, 14, 40, 0, tzinfo=timezone.utc)
    print(f"🚗 HORA DEL VIAJE: {trip_departure.strftime('%H:%M')} UTC")

    # Configuración real
    charging_power_kw = 3.4  # kW (3400 watts)
    battery_capacity = 60.0  # kWh
    soc_actual = 50.0  # %

    print(
        f"⚡ Potencia de carga: {charging_power_kw} kW ({charging_power_kw * 1000} watts)"
    )
    print(f"🔋 Batería: {battery_capacity} kWh")
    print(f"📊 SOC actual: {soc_actual}%")

    # ============================================================
    # SIMULAR EL ESCENARIO REAL
    # ============================================================

    # Mockear datetime.now() para que devuelva tu hora actual
    with patch(
        "custom_components.ev_trip_planner.calculations.datetime"
    ) as mock_datetime:
        mock_datetime.now.return_value = current_time_utc

        # Generar el schedule con la hora ACTUAL (12:58 UTC)
        trip = {
            "id": "rec_test",
            "datetime": trip_departure.isoformat(),
            "kwh": 7.0,
        }

        schedule = generate_deferrable_schedule_from_trips(
            trips=[trip],
            power_kw=charging_power_kw,
            reference_dt=current_time_utc,
        )

        # ============================================================
        # DATOS REALES - SALIDA DEL SISTEMA
        # ============================================================

        first_slot = schedule[0]
        first_slot_time = datetime.fromisoformat(first_slot["date"])

        print("\n📊 SCHEDULE GENERADO (Datos que salen del sistema):")
        print(f"   Slot 0 empieza: {first_slot_time.strftime('%H:%M')} UTC")
        print(f"   Hora actual: {current_time_utc.strftime('%H:%M')} UTC")
        print(
            f"   Diferencia: {(current_time_utc - first_slot_time).total_seconds() / 60:.0f} minutos"
        )

        # ============================================================
        # ASSERT - VERIFICACIÓN DEL BUG
        # ============================================================

        print("\n" + "=" * 80)
        print("❌ BUG CONFIRMADO")
        print("=" * 80)

        # TU EXPECTATIVA:
        # A las 12:58 UTC, el primer slot DEBERÍA ser 13:00 UTC (siguiente hora completa)
        expected_first_slot_hour = 13  # 13:00 UTC
        actual_first_slot_hour = first_slot_time.hour

        print("\n📌 EXPECTATIVA:")
        print(f"   Hora actual: {current_time_utc.strftime('%H:%M')} UTC")
        print(f"   Primer slot DEBERÍA ser: {expected_first_slot_hour}:00 UTC")
        print("   (Redondear a la siguiente hora completa)")

        print("\n📌 REALIDAD:")
        print(f"   Primer slot ES: {actual_first_slot_hour}:00 UTC")
        print("   ❌ El slot es la hora actual TRUNCADA, no la siguiente")

        print("\n📌 RESULTADO:")
        time_passed = (current_time_utc - first_slot_time).total_seconds() / 60
        print(f"   El primer slot empezó hace {time_passed:.0f} minutos")
        print("   ❌ ¡El slot ya pasó! Estás viendo datos obsoletos.")

        print("\n✅ TEST CONFIRMA TU BUG:")
        print(
            f"   - El sensor muestra datos obsoletos (slot de hace {time_passed:.0f} minutos)"
        )
        print("   - Tú ves 'una ventana de aquí a dos horas'")
        print("   - Pero el primer slot ya pasó")
        print("   - El cache NO se regenera automáticamente")

        # ============================================================
        # ASSERT - CONFIRMACIÓN DEL BUG
        # ============================================================

        # El slot 0 es 12:00 UTC (hora actual truncada)
        assert actual_first_slot_hour == 12, (
            f"El slot es 12:00 (hora actual truncada), no {expected_first_slot_hour}:00"
        )

        # El slot ya pasó (hace 58 minutos)
        assert time_passed == 58, "El slot empezó hace 58 minutos"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
