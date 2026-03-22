# Research: Playwright E2E Testing para Home Assistant

## Introduction

Esta investigación documenta las mejores prácticas y decisiones técnicas para implementar testing E2E con Playwright que verifique la creación del panel nativo en Home Assistant.

## Decisions

### Decision 1: Usar Playwright Test Framework

**What**: Implementar testing E2E con Playwright

**Why**:
- Playwright ofrece mejor manejo de waits automáticos (no requiere explicit waits)
- Mejor soporte para múltiples browsers y contextos
- Mayor velocidad de ejecución
- Mejor manejo de iframes y shadow DOM
- Mejor documentación y comunidad activa
- Soporte nativo para TypeScript y JavaScript

**Alternatives Considered**:
- **Cypress**: Excelente DX pero limitado a Chrome/Firefox/Webkit, más lento
- **Selenium**: Framework más antiguo, requiere más código boilerplate, menos feature-rich
- **Puppeteer**: Solo Chrome/Chromium, menos feature-rich que Playwright

### Decision 2: Usar Page Objects Pattern

**What**: Implementar tests con pattern de Page Objects para mejor mantenibilidad

**Why**:
- Separar lógica de navegación de assertions
- Facilitar mantenimiento cuando cambia la UI
- Reusar código entre tests
- Mejor legibilidad de los tests

**Implementation**:
```javascript
// Page Object para Integraciones
class IntegrationsPage {
  constructor(page) {
    this.page = page;
  }

  async addIntegration(name) {
    await this.page.click('button:has-text("Integrar integración")');
    await this.page.fill('input[type="search"]', name);
    await this.page.click('a:has-text("' + name + '")');
  }
}
```

### Decision 3: Captura de Logs y Errores

**What**: Usar event listeners de Playwright para capturar console logs y page errors

**Why**:
- Debugging más efectivo cuando los tests fallan
- Identificar errores de JavaScript en el navegador
- Capturar warnings y mensajes importantes
- Generar reportes más informativos

**Implementation**:
```javascript
const logs = [];
const errors = [];

page.on('console', msg => {
  logs.push({ type: 'console', text: msg.text() });
});

page.on('pageerror', error => {
  errors.push({ type: 'error', message: error.message });
});
```

### Decision 4: Verificación con Home Assistant API

**What**: Usar la API REST de Home Assistant para verificar entidades y servicios

**Why**:
- Verificación independiente del navegador (más rápida y confiable)
- No requiere renderizar UI para verificar estado
- Más fácil de hacer assertions sobre datos
- Mejor performance que verificar elementos DOM

**Implementation**:
```javascript
const axios = require('axios');

async function verifyEntities(haUrl, token) {
  const response = await axios.get(`${haUrl}/api/states`, {
    headers: { Authorization: `Bearer ${token}` }
  });

  return response.data.filter(e => e.entity_id.includes('ev_trip_planner'));
}
```

### Decision 5: Screenshots para Debugging

**What**: Generar screenshots automáticos cuando hay fallos o al completar el test

**Why**:
- Debugging visual de problemas de UI
- Evidence para reportar bugs
- Capturar estado exacto cuando falla
- Mejor reporting de tests

**Implementation**:
```javascript
// Screenshot en caso de fallo
test('example', async ({ page }) => {
  try {
    await page.click('button');
  } catch (error) {
    await page.screenshot({ path: 'failure.png' });
    throw error;
  }
});
```

## Technical Specifications

### Test Configuration

```javascript
// playwright.config.js
module.exports = {
  testMatch: '**/*.spec.js',
  timeout: 120000, // 2 minutos max por test
  use: {
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
  },
  webServer: {
    command: 'npm run start', // Si se requiere servidor
    url: 'http://localhost:3000',
    timeout: 120000,
  },
};
```

### Test Structure

```javascript
const { test, expect } = require('@playwright/test');
const axios = require('axios');

test.describe('EV Trip Planner - Native Panel E2E', () => {
  let page;
  let context;

  test.beforeEach(async ({ browser }) => {
    // Setup: Crear contexto y página
    context = await browser.newContext();
    page = await context.newPage();

    // Setup: Event listeners para captura de logs
    const logs = [];
    page.on('console', msg => logs.push(msg.text()));
    page.on('pageerror', error => logs.push(`ERROR: ${error.message}`));
  });

  test.afterEach(async () => {
    // Cleanup: Cerrar contexto
    await context.close();
  });

  test('Crear integración y verificar panel', async () => {
    // Step 1: Login
    await page.goto('http://ha.local:8123/login');
    await page.fill('input[type="email"]', 'malka');
    await page.fill('input[type="password"]', 'Darkpunk666/');
    await page.click('button[type="submit"]');
    await page.waitForSelector('ha-panel-lovelace');

    // Step 2: Navegar a integraciones
    await page.goto('http://ha.local:8123/config/integrations');

    // Step 3: Agregar integración EV Trip Planner
    await page.click('button:has-text("Integrar integración")');
    await page.click('a:has-text("EV Trip Planner")');

    // Step 4: Configurar vehículo
    await page.fill('input[name="name"]', 'Test Vehicle');
    await page.click('button[type="submit"]');

    // Step 5: Verificar panel
    const sidebarPanels = await page.$$('ha-side-nav-menu-item');
    const hasEvPanel = sidebarPanels.some(panel =>
      panel.textContent().toLowerCase().includes('ev')
    );

    expect(hasEvPanel).toBe(true);
  });
});
```

## Summary

- **Framework**: Playwright Test (mejor balance performance/feature)
- **Pattern**: Page Objects para mantenibilidad
- **Verification**: Combinar verificación DOM + API de HA
- **Debugging**: Capturar logs, errores y screenshots
- **Timeout**: 120 segundos max por test
