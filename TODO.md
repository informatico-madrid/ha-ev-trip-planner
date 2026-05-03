# TODO / BACKLOG — EV Trip Planner

> **Last updated**: 2026-05-03
> **Current version**: 0.5.23
> This file reflects the actual project state. For detailed milestone plans, see docs in `docs/`.

---

## ✅ Completed

### Milestone 0 — Project Foundation
- Repository structure, initial config flow, HACS metadata, MIT license

### Milestone 1 — Core Infrastructure
- Trip manager (recurrent + punctual), CRUD services, basic sensors, base dashboard
- TDD applied: 83% coverage, 29 tests

### Milestone 2 — Trip Calculations
- Sensors: `next_trip`, `next_deadline`, `kwh_today`, `hours_today`
- Recurrent trip expansion (7 days), timezone handling, recurrent + punctual combination

### Milestone 3 — EMHASS Integration & Smart Control (v0.3.0-dev, Dec 2025)
- `emhass_adapter.py`: Dynamic index assignment per trip (pool 0-49), persistence in HA Storage
- `vehicle_controller.py`: Strategy pattern (Switch / Service / Script / External)
- `schedule_monitor.py`: Real-time EMHASS schedule monitoring
- `presence_monitor.py`: Sensor or coordinate-based detection (Haversine), pre-action safety logic
- 156 tests, 93.6% passing

### Milestone 3.1 — Configuration UX Improvements (v0.3.1-dev, Dec 2025)
- Entity filters in config flow (SOC→battery class, Plugged→binary_sensor...)
- Help texts with concrete examples on all fields
- Complete Spanish translations

### Milestone 3.2 — Advanced Configuration (v0.4.0-dev, Mar 2026)
- Dynamic battery capacity (direct sensor / SOH% + nominal / manual)
- Consumption profiles by trip type (urban / highway / mixed)
- Auto-cleanup of past punctual trips (configurable)
- Complete 5-step config flow
- 398 tests, 85%+ coverage

### Milestone 4 — Smart Charging Profile (completed, Mar 2026)
- `sensor.{vehicle}_power_profile` sensor: 168-value array (24h x 7d) in Watts
- `deferrables_schedule` attribute with ISO 8601 timestamps
- Binary SOC-aware strategy: 0W = no charge, positive value = charging power
- Dashboard auto-import (full + simple) on config flow completion
- Retry logic: 3 attempts in 5-minute window

### SOLID Refactoring (current branch, Apr 2026)
- `protocols.py`: Formal interfaces to decouple dependencies
- `definitions.py`: Centralized entities, eliminating duplicates
- `coordinator.py`: Decoupled via dependency injection
- `diagnostics.py`: HACS quality diagnostic support
- Target: >80% coverage in all modules post-refactor

---

## 🔄 In Progress

- [ ] Achieve >80% coverage in all modules after SOLID refactoring
- [ ] Fix tests that failed due to interface changes after refactor
- [ ] Review and consolidate documentation (ROADMAP, README, docs/)

---

## 📌 Backlog — Milestone 4.1 (not started)

> Detailed plan in [`docs/MILESTONE_4_1_PLANNING.md`](docs/MILESTONE_4_1_PLANNING.md)

- [ ] **Smart distributed charging** (HIGH): Distribute charge in cheap hours (price integration with EMHASS)
- [ ] **Multi-vehicle support** (HIGH): Balancing with configurable home power limit
- [ ] **Climate adjustment** (MEDIUM): Adjust kWh by outside temperature (+20% cold, +10% hot)
- [ ] **Charging profile UI** (MEDIUM): Lovelace chart with active hours and price per hour
- [ ] **Proactive notifications** (MEDIUM): Pre-charge reminder, incomplete charge alert, weekly summary
- [ ] **Battery health mode** (LOW): Configurable daily SOC limit, slow charge preference

---

## 🔮 Future (post v1.0)

- [ ] Input normalization (days with/without accent, vehicle slugs)
- [ ] Origin-destination by address / coordinates (geocoding API)
- [ ] Conversational interface / voice (HA Assist)
- [ ] HA calendar integration (show trips as events)
- [ ] Consumption statistics and history
- [ ] Support for other optimizers (not just EMHASS)
- [ ] Multi-user fleet management

---

## ⚠️ Known Limitations (Active)

| Limitation | Impact | Workaround |
|---|---|---|
| Manual EMHASS configuration required | Less plug-and-play | README includes configuration snippet |
| Fixed planning horizon (7 days by default) | Does not adapt dynamically | User can adjust in config |
| Maximum 50 simultaneous indices (EMHASS pool) | Practical limit of active trips | Sufficient for home use |
| Multi-vehicle control without power balancing | May overload installation | Pending in M4.1 |

---

## ☠️ Obsolete / No Longer Applies

- **Slider migration** (`import_from_sliders`): Migration is optional and only relevant for pre-M3 configuration users. New users use config flow directly.
- **Manual 48h validation**: Superseded by 793 automatic tests + CI/CD suite.
- **Vehicle type selection (hybrid/electric)**: Removed from config flow in v0.4.1-dev as irrelevant.

---

## 🔧 Process Notes (Internal Use)

### Goose Agent — Output Truncation

**Symptom**: When using `RALPH_AGENT=claude`, the log only shows the final response (`TASK_COMPLETE`), not the full reasoning.

**Cause**: vLLM model (qwen3-5-35b-a3b-nvfp4) truncates the response. The full prompt is sent correctly but output is limited by the tokenizer.

**Workaround**: Use Claude for complex tasks where reasoning matters. Goose is adequate for simple tasks where only the final result matters.
