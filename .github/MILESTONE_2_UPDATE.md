Update on Milestone 2 - Trip Calculations

I've completed the basic trip calculation logic for the EV Trip Planner integration. Here's what's working:

**Implemented:**
- 4 new sensors that calculate: next trip, deadline countdown, kWh needed today, and charging hours required
- Logic to expand recurring trips for 7 days and combine with punctual trips
- Timezone-aware calculations using zoneinfo
- Real-time sensor updates when trips are added/modified
- 66/66 tests passing with 86% coverage

**Current Limitations:**
- Still using hardcoded vehicle efficiency (0.15 kWh/km) and charging power (3.7kW)
- No EMHASS integration yet - this is purely informational
- Basic error handling only
- Single vehicle support only

**Next Steps:**
The sensors now provide the data structure needed for EMHASS, but the actual integration (Milestone 3) will require:
- Configurable vehicle parameters
- Data export format for EMHASS consumption
- Hybrid mode that can fall back to manual sliders
- Extensive testing with real MPC runs

**Repository:** https://github.com/informatico-madrid/ha-ev-trip-planner  
**Current Tag:** v0.2.0-dev

If you're following the development, the calculation logic is in `trip_manager.py` and the sensors are in `sensor.py`. All tests are in the `tests/` folder.

The integration is functional for trip management and calculations, but not yet ready to replace manual MPC configuration. Milestone 3 will focus on the actual EMHASS integration with proper safety measures and rollback capability.