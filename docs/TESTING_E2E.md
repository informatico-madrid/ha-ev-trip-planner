# Guía de Tests E2E — EV Trip Planner

Esta guía explica cómo ejecutar los tests End-to-End (Playwright) tanto **en local** como en el **pipeline de CI**. La configuración es 100% compatible entre ambos entornos.

---

## Índice

1. [Cómo funcionan los tests](#cómo-funcionan-los-tests)
2. [Prerrequisitos](#prerrequisitos)
3. [Ejecución en Local — Opción A (Docker Compose, recomendado)](#opción-a-docker-compose-recomendado)
4. [Ejecución en Local — Opción B (hass manual)](#opción-b-hass-manual-sin-docker)
5. [Ejecución en CI (GitHub Actions)](#ejecución-en-ci-github-actions)
6. [Estructura de los tests](#estructura-de-los-tests)
7. [Usuarios y autenticación](#usuarios-y-autenticación)
8. [Comandos útiles](#comandos-útiles)
9. [Resolución de problemas](#resolución-de-problemas)

---

## Cómo funcionan los tests

```
npm run test:e2e
       │
       ├─► auth.setup.ts (globalSetup — se ejecuta UNA vez al inicio)
       │     ├─ Espera a que HA responda en http://localhost:8123
       │     ├─ Llama a la REST API de HA para crear el usuario "dev/dev" (si no existe)
       │     ├─ Configura la integración ev_trip_planner via Config Flow REST API
       │     │     vehicle_name = "test_vehicle"
       │     │     charging_sensor = "input_boolean.test_ev_charging"
       │     └─ Guarda la sesión autenticada en playwright/.auth/user.json
       │
       ├─► tests/e2e/*.spec.ts  (cada test)
       │     ├─ Carga la sesión guardada (storageState)
       │     ├─ Navega directamente a /ev-trip-planner-test_vehicle
       │     ├─ Realiza la acción (crear/editar/borrar viaje...)
       │     └─ Limpia los datos creados
       │
       └─► globalTeardown.ts  (limpia ficheros temporales)
```

**Puntos clave:**
- HA **debe estar corriendo** antes de ejecutar `npx playwright test`. La suite NO arranca HA.
- La autenticación se hace vía **trusted_networks** (sin login form, bypass automático desde 127.0.0.1).
- La integración se configura via REST API en `auth.setup.ts`, no vía UI.
- El panel se registra en la barra lateral con el nombre `test_vehicle`.
- La navegación al panel usa la URL directa `/ev-trip-planner-test_vehicle`.

---

## Prerrequisitos

### Todos los entornos

```bash
# Node.js ≥ 18 (comprobar)
node --version

# Instalar dependencias Node
npm install

# Instalar Chromium (solo se necesita Chromium)
npx playwright install chromium --with-deps
```

### Solo para ejecución local (sin Docker)

```bash
# Python 3.11-3.12
python3 --version

# Instalar Home Assistant
pip install homeassistant
```

### Solo para ejecución con Docker

```bash
# Docker + docker compose
docker --version
docker compose version
```

---

## Opción A: Docker Compose (recomendado)

Esta es la forma más sencilla y reproducible. El `docker-compose.yml` ya está configurado con:
- `trusted_networks` para bypass de login desde localhost.
- `input_boolean.test_ev_charging` necesario para el Config Flow.
- Volumen montando `custom_components/ev_trip_planner` desde el repo local.

### 1. Arrancar Home Assistant

```bash
# Desde la raíz del repositorio
docker compose up -d

# Comprobar que HA está listo (espera ~30-60 segundos)
docker compose logs -f homeassistant
# Ctrl+C cuando veas: "Home Assistant is running"
```

### 2. Completar el onboarding de HA (solo la primera vez)

Cuando HA arranca por primera vez en Docker, necesita el **onboarding inicial** (crear usuario admin). Tienes dos opciones:

**Opción A1 — Onboarding automático vía script:**
```bash
./scripts/ha-onboard.sh
```

**Opción A2 — Onboarding manual vía UI:**
1. Abre http://localhost:8123 en el navegador.
2. Crea el usuario: nombre=`Developer`, usuario=`dev`, contraseña=`dev`.
3. Acepta todas las pantallas hasta llegar al dashboard.

> ⚠️ Las credenciales `dev`/`dev` están hardcodeadas en `auth.setup.ts`. Si usas otras credenciales, edita ese fichero.

### 3. Ejecutar los tests

```bash
# Ejecutar todos los tests E2E
npx playwright test tests/e2e/ --workers=1

# O con make
make test-e2e

# Con navegador visible (para ver qué hace)
make test-e2e-headed

# Un solo fichero
npx playwright test tests/e2e/create-trip.spec.ts

# En modo debug (pausa en cada paso)
make test-e2e-debug
```

### 4. Parar Home Assistant

```bash
docker compose down
```

---

## Opción B: hass manual (sin Docker)

Útil si ya tienes Python instalado y prefieres no usar Docker.

### 1. Instalar Home Assistant

```bash
pip install homeassistant
```

### 2. Preparar el directorio de configuración

```bash
# Crear directorio de config para tests
mkdir -p /tmp/ha-e2e-config/custom_components

# Enlazar la configuración de test
cp tests/ha-manual/configuration.yaml /tmp/ha-e2e-config/configuration.yaml

# Enlazar el custom component
ln -sf $(pwd)/custom_components/ev_trip_planner \
       /tmp/ha-e2e-config/custom_components/ev_trip_planner
```

### 3. Arrancar Home Assistant

```bash
nohup hass -c /tmp/ha-e2e-config > /tmp/ha-e2e.log 2>&1 &
echo "HA PID: $!"

# Esperar a que esté listo (~30-60 segundos)
until curl -sf -o /dev/null -w "%{http_code}" http://localhost:8123/api/ | grep -qE "401|200"; do
  echo "Esperando HA..."
  sleep 3
done
echo "HA listo!"
```

### 4. Completar el onboarding (solo la primera vez)

```bash
# Script automático
./scripts/ha-onboard.sh

# O abre http://localhost:8123 y créate el usuario dev/dev manualmente
```

### 5. Ejecutar los tests

```bash
npx playwright test tests/e2e/ --workers=1
```

### 6. Parar Home Assistant

```bash
kill $(cat /tmp/ha-pid.txt) 2>/dev/null
# o
pkill -f "hass -c /tmp/ha-e2e-config"
```

---

## Ejecución en CI (GitHub Actions)

El workflow `.github/workflows/playwright.yml` reproduce exactamente los pasos de la Opción B:

1. Checkout del código.
2. Instala Node y dependencias (`npm install`, `npx playwright install chromium`).
3. Instala `homeassistant` via pip.
4. Copia la configuración de test a `/tmp/ha-e2e-config/`.
5. Arranca `hass -c /tmp/ha-e2e-config` en background.
6. Espera a que la API responda (`HTTP 401`).
7. Completa el onboarding automáticamente via REST API.
8. Ejecuta `npx playwright test tests/e2e/ --workers=1`.
9. Sube artefactos (`playwright-report/`, `test-results/`, logs de HA).

**No hay diferencia** entre ejecutar en local (Opción B) y en CI — usan la misma configuración.

---

## Estructura de los tests

```
tests/e2e/
  trips-helpers.ts              # Helpers: createTestTrip, deleteTestTrip, navigateToPanel
  create-trip.spec.ts           # US-1: Crear viaje puntual y recurrente
  edit-trip.spec.ts             # US-2: Editar viaje existente
  delete-trip.spec.ts           # US-3: Eliminar viaje (confirmar / cancelar)
  pause-resume-trip.spec.ts     # US-4: Pausar y reanudar viaje recurrente
  complete-cancel-trip.spec.ts  # US-5: Completar y cancelar viaje puntual
  trip-list-view.spec.ts        # US-6: Vista lista, detalles, botones por tipo
  form-validation.spec.ts       # US-7: Campos del formulario, cambio de tipo, opciones
```

### Panel URL

El panel del vehículo de test se registra en:
```
http://localhost:8123/ev-trip-planner-test_vehicle
```

Cada test navega directamente a esta URL (la sesión autenticada está en `storageState`).

### Selectores usados

Los tests usan IDs de elemento (`#trip-type`, `#trip-km`, etc.) y texto visible:

| Elemento | Selector |
|----------|----------|
| Tipo de viaje | `page.locator('#trip-type')` |
| Distancia | `page.locator('#trip-km')` |
| Energía | `page.locator('#trip-kwh')` |
| Descripción | `page.locator('#trip-description')` |
| Fecha/hora | `page.locator('#trip-datetime')` |
| Día semana | `page.locator('#trip-day')` |
| Hora (recurrente) | `page.locator('#trip-time')` |
| Botón crear | `page.getByRole('button', { name: 'Crear Viaje' })` |
| Botón agregar | `page.getByRole('button', { name: '+ Agregar Viaje' })` |
| Guardar cambios | `page.getByRole('button', { name: 'Guardar Cambios' })` |
| Editar | `page.getByText('Editar')` |
| Eliminar | `page.locator('.delete-btn')` |
| Pausar | `page.getByText('Pausar')` |
| Completar | `page.getByText('Completar')` |

### Diálogos nativos

Los botones Eliminar/Pausar/Completar/Cancelar usan `confirm()` y `alert()` nativos del navegador. Los tests los manejan con:

```typescript
// Registrar handler ANTES de la acción
const dialogPromise = setupDialogHandler(page, true);  // true = aceptar
await tripCard.getByText('Eliminar').click();
const msg = await dialogPromise;
```

---

## Usuarios y autenticación

### Usuario de test

| Campo | Valor |
|-------|-------|
| Nombre | Developer |
| Username | `dev` |
| Password | `dev` |

Estas credenciales están hardcodeadas en `auth.setup.ts`. Cámbielas si usas un HA con credenciales diferentes.

### trusted_networks

La configuración `tests/ha-manual/configuration.yaml` incluye:

```yaml
homeassistant:
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - 127.0.0.1
        - 172.17.0.0/16
        - ::1
      allow_bypass_login: true
    - type: homeassistant
```

Esto permite que el navegador Playwright (desde 127.0.0.1) autentique automáticamente sin formulario de login.

### Sesión guardada

La sesión se guarda en `playwright/.auth/user.json` durante `globalSetup`. Este fichero está en `.gitignore` y se regenera en cada ejecución.

---

## Comandos útiles

```bash
# Ejecutar TODOS los tests E2E
make test-e2e

# Con navegador visible
make test-e2e-headed

# En modo debug interactivo (abre el Playwright Inspector)
make test-e2e-debug

# Solo un fichero de test
npx playwright test tests/e2e/form-validation.spec.ts

# Solo un test concreto (por nombre)
npx playwright test tests/e2e/ --grep "should create a new puntual trip"

# Ver informe HTML (tras una ejecución)
npx playwright show-report

# Tests Python (unitarios, sin E2E)
make test

# Todos los checks (Python + lint + mypy)
make check
```

---

## Resolución de problemas

### HA no arranca / tests fallan con "connection refused"

```bash
# Comprobar que HA está corriendo
curl -s -o /dev/null -w "%{http_code}" http://localhost:8123/api/

# Ver logs de HA
docker compose logs homeassistant   # si usas Docker
tail -50 /tmp/ha-e2e.log            # si usas hass manual
```

### "Integration already set up" o error en globalSetup

El `auth.setup.ts` detecta si la integración ya está configurada y la salta. Si hay un estado corrupto:

```bash
# Docker: eliminar volúmenes y recrear
docker compose down -v
docker compose up -d

# hass manual: limpiar configuración
rm -rf /tmp/ha-e2e-config/.storage
```

### "trusted_networks" no funciona / aparece formulario de login

Asegúrate de que `configuration.yaml` tiene la configuración correcta bajo `homeassistant:` (no a nivel raíz):

```yaml
# ✅ CORRECTO
homeassistant:
  auth_providers:
    - type: trusted_networks
      ...

# ❌ INCORRECTO (nivel raíz, no funciona en HA moderno)
auth_providers:
  - type: trusted_networks
    ...
```

### Lit no carga / panel en blanco

El panel usa `lit-bundle.js` servido localmente por HA. Si el panel aparece en blanco:

1. Abre http://localhost:8123/ev-trip-planner/lit-bundle.js — debe devolver código JS.
2. Si devuelve 404, reinicia HA para que registre los static paths.

### Tests lentos o timeouts

Los tests tienen un timeout de 60 segundos por test. Si el sistema es lento:

```typescript
// En playwright.config.ts, aumenta el timeout
timeout: 120_000,
```

### "strict mode violation" — el selector encuentra múltiples elementos

Algunos tests usan `getByText('15')` que puede coincidir con fecha Y con kWh. En ese caso, acota el scope al trip card:

```typescript
const tripCard = page.locator('.trip-card', { hasText: 'Mi Viaje' }).last();
await expect(tripCard.getByText('15 kWh')).toBeVisible();
```

---

## Variables de entorno

| Variable | Valor por defecto | Descripción |
|----------|------------------|-------------|
| `HA_URL` | `http://localhost:8123` | URL de Home Assistant |
| `CI` | (vacío) | Si es `"true"`, activa retries y formato CI |

Para cambiar la URL de HA (por ejemplo, si usas otro puerto):

```bash
HA_URL=http://localhost:8124 npx playwright test tests/e2e/
```

> Nota: `auth.setup.ts` usa la constante `HA_URL = 'http://localhost:8123'`. Edita ese fichero si necesitas un puerto diferente de forma permanente.
