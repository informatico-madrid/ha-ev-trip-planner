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

  const evTripPlannerPath = '/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner';
  const panelJsPath = evTripPlannerPath + '/frontend/panel.js';
  const rootDir = '/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner';

  // Start ephemeral HA with the custom component
  const hassInstance = await HomeAssistant.create(`
binary_sensor:
  - platform: demo
    devices:
      - name: "Coche1 Cargando"
        device_class: plug
      - name: "Coche1 En Casa"
        device_class: home
      - name: "Coche1 Enchufado"
        device_class: plug

lovelace:
  mode: storage
  resources:
    - url: /local/panel.js
      type: module
`, {
    python: 'python3',
    browser: new PlaywrightBrowser('chromium'),
    customComponents: [evTripPlannerPath],
  });

  // Copy panel.js to www directory
  const wwwDir = path.join(hassInstance.configDir, 'www');
  fs.mkdirSync(wwwDir, { recursive: true });
  fs.copyFileSync(panelJsPath, path.join(wwwDir, 'panel.js'));
  console.log('[GlobalSetup] Copied panel.js to:', path.join(wwwDir, 'panel.js'));

  // Save server info to a file for other setups to use
  const authDir = path.join(rootDir, 'playwright', '.auth');
  fs.mkdirSync(authDir, { recursive: true });
  const serverInfoPath = path.join(authDir, 'server-info.json');
  fs.writeFileSync(serverInfoPath, JSON.stringify({
    link: hassInstance.link,
    configDir: hassInstance.configDir,
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
