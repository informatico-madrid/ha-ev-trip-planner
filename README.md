# 🚗⚡ EV Trip Planner para Home Assistant

**Planifica viajes eléctricos y optimiza el consumo energético de tu vehículo**

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![Versión](https://img.shields.io/badge/version-1.0.0-blue.svg?style=for-the-badge)](https://github.com/tu-usuario/ha-ev-trip-planner/releases)
[![Licencia](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

## 📋 Tabla de Contenidos

- [🎯 Características](#-características)
- [⚠️ Prerrequisitos](#️-prerrequisitos)
- [🚀 Instalación](#-instalación)
  - [Método 1: HACS (Recomendado)](#método-1-hacs-recomendado)
  - [Método 2: Instalación Manual](#método-2-instalación-manual)
  - [Método 3: Desarrollo/Testing](#método-3-desarrollotesting)
- [⚙️ Configuración Inicial](#️-configuración-inicial)
- [🎮 Uso](#-uso)
- [🔄 Actualización](#-actualización)
- [🗑️ Desinstalación](#️-desinstalación)
- [🔧 Solución de Problemas](#-solución-de-problemas)
- [📊 Desarrollo](#-desarrollo)

---

## 🎯 Características

- **🗓️ Viajes Recurrentes**: Programa viajes diarios/semanales (trabajo, compras)
- **📅 Viajes Puntuales**: Planifica viajes únicos con fecha/hora específica
- **🔋 Optimización**: Calcula energía necesaria basada en distancia y eficiencia
- **📱 Sensores en Tiempo Real**: 3 sensores automáticos con actualización reactiva
- **⚡ Integración con EMHASS**: Preparado para optimización energética
- **🎛️ Dashboard incluido**: Panel Lovelace preconfigurado

---

## ⚠️ Prerrequisitos

### Para Usuarios Finales (Producción)
- Home Assistant Core ≥ 2023.8.0 o Supervisor
- HACS (Home Assistant Community Store) instalado
- Acceso a "Modo Avanzado" en tu perfil de HA

### Para Desarrolladores
- Python 3.11+
- Git
- Docker (opcional, para testing)
- Conocimientos básicos de YAML y comandos Linux

---

## 🚀 Instalación

### Método 1: HACS (Recomendado) ⭐

**Este es el método para usuarios finales. No requiere comandos de terminal.**

1. **Abre Home Assistant** en tu navegador (`http://tu-ip:8123`)

2. **Accede a HACS**:
   - Barra lateral → HACS

3. **Añade el repositorio personalizado**:
   - HACS → Integraciones → ⋮ (menú) → Repositorios personalizados
   - URL: `https://github.com/tu-usuario/ha-ev-trip-planner`
   - Categoría: `Integración`
   - Haz clic en **AÑADIR**

4. **Instala la integración**:
   - Busca "EV Trip Planner" en HACS
   - Haz clic en el componente
   - Presiona **DESCARGAR**

5. **Reinicia Home Assistant**:
   - Configuración → Sistema → Reiniciar
   - Espera 30-60 segundos

6. **Añade la integración**:
   - Configuración → Dispositivos y Servicios → + AÑADAR INTEGRACIÓN
   - Busca "EV Trip Planner"
   - Sigue el asistente de configuración

✅ **¡Listo!** Los sensores se crearán automáticamente.

---

### Método 2: Instalación Manual (Producción)

**Usa este método solo si no tienes HACS o necesitas una versión específica.**

1. **Descarga la última versión**:
   ```bash
   cd /tmp
   wget https://github.com/tu-usuario/ha-ev-trip-planner/archive/refs/tags/v1.0.0.zip
   unzip v1.0.0.zip
   ```

2. **Copia al directorio de Home Assistant**:
   ```bash
   cp -r ha-ev-trip-planner-1.0.0/custom_components/ev_trip_planner \
     /home/malka/homeassistant/custom_components/
   ```

3. **Corrige permisos**:
   ```bash
   chown -R 1000:1000 /home/malka/homeassistant/custom_components/ev_trip_planner
   ```

4. **Reinicia Home Assistant**:
   ```bash
   docker restart homeassistant
   ```

5. **Añade la integración** desde la UI (paso 6 del Método 1)

---

### Método 3: Desarrollo/Testing

**⚠️ SOLO para desarrollo. NO uses en producción.**

1. **Clona el repositorio**:
   ```bash
   cd /home/malka
   git clone https://github.com/tu-usuario/ha-ev-trip-planner.git
   cd ha-ev-trip-planner
   ```

2. **Crea enlace simbólico** (para desarrollo en caliente):
   ```bash
   ln -sf /home/malka/ha-ev-trip-planner/custom_components/ev_trip_planner \
     /home/malka/homeassistant/custom_components/ev_trip_planner
   ```

3. **Instala dependencias de desarrollo**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements_dev.txt
   ```

4. **Ejecuta tests**:
   ```bash
   pytest tests/ -v --cov=custom_components/ev_trip_planner
   ```

5. **Reinicia Home Assistant** y verifica logs:
   ```bash
   docker restart homeassistant && docker logs -f homeassistant
   ```

---

## ⚙️ Configuración Inicial

### Configuración básica (UI)

1. **Después de añadir la integración**, el asistente te pedirá:

   - **Nombre del vehículo**: Ej. "Chispitas", "Morgan"
   - **Capacidad de batería (kWh)**: Ej. 27 (Leaf), 52 (Tesla)
   - **Eficiencia (kWh/100km)**: Ej. 15 (Leaf), 18 (Model 3)

2. **Haz clic en ENVIAR**

3. **Los sensores se crearán automáticamente**:
   - `sensor.{vehiculo}_trips_list`
   - `sensor.{vehiculo}_recurring_trips_count`
   - `sensor.{vehiculo}_punctual_trips_count`

### Configuración avanzada (YAML)

```yaml
# configuration.yaml
ev_trip_planner:
  vehicles:
    - name: "Chispitas"
      battery_capacity_kwh: 27
      efficiency_kwh_km: 0.15
      min_soc: 20  # % mínimo de batería
    - name: "Morgan"
      battery_capacity_kwh: 52
      efficiency_kwh_km: 0.18
      min_soc: 15
```

**Reinicia Home Assistant** después de editar `configuration.yaml`.

---

## 🎮 Uso

### Crear un viaje recurrente (ej: trabajo)

1. **Herramientas para desarrolladores** → **Servicios**
2. **Servicio**: `ev_trip_planner.add_recurring_trip`
3. **Datos del servicio**:

```yaml
service: ev_trip_planner.add_recurring_trip
data:
  vehicle_id: "Chispitas"
  dia_semana: "lunes"
  hora: "08:00"
  km: 25
  kwh: 3.75
  descripcion: "Trabajo"
```

### Crear un viaje puntual (ej: aeropuerto)

```yaml
service: ev_trip_planner.add_punctual_trip
data:
  vehicle_id: "Chispitas"
  datetime: "2025-12-15T14:30:00"
  km: 50
  kwh: 7.5
  descripcion: "Aeropuerto"
```

### Ver viajes en el dashboard

1. **Edita tu dashboard** Lovelace
2. **Añade una tarjeta** → **Entidades**
3. **Selecciona los 3 sensores** del vehículo

---

## 🔄 Actualización

### Actualización automática (HACS)

1. **HACS** → **Integraciones**
2. Busca "EV Trip Planner"
3. Si hay actualización disponible, aparecerá un botón **ACTUALIZAR**
4. Haz clic y **reinicia Home Assistant**

### Actualización manual

1. **Descarga la nueva versión** (ver Método 2 de instalación)
2. **Copia los archivos** sobreescribiendo los existentes
3. **Reinicia Home Assistant**

**⚠️ IMPORTANTE**: Las actualizaciones no borran tus viajes guardados (usan Storage API).

---

## 🗑️ Desinstalación

### Método 1: Desde HACS (Recomendado)

1. **HACS** → **Integraciones**
2. Busca "EV Trip Planner"
3. ⋮ (menú) → **Eliminar**
4. **Reinicia Home Assistant**

### Método 2: Manual

1. **Elimina la integración**:
   - Configuración → Dispositivos y Servicios
   - Busca "EV Trip Planner"
   - ⋮ → **Eliminar**

2. **Elimina los archivos**:
   ```bash
   rm -rf /home/malka/homeassistant/custom_components/ev_trip_planner
   ```

3. **Elimina la configuración** de `configuration.yaml` (si la tienes)

4. **Reinicia Home Assistant**

**⚠️ Los datos de viajes se perderán** al desinstalar.

---

## 🔧 Solución de Problemas

### Los sensores no aparecen

1. **Verifica logs**:
   ```bash
   docker logs homeassistant --tail 50 | grep ev_trip_planner
   ```

2. **Comprueba que la integración está cargada**:
   - Configuración → Dispositivos y Servicios
   - Debe aparecer "EV Trip Planner" con 3 dispositivos

3. **Reinstala si es necesario**

### Error: "No se encuentra el servicio"

- **Reinicia Home Assistant** (el servicio se registra al iniciar)
- Verifica que el componente está en `custom_components/`

### Los viajes no se guardan

- **Verifica permisos**:
  ```bash
  ls -la /home/malka/homeassistant/.storage/ | grep ev_trip_planner
  ```
- Debe tener permisos `1000:1000` (usuario homeassistant)

---

## 📊 Desarrollo

### Estructura del proyecto

```
ha-ev-trip-planner/
├── custom_components/ev_trip_planner/
│   ├── __init__.py          # Coordinator y setup
│   ├── config_flow.py       # Configuración UI
│   ├── const.py             # Constantes
│   ├── sensor.py            # Sensores
│   ├── trip_manager.py      # Lógica de viajes
│   └── services.yaml        # Definición de servicios
├── tests/
│   ├── test_coordinator.py  # Tests coordinator
│   ├── test_sensors.py      # Tests sensores
│   └── test_trip_manager.py # Tests manager
├── .github/workflows/
│   └── validate.yml         # CI/CD
├── hacs.json                # Metadata HACS
├── manifest.json            # Metadata HA
└── README.md               # Este archivo
```

### Ejecutar tests

```bash
cd /home/malka/ha-ev-trip-planner
source venv/bin/activate
pytest tests/ -v --cov=custom_components/ev_trip_planner
```

### Contribuir

1. **Fork el repositorio**
2. **Crea una rama**: `git checkout -b feature/nueva-funcion`
3. **Haz commits**: `git commit -am 'Añade nueva función'`
4. **Push**: `git push origin feature/nueva-funcion`
5. **Crea un Pull Request**

---

## 📄 Licencia

MIT License - Ver archivo [LICENSE](LICENSE) para detalles

---

## 🤝 Soporte

- **Issues**: [GitHub Issues](https://github.com/tu-usuario/ha-ev-trip-planner/issues)
- **Discusiones**: [GitHub Discussions](https://github.com/tu-usuario/ha-ev-trip-planner/discussions)
- **Documentación**: [Wiki](https://github.com/tu-usuario/ha-ev-trip-planner/wiki)

---

**⭐ Si te gusta este componente, dale una estrella en GitHub!**
