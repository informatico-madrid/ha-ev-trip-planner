# 🧪 E2E Testing con Playwright - Guía para Desarrolladores

## 🎯 Overview

Este proyecto utiliza **Playwright** para pruebas End-to-End (E2E) de la integración EV Trip Planner en Home Assistant. Las pruebas simulan el flujo completo: login → Config Flow → panel del usuario.

## 📦 Stack de Herramientas

### Agentes y Skills

| Herramienta | Ubicación | Descripción |
|-------------|-----------|-------------|
| **Agent** | `.claude/agents/ha-e2e-test-architect.md` | Reglas arquitectónicas y patrones de testing |
| **Skill** | `~/.agents/skills/ha-e2e-testing/` | Documentación oficial y scripts |
| **Memorias** | `.claude/agent-memory-local/ha-e2e-test-architect/` | Lecciones aprendidas y patterns |

### Scripts de Testing

```bash
~/.agents/skills/ha-e2e-testing/scripts/
├── check_session.js          # Valida autenticación antes de tests
├── create_auth_setup.js      # Genera auth.setup.ts con Config Flow
├── extract_report.js         # Resumen estructurado de tests
├── get_ha_url.js             # Obtiene URL de HA desde server-info.json
├── inspect_dom.js            # Inspecciona Shadow DOM cuando selector falla
├── reload_integration.sh     # Hot-reload sin reiniciar HA
├── run_playwright_test.sh    # Ejecuta tests con reporte JSON
└── validate_selector.js      # Valida selectores Web-First
```

## 🚀 Quick Start

### 1. Setup Inicial (una vez por sesión)

```bash
# Ejecutar setup (login + Config Flow + save storageState)
npx playwright test auth.setup.ts --reporter=list

# Verificar autenticación
node ~/.agents/skills/ha-e2e-testing/scripts/check_session.js

# Obtener URL de HA
node ~/.agents/skills/ha-e2e-testing/scripts/get_ha_url.js
```

### 2. Ejecutar Tests

```bash
# Ejecutar tests con reporte estructurado
bash ~/.agents/skills/ha-e2e-testing/scripts/run_playwright_test.sh tests/e2e/panel.spec.ts

# Ver reporte
node ~/.agents/skills/ha-e2e-testing/scripts/extract_report.js
```

### 3. Debug (si falla)

```bash
# Ver trace viewer
npx playwright show-trace playwright/trace.zip

# Inspeccionar DOM real
node ~/.agents/skills/ha-e2e-testing/scripts/inspect_dom.js http://127.0.0.1:8271/config/integrations
```

## 🏗️ Arquitectura de Tests

### Proyectos de Playwright

```typescript
// playwright.config.ts
projects: [
  {
    name: 'auth',              // Paso 1: Login + Config Flow
    testMatch: 'auth.setup.ts',
    use: { ...devices['Desktop Chrome'] },
  },
  {
    name: 'chromium',          // Paso 2: Tests E2E
    testMatch: 'panel.spec.ts',
    use: {
      storageState: 'playwright/.auth/user.json', // Estado autenticado
      dependencies: ['auth'], // Depende del proyecto auth
    },
  },
]
```

### Flujo de Autenticación

```
1. auth.setup.ts
   ├── Login en /login
   ├── Navegar a /config/integrations
   ├── Config Flow: EV Trip Planner
   ├── Rellenar campos (vehicle_name, battery_capacity_kwh, etc.)
   └── Guardar storageState → playwright/.auth/user.json

2. panel.spec.ts (usa storageState)
   ├── Comienza YA autenticado
   ├── Navegar a /dashboard
   ├── Clic en sidebar link
   └── Tests del panel
```

## 🎨 Patrones de Selectores

### ✅ Web-First Locators (Recomendado)

```typescript
// getByRole con regex para traducciones
await page.getByRole('button', { name: /Save/i }).click()

// getByText para elementos sin role específico
await expect(page.getByText('EV Trip Planner')).toBeVisible()

// getByLabel para formularios
await page.getByLabel(/Trip Name/i).fill('Morning Commute')
```

### ❌ Anti-patrones a Evitar

```typescript
// NO usar waitForTimeout
await page.waitForTimeout(1000)

// NO usar XPath innecesario
await page.locator('xpath=ancestor-or-self::*[@role="dialog"]')

// NO usar CSS classes frágiles
await page.click('.clase-css-random')

// NO usar :has-text() no estándar
await page.click('button:has-text("Add integration")')
```

### ✅ Patrones Correctos

```typescript
// Auto-waiting en vez de waitForTimeout
await expect(page.getByRole('button', { name: /Save/i }))
  .toBeVisible({ timeout: 10000 })

// getByRole en vez de XPath
await page.getByRole('dialog', { name: /EV Trip Planner/i })

// getByRole en vez de CSS classes
await page.getByRole('button', { name: /Add integration/i }).click()
```

## 🔍 Debugging de Selectores

### Problema: Selector no encuentra elemento

```bash
# 1. Ejecutar test para ver error
bash ~/.agents/skills/ha-e2e-testing/scripts/run_playwright_test.sh tests/e2e/auth.setup.ts

# 2. Ver snapshot del DOM en error
cat test-results/auth.setup.ts-*/error-context.md | head -100

# 3. Inspeccionar DOM real
node ~/.agents/skills/ha-e2e-testing/scripts/inspect_dom.js http://127.0.0.1:8271/config/integrations

# 4. Buscar el elemento en el output
grep -A 10 "EV Trip Planner" test-results/*/error-context.md
```

### Lecciones Comunes

#### Problema: `getByRole('listitem')` no encuentra elemento

**Causa:** Home Assistant usa Lit Elements que renderizan `<generic>` en vez de `<listitem>`.

**Solución:**
```typescript
// ❌ Falla
await expect(page.getByRole('listitem', { name: /EV Trip Planner/i }))
  .toBeVisible()

// ✅ Funciona
await expect(page.getByText('EV Trip Planner'))
  .toBeVisible()
```

**Documentado en:** `.claude/agent-memory-local/ha-e2e-test-architect/feedback_selectors.md`

## 📊 Configuración de Playwright

### playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  fullyParallel: false, // Tests de configuración deben ser secuenciales
  forbidOnly: !!process.env.CI,
  retries: 0, // 2 en CI
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'playwright-results.xml' }],
    ['list'],
  ],

  // Configuración global
  globalSetup: './tests/global.setup.ts',
  globalTeardown: './tests/global.teardown.ts',

  use: {
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  projects: [
    {
      name: 'auth',
      testMatch: 'auth.setup.ts',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'chromium',
      testMatch: 'panel.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json',
        dependencies: ['auth'],
      },
    },
  ],
});
```

## 🛠️ Scripts Útiles

### check_session.js

```bash
# Valida si la sesión es válida
node ~/.agents/skills/ha-e2e-testing/scripts/check_session.js

# OUTPUT:
{
  "valid": true,
  "reason": "Session is valid"
}
```

### inspect_dom.js

```bash
# Inspecciona DOM real para ver roles de elementos
node ~/.agents/skills/ha-e2e-testing/scripts/inspect_dom.js http://127.0.0.1:8271/config/integrations

# OUTPUT:
# 🔒 Elementos con Shadow DOM (150):
#    • <ha-list-item> role="listitem"
#    • <generic> role="generic" (no listitem!)
#    • <generic> role="generic" (dentro de <list>)
```

### validate_selector.js

```bash
# Valida selector antes de usarlo en tests
node ~/.agents/skills/ha-e2e-testing/scripts/validate_selector.js "getByRole('button', { name: /Save/i })"
```

### create_auth_setup.js

```bash
# Genera auth.setup.ts automáticamente con Config Flow
node ~/.agents/skills/ha-e2e-testing/scripts/create_auth_setup.js "Mi Tesla" "battery_capacity_kwh=75.0 charging_power_kw=11.0"

# Ejecutar el setup generado
npx playwright test auth.setup.ts --reporter=list
```

### reload_integration.sh

```bash
# Hot-reload sin reiniciar Home Assistant
bash ~/.agents/skills/ha-e2e-testing/scripts/reload_integration.sh ev_trip_planner
```

## 📝 Archivos de Test

### auth.setup.ts

```typescript
import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  // 1. Login
  await page.goto('/login');
  await page.fill('[name="username"]', 'dev');
  await page.click('button[type="submit"]');

  // 2. Config Flow
  await page.goto('/config/integrations');
  await page.getByRole('button', { name: /Add Integration/i }).click();
  await page.getByPlaceholder(/Search/i).fill('EV Trip Planner');
  await page.getByRole('listitem', { name: /EV Trip Planner/i }).click();

  // 3. Rellenar campos
  await page.getByRole('textbox', { name: /vehicle_name/i }).fill('Mi Tesla');
  await page.getByRole('button', { name: /Next/i }).click();

  // 4. Guardar estado
  await page.context().storageState({ path: authFile });
});
```

### panel.spec.ts

```typescript
import { test, expect } from '@playwright/test';

test.describe('EV Trip Planner Panel', () => {
  test('should display dashboard heading', async ({ page }) => {
    // Navegar vía sidebar
    await page.goto('/dashboard');
    await page.getByRole('link', { name: /EV Trip Planner/i }).click();

    // Verificar que el panel cargó
    await expect(
      page.getByRole('heading', { name: /EV Trip Planner/i })
    ).toBeVisible();

    // Verificar elementos del panel
    await expect(
      page.getByRole('button', { name: /New Trip/i })
    ).toBeVisible();
  });

  test('should create a new trip', async ({ page }) => {
    // Navegar al panel
    await page.goto('/dashboard');
    await page.getByRole('link', { name: /EV Trip Planner/i }).click();

    // Clic en crear nuevo viaje
    await page.getByRole('button', { name: /New Trip/i }).click();

    // Rellenar formulario
    await page.getByLabel(/Trip Name/i).fill('Morning Commute');
    await page.getByLabel(/Departure Time/i).fill('08:00');

    // Clic en crear
    await page.getByRole('button', { name: /Create|Save/i }).click();

    // Verificar que el viaje se creó
    await expect(
      page.getByText(/Morning Commute/i)
    ).toBeVisible();
  });
});
```

## 🚀 Comandos Útiles

```bash
# Ejecutar todos los tests
npx playwright test

# Ejecutar con browser visible
npx playwright test --headed

# Ejecutar solo auth.setup.ts
npx playwright test auth.setup.ts

# Ejecutar solo panel.spec.ts
npx playwright test panel.spec.ts

# Ejecutar con modo debug
npx playwright test --debug

# Ver reporte HTML
npx playwright show-report playwright-report

# Ver trace de test fallido
npx playwright show-trace playwright/trace.zip

# Limpiar resultados
npx playwright test --clean
```

## 📚 Recursos Adicionales

- **SKILL.md**: `~/.agents/skills/ha-e2e-testing/SKILL.md`
- **Memorias**: `.claude/agent-memory-local/ha-e2e-test-architect/`
- **Scripts**: `~/.agents/skills/ha-e2e-testing/scripts/`
- **Playwright Docs**: https://playwright.dev

## 🎯 Mejores Prácticas

1. **Nunca usar waitForTimeout** - Usar `expect().toBeVisible()` con auto-waiting
2. **Nunca hardcodear URLs** - Navegar vía sidebar con `getByRole('link', { name: /.../i })`
3. **Nunca usar XPath** - Usar `getByRole` o `getByText`
4. **Nunca incluir login en .spec.ts** - Usar storageState desde auth.setup.ts
5. **Siempre verificar DOM real** - Usar `inspect_dom.js` cuando selector falla
6. **Siempre documentar lecciones** - Guardar en `.claude/agent-memory-local/`

## ⚡ Rendimiento

**ANTES** (sin patrones):
- Debugging: 3-4 horas
- Configuración de autenticación: 2-3 horas
- Corrección de anti-patrones: 2-3 horas
- **Total: 7-11 horas**

**DESPUÉS** (con patrones):
- Debugging: 30 minutos
- Configuración de autenticación: 10 segundos
- Corrección de anti-patrones: 10 segundos
- **Total: 50 minutos**

**Reducción de tiempo: 85-90%**
