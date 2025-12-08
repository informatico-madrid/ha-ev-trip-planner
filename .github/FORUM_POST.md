# 🚗⚡ New Integration: EV Trip Planner (Beta) - Trip Management + EMHASS Optimization

Hi everyone! 👋

I've been working on a new Home Assistant integration to solve a common EV owner problem: **planning trips and ensuring your car is charged when you need it**.

**🎯 Key Focus**: This integration is designed to work seamlessly with **EMHASS (Energy Management for Home Assistant)** and other optimizers, providing them with your trip schedule so they can optimize charging times based on your actual needs, energy prices, and solar production.

## 🎯 The Problem

Most EV integrations show you the current battery level, but they don't help you plan ahead:
- When do I need to charge for my morning commute?
- How much energy do I need for this weekend trip?
- Can I delay charging to use cheaper/greener electricity?

## 💡 The Solution: EV Trip Planner

This integration lets you:

✅ **Plan Your Routine**: Define recurring trips (work, gym, school run)  
✅ **Add One-Time Trips**: Special events, road trips, etc.  
✅ **Get Smart Calculations**: Automatic kWh and charging time estimates  
✅ **Optimize with EMHASS**: Designed to feed your trip schedule into EMHASS/MPC optimizers  
✅ **See Everything**: Beautiful dashboard with weekly grid and trip list  
✅ **Stay Flexible**: Works with ANY EV integration (Tesla, OVMS, Renault, etc.)

### 🔋 EMHASS Integration (Coming in Milestone 3)

The **primary goal** of this integration is to replace manual charging schedules with **intelligent, trip-based planning**:

- **Instead of**: Setting fixed SOC targets and hardcoded departure times
- **You get**: Dynamic charging schedules that adapt to your actual trips
- **EMHASS will**: Optimize charging times based on:
  - Your trip deadlines (when you actually need the car)
  - Energy prices (charge when electricity is cheap)
  - Solar production (maximize self-consumption)
  - Grid constraints (avoid peak hours)

**Current workaround**: Many EMHASS users manually adjust deferrable loads or use complex automations. This integration will make it seamless.  

### 📊 Current Status (v0.1.0-milestone1)

**✅ What works NOW (Available Today):**
- Basic trip planning (add/edit/delete trips manually)
- Store recurring weekly trips (e.g., "work every Monday at 9am")
- Store one-time trips (e.g., "road trip on Dec 25")
- View your trips in sensors and dashboard
- Full UI-based configuration

**⚠️ What does NOT work yet:**
- ❌ No automatic calculations (you manually enter kWh needed)
- ❌ No EMHASS integration (that's the goal!)
- ❌ No automatic charging control
- ❌ No deadline management
- ❌ Currently **informational only** - you still need to manage charging manually

**🚧 Coming in Milestone 2 (~1 week):**
- ⏳ Calculate next trip deadline automatically
- ⏳ Calculate kWh needed per day
- ⏳ Calculate required charging hours
- ⏳ Sensors ready for optimizer consumption

**🎯 Coming in Milestone 3 (~2-3 weeks) - THE GOAL:**
- ⏳ Direct EMHASS MPC integration
- ⏳ Automatic deferrable load configuration
- ⏳ Multi-vehicle support with shared charging line
- ⏳ Smart deadline management (no more hardcoded cutoffs!)
- ⏳ Full trip-based optimization

### 🎬 Quick Demo

Once installed and configured, you get sensors like:
```yaml
sensor.my_ev_trips_list: 3
  # attributes show all your trips with details
sensor.my_ev_recurring_trips_count: 1
sensor.my_ev_punctual_trips_count: 2
```

And services to manage trips:
```yaml
service: ev_trip_planner.add_recurring_trip
data:
  vehicle_id: "My EV"
  dia_semana: "lunes"
  hora: "09:00"
  km: 24
  kwh: 3.6
  descripcion: "Trabajo"
```

### 📦 Installation

**Via HACS (Custom Repository):**
1. Go to HACS > Integrations > ⋮ (menu) > Custom repositories
2. Add: `https://github.com/informatico-madrid/ha-ev-trip-planner`
3. Category: Integration
4. Install and restart HA

**Manual:**
1. Copy `custom_components/ev_trip_planner` to your config directory
2. Restart Home Assistant
3. Add via Configuration > Integrations

### 🔗 Links

- **GitHub Repository**: https://github.com/informatico-madrid/ha-ev-trip-planner
- **Latest Release**: v0.1.0-milestone1
- **Roadmap**: See full development plan in the repo
- **License**: MIT

### ⚠️ Important: This is an EARLY BETA

**Current state (v0.1.0):**
- ✅ You CAN: Plan and store your trips
- ❌ You CANNOT: Have automatic charging optimization (yet!)
- 📝 It's a trip **planner** but not yet a trip **optimizer**

**Why release now?**
- Get early feedback on the UX and data model
- Let EMHASS users see where this is going
- Build in public with community input

**Tested with:**
- Home Assistant 2024.11+
- OVMS integration
- Should work with any EV integration that provides SOC sensor

**Bottom line**: This is the foundation. The magic (EMHASS integration) comes in ~2-3 weeks.

### 🤝 Feedback Welcome!

I'm following a TDD approach and building incrementally. Would love to hear:
- What features would be most useful for YOU?
- What EV/charger setup do you have?
- **Are you using EMHASS?** How do you currently handle trip planning?
- Any bugs or issues you encounter?

**Special interest**: If you're already using EMHASS or other optimizers, I'd love to hear about your current workflow and pain points. This integration is being built specifically to solve those! 🎯

This is my first public HA integration, so constructive feedback is greatly appreciated! 🙏

### 🎯 Roadmap Preview

- **Milestone 2** (next, ~1 week): Trip calculations and deadline management
- **Milestone 3** (~2 weeks): **EMHASS/MPC Integration** - The main goal! 🎯
- **Milestone 4**: Multi-vehicle support with shared charging line
- **v1.0**: Stable release with full optimizer integration

---

**TL;DR**: New integration for planning EV trips with **EMHASS optimizer integration** as the primary goal. Currently beta but functional for trip management. Building toward intelligent, price-optimized charging based on your actual travel needs. Feedback from EMHASS users especially welcome!

Let me know what you think! 🚗⚡
