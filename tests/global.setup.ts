/**
 * Global Setup - Server Lifecycle + Auth
 *
 * This file is executed once before all tests.
 * 1. Starts the ephemeral HA server
 * 2. Runs Config Flow UI to authenticate (via auth.setup.ts)
 * 3. Saves storageState for test projects
 */

import { FullConfig } from '@playwright/test';
import { HomeAssistant, PlaywrightBrowser } from 'hass-taste-test';
import * as fs from 'fs';
import * as path from 'path';
import { runAuthSetup } from './e2e/auth.setup';

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

  // Wait for HA to be fully ready
  console.log('[GlobalSetup] Waiting for HA to be ready...');
  await new Promise(resolve => setTimeout(resolve, 10000));

  // Save server info to a file for auth.setup.ts
  const authDir = path.join(rootDir, 'playwright', '.auth');
  fs.mkdirSync(authDir, { recursive: true });
  const serverInfoPath = path.join(authDir, 'server-info.json');
  fs.writeFileSync(serverInfoPath, JSON.stringify({
    link: hassInstance.link,
    configDir: (hassInstance as any).configDir,
  }));
  console.log('[GlobalSetup] Server URL:', hassInstance.link);
  console.log('[GlobalSetup] Server info saved to:', serverInfoPath);

  // Run Config Flow UI authentication
  // This creates the storageState used by test projects
  console.log('[GlobalSetup] Running Config Flow authentication...');
  await runAuthSetup();

  // Store the instance reference globally for cleanup
  (global as any).__hassInstance = hassInstance;
  (global as any).__serverInfoPath = serverInfoPath;

  console.log('[GlobalSetup] All setup complete!');
}

export default globalSetup;