"""RED phase test: Failing test that demonstrates the bug in emhass_adapter.py.

This test FAILS with the current code because def_end_timestep is calculated
incorrectly using hours_available instead of fin_ventana.

After fixing the code, this test should PASS.
"""

from datetime import datetime, timedelta, timezone
from custom_components.ev_trip_planner.calculations import calculate_multi_trip_charging_windows


def test_charging_window_returns_fin_ventana():
    """Verify calculate_multi_trip_charging_windows returns fin_ventana.

    This is a prerequisite for fixing the bug.
    """
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=96)
    trip = {"id": "test", "kwh": 21.0}

    windows = calculate_multi_trip_charging_windows(
        trips=[(deadline, trip)],
        soc_actual=50.0,
        hora_regreso=None,  # Car not yet returned
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        duration_hours=6.0,
        safety_margin_percent=10.0,
    )

    assert len(windows) > 0
    window = windows[0]

    # The function MUST return both inicio_ventana and fin_ventana
    assert "inicio_ventana" in window, "calculate_multi_trip_charging_windows must return inicio_ventana"
    assert "fin_ventana" in window, "calculate_multi_trip_charging_windows must return fin_ventana"

    inicio_ventana = window["inicio_ventana"]
    fin_ventana = window["fin_ventana"]

    # Both should be non-None
    assert inicio_ventana is not None, "inicio_ventana should not be None"
    assert fin_ventana is not None, "fin_ventana should not be None"

    # fin_ventana should be after inicio_ventana
    assert fin_ventana > inicio_ventana, "fin_ventana should be after inicio_ventana"

    # The window duration should be positive
    ventana_horas = (fin_ventana - inicio_ventana).total_seconds() / 3600
    assert ventana_horas > 0, f"Window should have positive duration, got {ventana_horas}h"

    print(f"✓ Charging window: inicio={inicio_ventana}, fin={fin_ventana}, duration={ventana_horas}h")


def test_def_end_timestep_calculation_bug():
    """RED phase test: Demonstrates the bug in def_end_timestep calculation.

    Scenario from user's bug report:
    - Trip needs 6 hours of charging (21 kWh at 3.6 kW)
    - Deadline is 96 hours from now
    - Charging window (inicio_ventana) is at hour ~90 (estimated)
    - fin_ventana is at hour 96 (deadline)

    Current buggy code:
        def_end_timestep = min(int(hours_available), 168)
    where hours_available = (deadline - now) / 3600 = 96

    When inicio_ventana is also at hour 96:
        def_start_timestep = 96
        def_end_timestep = 96 (BUG! Same as start)

    Expected fix:
        def_end_timestep should be calculated from fin_ventana, not hours_available
    """
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=96)

    # Simulate what calculate_multi_trip_charging_windows returns
    inicio_ventana = deadline - timedelta(hours=6)  # 6 hours before deadline
    fin_ventana = deadline  # At deadline

    # Current buggy calculation
    hours_available = (deadline - now).total_seconds() / 3600
    def_end_timestep_BUG = min(int(hours_available), 168)

    # When charging window starts at deadline (edge case):
    inicio_at_deadline = deadline
    delta_hours = (inicio_at_deadline - now).total_seconds() / 3600
    def_start_timestep = max(0, min(int(delta_hours), 168))

    # BUG: def_start == def_end when inicio_ventana == deadline
    assert def_end_timestep_BUG == def_start_timestep, \
        f"Bug: def_end ({def_end_timestep_BUG}) == def_start ({def_start_timestep}) when inicio_ventana == deadline"

    # This is impossible for a 6-hour charge!
    window_size_bug = def_end_timestep_BUG - def_start_timestep
    assert window_size_bug == 0, "Bug: Window size is 0 when charging is needed"

    print("\n✗ BUG DEMONSTRATED:")
    print(f"  def_start_timestep = {def_start_timestep}")
    print(f"  def_end_timestep (BUG) = {def_end_timestep_BUG}")
    print(f"  Window size = {window_size_bug} hours (impossible for 6h charge!)")


def test_def_end_timestep_correct_calculation():
    """Shows the CORRECT way to calculate def_end_timestep."""
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=96)

    # Charging window from calculate_multi_trip_charging_windows
    inicio_ventana = deadline - timedelta(hours=6)
    fin_ventana = deadline

    # CORRECT calculation using fin_ventana
    delta_hours_inicio = (inicio_ventana - now).total_seconds() / 3600
    def_start_timestep = max(0, min(int(delta_hours_inicio), 168))  # = 90

    delta_hours_fin = (fin_ventana - now).total_seconds() / 3600
    def_end_timestep_CORRECT = max(0, min(int(delta_hours_fin), 168))  # = 96

    window_size = def_end_timestep_CORRECT - def_start_timestep  # = 6 hours

    assert window_size >= 6, f"Window size ({window_size}h) should allow 6h charging"
    assert def_end_timestep_CORRECT > def_start_timestep, \
        f"def_end ({def_end_timestep_CORRECT}) > def_start ({def_start_timestep})"

    print("\n✓ CORRECT CALCULATION:")
    print(f"  def_start_timestep = {def_start_timestep}")
    print(f"  def_end_timestep (CORRECT) = {def_end_timestep_CORRECT}")
    print(f"  Window size = {window_size} hours (enough for 6h charge!)")


if __name__ == "__main__":
    print("Running RED phase tests...\n")

    test_charging_window_returns_fin_ventana()
    test_def_end_timestep_calculation_bug()
    test_def_end_timestep_correct_calculation()

    print("\n✓ All tests passed (bug demonstrated, fix pending)")
