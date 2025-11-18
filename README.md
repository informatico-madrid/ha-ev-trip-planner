# 🚗 EV Trip Planner for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0--dev-blue)](https://github.com/informatico-madrid/ha-ev-trip-planner)

Plan your Electric Vehicle trips and let Home Assistant optimize charging schedules automatically.

## ✨ Features

- 📅 **Weekly Routine Planning**: Define your recurring trips (work, gym, etc.)
- 🎯 **One-time Trips**: Add specific trips with exact dates and times
- 🔋 **Smart Calculations**: Automatic kWh and charging hours estimation
- ⚡ **Deadline Management**: System knows when your car needs to be ready
- 📊 **Beautiful Dashboard**: Visual overview of your trips and vehicle status
- 🔌 **Universal Compatibility**: Works with any EV integration (Tesla, OVMS, Renault, etc.)
- 💰 **Optimizer Integration**: Optional integration with EMHASS or custom optimizers
- 🎤 **Voice Commands**: (Coming soon) Plan trips with voice assistants

## 🚀 Status

**Current Version**: 0.1.0-dev (In active development)

This integration is being developed incrementally. Check [Issues](https://github.com/informatico-madrid/ha-ev-trip-planner/issues) for current progress and roadmap.

## 📋 Requirements

- Home Assistant 2024.1 or newer
- An EV integration providing at least:
  - Battery SOC (State of Charge) sensor
  - Battery capacity (kWh)
  - Charging power (kW)

## 🏗️ Supported Use Cases

### ✅ Currently Supported (v0.1.0-dev)
- Single vehicle with manual or automatic charge control
- Recurring weekly trips (your routine)
- Punctual one-time trips (specific events)
- Basic calculations and deadline management

### 🚧 Planned (v0.2+)
- Multiple vehicles
- Shared charging line management
- EMHASS integration
- Voice command support
- Advanced optimization

## 📦 Installation

### HACS (Recommended - Coming Soon)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click "+" and search for "EV Trip Planner"
4. Click "Download"
5. Restart Home Assistant

### Manual Installation

1. Copy `custom_components/ev_trip_planner` to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click "+" and search for "EV Trip Planner"
5. Follow the configuration wizard

## ⚙️ Configuration

The integration uses a configuration flow (UI-based setup). You'll need to provide:

### Basic Configuration
- **Vehicle Name**: Friendly name for your EV (e.g., "Tesla Model 3")
- **Vehicle Type**: EV or PHEV
- **SOC Sensor**: Entity ID of your battery level sensor
- **Battery Capacity**: Total battery capacity in kWh
- **Charging Power**: Your charger's power in kW
- **Consumption**: Average kWh per km (default: 0.15)

### Optional Configuration
- **Range Sensor**: Entity ID for remaining range
- **Charging Status**: Binary sensor indicating if charging
- **Charge Control**: Configuration for automatic charging control
- **Optimizer Integration**: Connect to EMHASS or custom optimizer

## 📖 Usage

### Planning Recurring Trips

1. Go to your EV Trip Planner dashboard
2. In the "Weekly Routine" section, click on a day
3. Add your recurring trips (e.g., "Work" Monday-Friday at 09:00)

### Planning One-time Trips

1. In the "Punctual Trips" section
2. Click "Add Trip"
3. Enter destination, date, time, and distance
4. System calculates kWh needed and schedules charging

### Checking Status

The dashboard shows:
- Current battery level and range
- Next scheduled trip
- Time remaining until trip
- Charging status and schedule

## 🎨 Screenshots

*Coming soon - Integration in active development*

## 🤝 Contributing

Contributions are welcome! This project is in active development.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a Pull Request

## 🐛 Bug Reports & Feature Requests

Please use [GitHub Issues](https://github.com/informatico-madrid/ha-ev-trip-planner/issues) to report bugs or request features.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Home Assistant community
- EMHASS project for optimization inspiration
- All EV integration developers

## 📊 Roadmap

- [x] Initial project structure
- [ ] Core trip management (v0.1)
- [ ] Basic dashboard (v0.1)
- [ ] Charge control automation (v0.1)
- [ ] Multi-vehicle support (v0.2)
- [ ] EMHASS integration (v0.2)
- [ ] Voice commands (v0.3)
- [ ] Advanced optimization (v0.3)

## 💬 Community

- **Issues**: [GitHub Issues](https://github.com/informatico-madrid/ha-ev-trip-planner/issues)
- **Discussions**: [GitHub Discussions](https://github.com/informatico-madrid/ha-ev-trip-planner/discussions)

---

**Note**: This integration is under active development. Features and documentation will evolve rapidly. Star ⭐ the repo to follow progress!
