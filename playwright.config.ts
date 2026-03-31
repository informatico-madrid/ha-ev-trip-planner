import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath, URL } from 'url'
import * as fs from 'fs'
import * as path from 'path'
const __dirname = fileURLToPath(new URL('.', import.meta.url))

/**
 * Playwright Test Configuration para EV Trip Planner E2E Testing
 *
 * ARQUITECTURA:
 * - Proyecto 'setup': Autenticación inicial con storageState
 * - Proyecto 'chromium': Tests principales que usan el estado guardado
 * - Patrón storageState: Login solo en setup, tests individuales sin código de login
 *
 * REGLAS:
 * - Cero waitForTimeout: Playwright auto-waiting por defecto
 * - Selectores semánticos: getByRole, getByText, getByLabel
 * - Aserciones async: await expect(). con retry automático
 */

export default defineConfig({
  // Directorio de tests
  testDir: './tests/e2e',

  // Ejecución paralela completa
  fullyParallel: true,

  // Prohibir tests en CI si hay fallos
  forbidOnly: !!process.env.CI,

  // Retries para tests flaky en CI
  retries: process.env.CI ? 2 : 0,

  // Workers limitados en CI para estabilidad
  workers: process.env.CI ? 1 : undefined,

  // Reporteros
  reporter: [
    ['html', {
      outputFolder: 'playwright-report',
      open: 'never'
    }],
    ['json', {
      outputFile: 'playwright-results.json'
    }],
    ['junit', {
      outputFile: 'playwright-results.xml'
    }]
  ],

  // Configuración global
  use: {
    // Base URL para navegación relativa
    // Leer la URL del servidor HA desde server-info.json (creado por globalSetup)
    baseURL: (() => {
      const authDir = path.join(__dirname, 'playwright', '.auth');
      const serverInfoPath = path.join(authDir, 'server-info.json');
      try {
        const serverInfo = JSON.parse(fs.readFileSync(serverInfoPath, 'utf-8'));
        return new URL(serverInfo.link).origin;
      } catch (error) {
        console.warn('Could not read server-info.json, using default localhost:8123');
        return 'http://localhost:8123';
      }
    })(),

    // Trace en primer retry para debugging
    trace: 'on-first-retry',

    // Screenshot solo en fallos
    screenshot: 'only-on-failure',

    // Video solo en fallos
    video: 'retain-on-failure',

    // Timeouts razonables
    actionTimeout: 10000,
    navigationTimeout: 30000,


    // Deshabilitar Service Workers para evitar cacheo agresivo de JS en HA
    serviceWorkers: 'block'
  },

  // Proyectos
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Inyecta el estado de autenticación guardado por 'setup'
        storageState: 'playwright/.auth/user.json'
      },
      dependencies: ['setup']
    }
  ],

  // Global setup para crear servidor HA efímero
  globalSetup: './tests/global.setup.ts',

  // Global teardown para cleanup
  globalTeardown: './tests/global.teardown.ts',

  // Sin webServer - hass-taste-test maneja el servidor HA efímero
  // El panel.js se copia después de que HA arranca (líneas 43-55 de global.setup.ts)
  // Esto funciona porque hass-taste-test crea el directorio www/ antes de iniciar HA
})
