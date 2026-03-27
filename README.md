# 🚗⚡ EV Trip Planner para Home Assistant

**Planifica viajes eléctricos y optimiza el consumo energético de tu vehículo**

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg
  ?style=for-the-badge)](https://github.com/custom-components/hacs)
[![Versión](https://img.shields.io/badge/version-0.4.0--dev-blue.svg
  ?style=for-the-badge)](https://github.com/tu-usuario/ha-ev-trip-planner/releases)
[![Licencia](https://img.shields.io/badge/license-MIT-green.svg
  ?style=for-the-badge)](https://opensource.org/licenses/MIT)

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
  - [🤖 Agente ha-e2e-test-architect](#-agente-ha-e2e-test-architect)
  - [🧩 Skills Externas (Opcionales)](#-skills-externas-opcionales)
  - [📊 Valor de la Ventaja](#-valor-de-la-ventaja)
  - [Documentación de Testing E2E](#documentación-de-testing-e2e)
  - [Estructura del proyecto](#estructura-del-proyecto)

---

## 🎯 Características

### ✅ Milestone 2 - Gestión de Viajes (COMPLETADO)
- **🗓️ Viajes Recurrentes**: Programa viajes diarios/semanales (trabajo, compras)
- **📅 Viajes Puntuales**: Planifica viajes únicos con fecha/hora específica
- **🔋 Optimización**: Calcula energía necesaria basada en distancia y eficiencia
- **📱 Sensores en Tiempo Real**: 7 sensores automáticos con actualización reactiva
- **🎛️ Dashboard incluido**: Panel Lovelace preconfigurado

### ✅ Milestone 3 - Integración EMHASS (COMPLETADO)
- **⚡ Integración con EMHASS**: Optimización energética con horarios dinámicos
- **🎮 Control de Vehículo**: 4 estrategias (switch, service, script, external)
- **🏠 Detección de Presencia**: Sensor y coordenadas para seguridad
- **🔔 Notificaciones Inteligentes**: Alertas cuando carga necesaria pero no posible
- **🔄 Asignación de Índices**: Múltiples viajes por vehículo sin conflictos

### ✅ Milestone 4 - Perfil de Carga Inteligente (COMPLETADO)
- **📊 Perfil de Carga Binario**: 0W o máxima potencia, distribuido inteligentemente
- **🔋 Cálculo SOC-Aware**: Considera batería actual y margen de seguridad del 40%
- **⚠️ Alertas de Tiempo**: Notifica si no hay tiempo suficiente para cargar
- **📈 Sensor de Perfil**: Perfil de potencia con 168 horas de planificación
- **🧠 Optimización Inteligente**: Distribuye carga justo antes de cada viaje

### 🚀 Milestone 4.1 - Próximas Mejoras (PLANIFICADO)
- **⚡ Carga Distribuida**: Distribuir en múltiples horas con optimización de costes
- **🚗 Múltiples Vehículos**: Soporte para 2+ vehículos con balanceo de carga
- **🌡️ Predicción Climática**: Ajusta consumo según temperatura
- **📊 UI Mejorada**: Gráficos de perfil de carga en dashboard

---

## ⚠️ Prerrequisitos

### Para Usuarios Finales (Producción)
- Home Assistant Core ≥ 2023.8.0 o Supervisor
- HACS (Home Assistant Community Store) instalado
- Acceso a "Modo Avanzado" en tu perfil de HA
- **Opcional**: EMHASS instalado para optimización energética

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
     $HOME/homeassistant/custom_components/
   ```

3. **Corrige permisos**:
   ```bash
   chown -R 1000:1000 $HOME/homeassistant/custom_components/ev_trip_planner
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
   cd $PROJECT_ROOT
   git clone https://github.com/tu-usuario/ha-ev-trip-planner.git
   cd ha-ev-trip-planner
   ```

2. **Crea enlace simbólico** (para desarrollo en caliente):
   ```bash
   ln -sf $PROJECT_ROOT/custom_components/ev_trip_planner \
     $HOME/homeassistant/custom_components/ev_trip_planner
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

1. **Después de añadir la integración**, el asistente te guiará a través de **4 pasos simplificados**:

   - **Paso 1 - Vehículo**: Solo necesitas el nombre del vehículo (ej. "Chispitas", "Morgan")
   - **Paso 2 - Sensores**: Capacidad de batería, potencia de carga, consumo
   - **Paso 3 - EMHASS** (opcional): Configuración de optimización energética
   - **Paso 4 - Control** (opcional): Tipo de control y notificaciones

2. **Traducción completa al español**: Todos los pasos, mensajes y campos de ayuda están en español, incluyendo sugerencias claras para los sensores opcionales.

3. **Dashboard automático**: Al completar la configuración, el dashboard de Lovelace se importa automáticamente a tu sistema.

4. **Los sensores se crearán automáticamente**:
   - `sensor.{vehiculo}_trips_list`
   - `sensor.{vehiculo}_recurring_trips_count`
   - `sensor.{vehiculo}_punctual_trips_count`
   - Y sensores adicionales según la configuración

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

## ⚡ Integración EMHASS

### ¿Qué es EMHASS?

**EMHASS** (Energy Management for Home Assistant) es un optimizador energético
que gestiona cargas diferibles (como la carga de vehículos eléctricos) para
aprovechar tarifas variables y energía renovable.

### Configuración EMHASS

Al configurar tu vehículo, puedes configurar estos parámetros EMHASS:

| Parámetro | Descripción | Valor recomendado |
|-----------|-------------|-------------------|
| Planning Horizon | Días de planificación (1-365) | 7 días |
| Max Deferrable Loads | Cargas simultáneas (10-100) | 50 |
| Planning Sensor | Sensor de horizonte (opcional) | - |

### Ejemplo de shell command

Para conectar EV Trip Planner con EMHASS, añade esto en tu
`configuration.yaml`:

```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -H "Content-Type: application/json" -X POST -d '{
      "P_deferrable": {{ (state_attr(
        'sensor.emhass_perfil_diferible_{vehicle_id}',
        'power_profile_watts'
      ) | default([0]*168)) | tojson }}
    }' http://$EMHASS_IP:5000/action/dayahead-optim
```

**Nota**: Reemplaza `$EMHASS_IP` con la IP de tu servicio EMHASS (ej: `192.168.1.201`).

### Sensores de carga diferible

El sistema crea sensores de plantilla con atributos:

- `sensor.emhass_perfil_diferible_{vehicle_id}` - Perfil de potencia
- `power_profile_watts` - Array de 168 valores (1 semana)
- `deferrables_schedule` - Detalle por hora

### Verificar integración

1. **Dashboard**: Ve al dashboard `ev-trip-planner-{vehiculo}`
2. **Sensores**: Busca `sensor.emhass_perfil_diferible_*`
3. **Logs**: Busca "emhass" en registros para errores

---

## 🚗 Control de Vehículo

### Tipos de control

EV Trip Planner soporta 4 estrategias de control:

| Tipo | Descripción | Cuándo usarlo |
|------|-------------|---------------|
| **None** | Sin control | Solo notificaciones |
| **Switch** | Controla un switch | Wallbox con switch entity |
| **Service** | Llama a un servicio | Integración con servicio |
| **Script** | Ejecuta un script | Carga con script HA |
| **External** | Notificaciones only | Solo avisa, no controla |

### Configuración de control

#### Switch (Recomendado)

1. Selecciona "Switch" como tipo de control
2. Elige el switch de carga (ej: `switch.wallbox_charging`)
3. El sistema encenderá/apagará el switch según EMHASS

#### Service

1. Selecciona "Service" como tipo de control
2. Proporciona el ID del servicio (ej: `button.start_charging`)
3. El sistema llamará al servicio cuando sea necesario

#### Script

1. Selecciona "Script" como tipo de control
2. Elige el script (ej: `script.charge_vehicle`)
3. El sistema ejecutará el script para iniciar/detener carga

#### External / Notificaciones Only

1. Selecciona "Notificaciones Only"
2. Solo recibirás alertas cuando la carga sea necesaria
3. No se realiza ningún control automático

### Detección de presencia

Para un funcionamiento seguro, el sistema verifica:

- **Sensor de carga**: ¿El vehículo está cargando? (OBLIGATORIO)
- **Sensor de hogar**: ¿El vehículo está en casa?
- **Sensor de enchufe**: ¿Está conectado el cable?

### Flujo de control

```
EMHASS optimiza → Trip Planner recibe → ¿Vehículo en casa?
    → Sí → ¿Enchufado? → Sí → Activar carga
    → No → Enviar notificación
```

### Notificaciones

Cuando la carga sea necesaria pero no se pueda ejecutar:

- "Vehículo no en casa - No se puede cargar"
- "Vehículo no enchufado - No se puede cargar"
- "Carga activada para viaje a {destino}"

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

**⚠️ IMPORTANTE**: Las actualizaciones no borran tus viajes (usan Storage API).

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
   rm -rf $HOME/homeassistant/custom_components/ev_trip_planner
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

- **Los viajes ahora persisten entre reinicios**: El sistema usa Storage API de Home Assistant para guardar los viajes de forma persistente.
- **Verifica permisos**:
  ```bash
  ls -la $HOME/homeassistant/.storage/ | grep ev_trip_planner
  ```
- Debe tener permisos `1000:1000` (usuario homeassistant)
- Los archivos se guardan en `.storage/ev_trip_planner_{vehicle_id}.json`

### El dashboard no se importa automáticamente

- **Verifica que Lovelace está disponible**: El sistema necesita que Lovelace esté configurado en Home Assistant.
- **Mira los logs**:
  ```bash
  docker logs homeassistant --tail 50 | grep ev_trip_planner
  ```
- Busca mensajes como "Lovelace not available" o "Dashboard imported successfully"
- El dashboard se sobrescribe automáticamente si ya existe

---

## 📊 Desarrollo

### 🤖 Agente ha-e2e-test-architect

Tu agente de testing E2E personal que **aprende y mejora continuamente**.

#### ¿Qué hace tu agente?

| Función | Cómo te ayuda | Ejemplo real |
|---------|---------------|--------------|
| **Detecta anti-patrones** | Identifica automáticamente código frágil | `waitForTimeout` → `expect().toBeVisible()` |
| **Sugiere correcciones** | Aplica patterns conocidos sin que pidas | XPath → `getByRole` |
| **Documenta lecciones** | Guarda automáticamente lo aprendido | `feedback_selectors.md` |
| **Recuerra contextos** | No pierdes conocimiento entre sesiones | "getByRole('listitem') no funciona en HA" |

#### Lo que tu agente ya sabe

**Lecciones aprendidas (guardadas automáticamente):**
- `feedback_verification.md` - Regla de verificación obligatoria
- `feedback_selectors.md` - Lecciones sobre selectores
- `scripts_location.md` - Dónde están los scripts
- `skill_path.md` - Ruta correcta del SKILL.md

#### Cómo usar tu agente de testing ha-e2e-test-architect

**Cuando un test falla:**

```typescript
// ❌ Test falla con "locator timeout"
await expect(page.getByRole('listitem', { name: /EV Trip Planner/i }))
  .toBeVisible()

// ✅ Tu agente detecta el problema y sugiere:
// "getByRole('listitem') no funciona en Shadow DOM"
// "Usar getByText en vez de getByRole('listitem')"

// ✅ Tu agente aplica la corrección automáticamente:
await expect(page.getByText('EV Trip Planner'))
  .toBeVisible()
```

**Cuando necesitas debugging:**

```bash
# Tu agente sabe qué script usar
# (solo pídeselo y te lo ejecuta)
node ~/.agents/skills/ha-e2e-testing/scripts/inspect_dom.js http://127.0.0.1:8271/config/integrations

# OUTPUT:
# 🔒 Elementos con Shadow DOM (150):
#    • <ha-list-item> role="listitem"
#    • <generic> role="generic" (no listitem!)
```

**Cuando escribes tests nuevos:**

```typescript
// Tu agente recuerda patrones exitosos
// y te sugiere correcciones automáticamente

// ❌ Anti-patrón detectado
await page.waitForTimeout(1000)

// ✅ Tu agente sugiere:
await expect(page.getByRole('button', { name: /Save/i }))
  .toBeVisible({ timeout: 10000 })
```

## 📊 Valor Real

**Antes del agente:**
- Agente detecta y corrige anti-patrones
- Autenticación configurada automáticamente
- Patrones aplicados sin pensar

**Lo más importante:** Tu agente **nunca olvida** las lecciones aprendidas. Cada test fallido se convierte en conocimiento persistente.

## 🧩 Plugins y Skills Necesarias

### 🤖 Agente Incluido en el Repositorio

**Listo para usar !** Este proyecto incluye tu agente de testing E2E directamente en el repositorio:

**Agente incluido:**
- `.claude/agents/ha-e2e-test-architect.md` - Agente especializado en E2E testing para Home Assistant

**Memorias incluidas (local):**
- `.claude/agent-memory-local/ha-e2e-test-architect/MEMORY.md` - Índice de memorias
- `.claude/agent-memory-local/ha-e2e-test-architect/feedback_selectors.md` - Lecciones sobre selectores
- `.claude/agent-memory-local/ha-e2e-test-architect/feedback_verification.md` - Regla de verificación
- `.claude/agent-memory-local/ha-e2e-test-architect/scripts_location.md` - Ubicación de scripts
- `.claude/agent-memory-local/ha-e2e-test-architect/skill_path.md` - Ruta del SKILL.md

**Nota sobre Engram:**
El agente menciona herramientas Engram (`engram_*`), pero Engram es un plugin local instalado en `~/.claude/plugins/`. Las memorias en `.claude/agent-memory-local/` son archivos markdown locales que el agente puede leer, pero no usan el sistema Engram MCP.

**Configuración incluida:**
- `.claude/commands/*.md` - Comandos disponibles (speckit workflows)
- `.claude/settings.local.json` - Configuración local (NO en git, se genera automáticamente)

**Nota sobre settings.json:**
`.claude/settings.json` contiene credenciales y configuración personal, por lo tanto ha sido eliminado del repositorio. Se genera automáticamente cuando configuras el agente localmente.

### 🧩 Skills Externas (Opcionales)

Las skills adicionales se instalan en tu configuración personal de Claude:

**Skills recomendadas:**

| Skill | Comando de instalación |
|-------|----------------------|
| **playwright-best-practices** | `git clone https://github.com/tu-usuario/playwright-best-practices.git ~/.agents/skills/` |
| **home-assistant-best-practices** | `git clone https://github.com/tu-usuario/home-assistant-best-practices.git ~/.agents/skills/` |

**Activar en settings.json:**

```json
{
  "skills": {
    "playwright-best-practices": true,
    "home-assistant-best-practices": true
  }
}
```

**Nota:** Las skills son opcionales. El agente ha-e2e-test-architect.md incluido en el repositorio funciona con o sin ellas.

### 📊 Valor de la Ventaja

**¿Qué obtienes al clonar este repositorio?**

1. ✅ **Agente ha-e2e-test-architect.md** - Especializado en E2E testing para Home Assistant
2. ✅ **Memorias locales** - Lecciones aprendidas guardadas en archivos markdown
3. ✅ **Comandos speckit** - workflows disponibles en `.claude/commands/`
4. ✅ **Documentación técnica** - docs/ con patrones, debugging y guía completa
5. ✅ **Lecciones aprendidas** - feedback_selectors.md, feedback_verification.md, etc.

**Nota:** `.claude/settings.json` contiene credenciales personales y NO está en git. Se genera automáticamente cuando configuras el agente localmente.

**¿Qué necesitas instalar adicionalmente (opcional)?**

- Engram plugin - `npx skillhub@latest install engram` (opcional, para memoria MCP)
- Skills externas (playwright-best-practices, home-assistant-best-practices) - opcionales
- Scripts de testing (opcionalmente, disponibles en ~/.agents/skills/)

**Resultado profesional:** Clona el repositorio y tu agente ya funciona con:
- ✅ Conocimiento encapsulado en el agente
- ✅ Memoria local (archivos markdown) - puedes ver y editar las lecciones
- ✅ Patrones documentados - puedes replicar el workflow
- ✅ Debugging especializado - scripts y herramientas incluidas

**Diferencia clave:** A diferencia de otros proyectos que solo tienen código, este incluye tu **agente de testing especializado** y su **conocimiento acumulado**. Es como tener un QA senior documentado en el repositorio.

**Nota sobre Engram:** Las herramientas Engram (`engram_*`) mencionadas en el agente requieren instalar el plugin Engram localmente. Si no lo instalas, el agente funcionará sin memoria persistente MCP, pero las memorias en `.claude/agent-memory-local/` seguirán siendo accesibles como archivos markdown.

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
cd $PROJECT_ROOT
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
- **Discusiones**: [GitHub
  Discussions](https://github.com/tu-usuario/ha-ev-trip-planner/discussions)
- **Documentación**: [Wiki](https://github.com/tu-usuario/ha-ev-trip-planner/wiki)

---

**⭐ Si te gusta este componente, dale una estrella en GitHub!**