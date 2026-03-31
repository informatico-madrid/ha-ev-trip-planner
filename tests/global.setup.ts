/**
 * Global Setup - Server Lifecycle
 *
 * This file is executed once before all tests.
 * It only starts the ephemeral HA server - NO browser interactions.
 */

import { chromium, FullConfig } from '@playwright/test';
import { HomeAssistant, PlaywrightBrowser } from 'hass-taste-test';
import * as fs from 'fs';
import * as path from 'path';

async function globalSetup(config: FullConfig) {
  console.log('[GlobalSetup] Starting ephemeral HA server...');

  const evTripPlannerPath = path.join(process.cwd(), 'custom_components/ev_trip_planner');
  const panelJsPath = path.join(evTripPlannerPath, 'frontend/panel.js');
  const rootDir = process.cwd();

  // Start ephemeral HA with the custom component
  // Use input_boolean to create presence detection entities
  // These will be used by the EntitySelector in the Config Flow
  // input_boolean works consistently in both local and CI environments
  const hassInstance = await HomeAssistant.create(`
input_boolean:
  binary_sensor_coche1_cargando:
    name: "Coche1 Cargando"
  binary_sensor_coche1_en_casa:
    name: "Coche1 En Casa"
  binary_sensor_coche1_enchufado:
    name: "Coche1 Enchufado"

lovelace:
  mode: storage
  resources:
    - url: /local/panel.js
      type: module
`, {
    python: process.env.PYTHON_PATH || 'python3',
    browser: new PlaywrightBrowser('chromium'),
    customComponents: [evTripPlannerPath],
  });

  // Copy panel.js to www directory AFTER HA starts
  // The panel component registers its own static paths
  const wwwDir = (hassInstance as any).configDir;
  fs.mkdirSync(wwwDir, { recursive: true });
  const wwwPath = path.join(wwwDir, 'www');
  fs.mkdirSync(wwwPath, { recursive: true });

  if (!fs.existsSync(panelJsPath)) {
    throw new Error(`Source file not found: ${panelJsPath}`);
  }

  fs.copyFileSync(panelJsPath, path.join(wwwPath, 'panel.js'));
  console.log('[GlobalSetup] Copied panel.js to:', path.join(wwwPath, 'panel.js'));

  // NOTE: global.setup.ts NO LONGER creates config entry via API.
  // The auth.setup.ts test handles the FULL UI Config Flow - this IS the E2E test.
  // This follows test-automator and ha-e2e-testing skills: Test Isolation, No API bypass.

  // Wait for HA to be fully ready
  console.log('[GlobalSetup] Waiting for HA to be ready...');
  await new Promise(resolve => setTimeout(resolve, 10000));

  // Save server info to a file for other setups to use
  const authDir = path.join(rootDir, 'playwright', '.auth');
  fs.mkdirSync(authDir, { recursive: true });
  const serverInfoPath = path.join(authDir, 'server-info.json');
  fs.writeFileSync(serverInfoPath, JSON.stringify({
    link: hassInstance.link,
    configDir: (hassInstance as any).configDir,
  }));
  console.log('[GlobalSetup] Server URL:', hassInstance.link);
  console.log('[GlobalSetup] Server info saved to:', serverInfoPath);

  // Store the instance reference globally for cleanup
  (global as any).__hassInstance = hassInstance;
  (global as any).__serverInfoPath = serverInfoPath;

  console.log('[GlobalSetup] Ephemeral HA server started successfully!');

  // Wait for entities to fully register
  console.log('[GlobalSetup] Waiting for binary_sensor entities to register...');
  await new Promise(resolve => setTimeout(resolve, 5000));
  console.log('[GlobalSetup] Entities registration wait complete');
}

export default globalSetup;
