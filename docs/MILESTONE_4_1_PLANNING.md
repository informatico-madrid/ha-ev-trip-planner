# 🚀 Milestone 4.1: Smart Charging Profile Improvements — Implementation Plan

**Planning Document**  
**Version**: 1.1  
**Date**: 2025-12-14  
**Last Review**: 2026-04-09  
**Status**: 📋 **PLANNED — NOT STARTED**  
**Target**: v0.5.0

> ⚠️ **This document is a future work plan. Nothing described here is implemented yet.**  
> The current code covers up to Milestone 4 (binary SOC-aware charging profile).  
> See [`ROADMAP.md`](../ROADMAP.md) for the global project status.

---

## 📋 Executive Summary

Milestone 4.1 extends the Smart Charging Profile functionality (Milestone 4) with improvements based on production feedback and advanced use case analysis. This milestone focuses on **cost optimization**, **multi-vehicle support**, and **enhanced user experience**.

**Added Value**: Up to 30% charging cost reduction, support for homes with multiple EVs, and interactive UI for real-time monitoring.

**Starting Point**: Milestone 4 implemented and in production — binary profile of 168 values (24h × 7d), EMHASS integration with dynamic index per trip, SOC-aware, coordinated with `presence_monitor` and `schedule_monitor`.

---

## 🎯 Planned Improvements

### 1. ⚡ Smart Distributed Charging (HIGH PRIORITY)

**Current Problem**: The current charging profile uses a binary strategy (0W or maximum power) in a single hour before the trip. It does not optimize electricity costs.

**Proposed Solution**:
- Distribute charging across multiple hours before the trip
- Prioritize hours with lowest electricity price (EMHASS integration)
- Implement simple optimization algorithm based on:
  - Hourly electricity price (EMHASS sensor)
  - Hours available until the trip
  - Charger maximum power

**Optimization Algorithm**:
```python
# Pseudocode
def optimize_charging(energy_needed_kwh, hours_available, prices_per_hour):
    # 1. Sort hours by price ascending
    sorted_hours = sorted(prices_per_hour.items(), key=lambda x: x[1])
    
    # 2. Assign charging to cheapest hours first
    optimized_profile = [0] * 168
    remaining_energy = energy_needed_kwh
    
    for hour, price in sorted_hours:
        if remaining_energy <= 0:
            break
        if hour < hours_available:
            # Assign maximum power to cheap hour
            energy_hour = min(charging_power_kw, remaining_energy)
            optimized_profile[hour] = energy_hour * 1000  # Convert to Watts
            remaining_energy -= energy_hour
    
    return optimized_profile
```

**Benefit**: Up to 30% charging cost reduction on variable tariffs.

**Complexity**: Medium  
**Estimate**: 2-3 days development  
**Tests Required**: 5-7 TDD tests

---

### 2. 🚗 Multiple Vehicle Support (HIGH PRIORITY)

**Current Problem**: The system assumes a single vehicle per configuration. There is no load balancing between vehicles.

**Proposed Solution**:
- Support for 2+ simultaneous vehicles
- Load balancing based on:
  - Vehicle priority (configurable)
  - Trip urgency (how much time until the trip)
  - Current SOC of each vehicle
- Home power limit (e.g., 10 kW total)

**Usage Example**:
```yaml
# Multiple vehicle configuration
vehicles:
  - vehicle_id: chispitas
    priority: 1  # High priority
    soc_sensor: sensor.ovms_chispitas_soc
  - vehicle_id: morgan
    priority: 2  # Low priority
    soc_sensor: sensor.morgan_battery_level

# Home power limit
home_max_power_kw: 10.0  # If both charge, do not exceed 10 kW
```

**Benefit**: Homes with multiple EVs can charge efficiently without overloading the electrical installation.

**Complexity**: High  
**Estimate**: 4-5 days development  
**Tests Required**: 8-10 TDD tests

---

### 3. 🌡️ Climate-Based Consumption Prediction (MEDIUM PRIORITY)

**Current Problem**: The necessary energy calculation does not consider climate factors that affect range.

**Proposed Solution**:
- Integration with exterior temperature sensor
- Automatic consumption adjustment based on:
  - Extreme cold (< 5°C): +20% consumption
  - Extreme heat (> 35°C): +10% consumption
  - Optimal temperature (15-25°C): normal consumption
- Alerts when climate significantly affects range

**Adjustment Formula**:
```python
def adjust_consumption_by_climate(kwh_needed, temperature_celsius):
    if temperature_celsius < 5:
        factor = 1.20  # +20% in cold
    elif temperature_celsius > 35:
        factor = 1.10  # +10% in heat
    else:
        factor = 1.00  # No adjustment
    
    return kwh_needed * factor
```

**Benefit**: Accuracy in necessary energy calculations, avoiding running out of battery.

**Complexity**: Low  
**Estimate**: 1-2 days development  
**Tests Required**: 3-4 TDD tests

---

### 4. 📊 Improved UI for Charging Profile (MEDIUM PRIORITY)

**Current Problem**: There is no graphical visualization of the charging profile. Users cannot see when the vehicle will charge.

**Proposed Solution**:
- Dashboard chart showing:
  - Next 24-48 hours of charging profile
  - Hours with active charging (colored)
  - Electricity price per hour (if available)
  - Current and projected SOC
- "Next charge in X hours" indicator
- "Charge Now" forced button (automatic override)

**UI Components**:
```yaml
# Lovelace card example
type: custom:mini-graph-card
entities:
  - entity: sensor.chispitas_power_profile
    attribute: power_profile_watts
  - entity: sensor.emhass_electricity_price
name: "Charging Profile and Prices"
```

**Benefit**: Full transparency for the user. Can see when and why charging occurs.

**Complexity**: Medium  
**Estimate**: 3-4 days development (includes frontend)  
**Tests Required**: 4-5 TDD tests (backend) + manual UI testing

---

### 5. 🔋 Battery Health Optimization (LOW PRIORITY)

**Current Problem**: Charging always uses maximum power, which is not optimal for long-term battery health.

**Proposed Solution**:
- "Battery Health" mode that:
  - Limits charging to 80% SOC for daily trips (configurable)
  - Uses slow charging (3.7 kW) instead of fast (7.4 kW) when time allows
  - Schedules charging to avoid battery at 100% for hours

**Example**:
```yaml
# Battery health configuration
battery_health_mode: true
max_daily_soc: 80  # Do not charge beyond 80% for daily trips
prefer_slow_charging: true  # Use 3.7 kW when possible
```

**Benefit**: Extend battery life by 15-20% according to studies.

**Complexity**: Medium  
**Estimate**: 2-3 days development  
**Tests Required**: 4-5 TDD tests

---

### 6. 🔔 Improved Smart Notifications (MEDIUM PRIORITY)

**Current Problem**: Notifications are basic. There are no proactive reminders.

**Proposed Solution**:
- "Connect vehicle" reminder X hours before scheduled charging
- "Incomplete charge" alert if vehicle does not reach target SOC
- "Trip at risk" notification if climate will significantly affect range
- Daily/weekly cost savings summary

**Examples**:
```yaml
# Notification configuration
notifications:
  pre_charge_reminder_hours: 2  # Reminder 2h before
  incomplete_charge_alert: true
  weather_impact_alert: true
  savings_summary: "weekly"  # daily, weekly, monthly
```

**Benefit**: User always informed and can take preventive action.

**Complexity**: Low  
**Estimate**: 1-2 days development  
**Tests Required**: 3-4 TDD tests

---

## 📊 Prioritization and Roadmap

### Prioritization Matrix

| Improvement | User Impact | Technical Complexity | Cost ROI | Priority | Target Version |
|--------|----------------|-------------------|------------|-----------|----------------|
| Smart Distributed Charging | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **HIGH** | v0.5.0 |
| Multiple Vehicles | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **HIGH** | v0.5.0 |
| Climate Prediction | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | MEDIUM | v0.5.1 |
| Improved UI | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | MEDIUM | v0.5.1 |
| Battery Health | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | LOW | v0.5.2 |
| Notifications | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | MEDIUM | v0.5.1 |

---

## 🧪 Testing Strategy (TDD)

### Phase 1: Distributed Charging Tests (HIGH PRIORITY)

```python
# tests/test_power_profile_optimization.py

async def test_distributed_charging_prioritizes_cheap_hours(hass):
    """Test that charging is assigned to hours with lowest price."""
    # Arrange: Trip in 6 hours, needs 3 hours of charging
    # Prices: [0.15, 0.12, 0.10, 0.20, 0.18, 0.14] €/kWh
    
    # Act: Generate optimized profile
    
    # Assert: Charging assigned to hours 1, 2, 5 (lowest prices)
    assert profile[1] == 7400  # Cheap hour
    assert profile[2] == 7400  # Cheap hour
    assert profile[0] == 0     # Expensive hour, do not use

async def test_distributed_charging_respects_hours_available(hass):
    """Test that charging is not scheduled after the trip."""
    # Arrange: Trip in 3 hours, needs 5 hours of charging
    
    # Act: Generate profile
    
    # Assert: Insufficient time alert, empty profile
    assert alert == True
    assert all(p == 0 for p in profile[3:])  # No charging after trip
```

### Phase 2: Multiple Vehicles Tests (HIGH PRIORITY)

```python
# tests/test_multi_vehicle.py

async def test_two_vehicles_without_exceeding_home_limit(hass):
    """Test that two vehicles do not exceed home power limit."""
    # Arrange: Home limit 10 kW, both need 7.4 kW
    
    # Act: Generate profiles with balancing
    
    # Assert: One charges at 7.4 kW, other waits or charges at 2.6 kW
    assert total_power <= 10000  # 10 kW limit

async def test_vehicle_priority_affects_charging_order(hass):
    """Test that vehicle with priority 1 charges first."""
    # Arrange: Two vehicles, same need, different priorities
    
    # Act: Generate profiles
    
    # Assert: Priority 1 vehicle has more charging hours assigned
    assert charging_hours_prio1 > charging_hours_prio2
```

### Phase 3: Climate Tests (MEDIUM PRIORITY)

```python
# tests/test_climate_adjustment.py

async def test_consumption_adjustment_extreme_cold(hass):
    """Test that extreme cold increases consumption by 20%."""
    # Arrange: 10 kWh trip, temperature 0°C
    
    # Act: Calculate with climate adjustment
    
    # Assert: 12 kWh needed (10 * 1.20)
    assert energy_needed == 12.0

async def test_consumption_adjustment_optimal_temperature(hass):
    """Test that optimal temperature does not adjust consumption."""
    # Arrange: 10 kWh trip, temperature 20°C
    
    # Act: Calculate with climate adjustment
    
    # Assert: 10 kWh needed (no adjustment)
    assert energy_needed == 10.0
```

---

## 📅 Estimated Timeline

### Sprint 1: Smart Distributed Charging (2 weeks)
- **Week 1**: Core implementation + TDD tests
- **Week 2**: EMHASS integration + production validation

### Sprint 2: Multiple Vehicles (3 weeks)
- **Week 1**: Architecture design + TDD tests
- **Week 2**: Balancing implementation + integration tests
- **Week 3**: Validation with 2+ real vehicles

### Sprint 3: Improved UI + Notifications (2 weeks)
- **Week 1**: Backend for UI + endpoints
- **Week 2**: Lovelace dashboard + notifications

### Sprint 4: Climate + Battery Health (2 weeks)
- **Week 1**: Climate integration + tests
- **Week 2**: Battery health mode + optimization

**Total Estimated**: 9 weeks (2-3 months) for complete Milestone 4.1

---

## 🔧 Technical Requirements

### New Dependencies
```python
# requirements.txt (optional)
# - numpy (for optimization calculations)
# - pandas (for price analysis)
```

### Config Flow Changes
- New step: "Multiple Vehicles" (if detects >1 config entry)
- New field: `home_max_power_kw` (optional)
- New field: `battery_health_mode` (checkbox)

### Database Changes
- New attribute in `vehicle_config`: `priority` (int, default: 1)
- New attribute in `vehicle_config`: `max_soc_daily` (float, default: 100.0)

---

## 📈 Success Metrics

### KPIs to Measure
1. **Cost Reduction**: % savings on monthly electricity bill
2. **User Satisfaction**: Satisfaction survey (1-5)
3. **SOC Accuracy**: % of times vehicle reaches target SOC
4. **UI Usage**: % of users using charging profile dashboard
5. **Stability**: % false alerts / errors

### Objectives
- **Costs**: Reduce charging cost by 25% on average
- **Satisfaction**: 4.5/5 or higher on survey
- **Accuracy**: 95% of trips with target SOC reached
- **UI**: 70% of active users use dashboard
- **Stability**: < 1% critical errors

---

## 📝 Implementation Notes

### Security Considerations
- **Limit Validation**: Always respect `home_max_power_kw`
- **Fallback**: If optimization fails, use current binary strategy (Milestone 4)
- **Manual Override**: User can always force charging manually

### Backward Compatibility
- All improvements are **optional**
- Existing configuration works without changes
- New fields have sensible default values

### Performance
- Optimization calculations: < 100ms per vehicle
- Profile updates: Every 15 minutes or when SOC changes
- Price cache: 1 hour (configurable)

---

## 📚 Related Documentation

- [`MILESTONE_4_POWER_PROFILE.md`](MILESTONE_4_POWER_PROFILE.md) — Milestone 4 base implementation (binary profile)
- [`TDD_METHODOLOGY.md`](TDD_METHODOLOGY.md) — TDD testing methodology applied in the project
- [`../ROADMAP.md`](../ROADMAP.md) — Global project status and milestone prioritization

> 📌 Note: `MILESTONE_3_IMPLEMENTATION_PLAN.md`, `MILESTONE_3_ARCHITECTURE_ANALYSIS.md` and `MILESTONE_3_REFINEMENT.md`
> existed during M3 development but are not present in this branch. The CHANGELOG documents their content.

---

## ✅ Implementation Checklist

### Pre-Development
- [ ] Validate requirements with pilot users
- [ ] Create GitHub issues for each improvement
- [ ] Update ROADMAP.md with Milestone 4.1 status
- [ ] Set up testing environment for multiple vehicles

### Development
- [ ] **Sprint 1**: Smart Distributed Charging
  - [ ] TDD tests (5-7 tests)
  - [ ] Core implementation
  - [ ] EMHASS integration
  - [ ] Production validation (1 vehicle)
  
- [ ] **Sprint 2**: Multiple Vehicles
  - [ ] TDD tests (8-10 tests)
  - [ ] Balancing architecture
  - [ ] Power limits
  - [ ] Production validation (2+ vehicles)

- [ ] **Sprint 3**: UI + Notifications
  - [ ] TDD tests (7-9 tests)
  - [ ] Backend for UI
  - [ ] Lovelace dashboard
  - [ ] Notification system

- [ ] **Sprint 4**: Climate + Battery Health
  - [ ] TDD tests (7-9 tests)
  - [ ] Climate integration
  - [ ] Battery health mode
  - [ ] Complete validation

### Post-Development
- [ ] Update CHANGELOG.md with v0.5.0 entry
- [ ] Update ROADMAP.md marking M4.1 completed
- [ ] Create GitHub release
- [ ] User satisfaction survey

---

**Document Version**: 1.1  
**Last Updated**: 2026-04-09  
**Status**: 📋 PLANNED — NOT STARTED  
**Next Review**: Start of Sprint 1 (Distributed Charging)
