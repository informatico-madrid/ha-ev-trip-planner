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
import { spawn } from 'child_process';

async function globalSetup(config: FullConfig) {
  console.log('[GlobalSetup] Starting ephemeral HA server...');

  const evTripPlannerPath = path.join(process.cwd(), 'custom_components/ev_trip_planner');
  const panelJsPath = path.join(evTripPlannerPath, 'frontend/panel.js');
  const rootDir = process.cwd();

  // FIX: josepy 1.14+ removed ComparableX509 which breaks acme (used by hass-nabucasa)
  // Monkey-patch HomeAssistant.setupVenv to downgrade josepy after homeassistant installation
  console.log('[GlobalSetup] Applying josepy compatibility fix...');

  const runCommand = (command: string, args: string[]): Promise<number> => {
    return new Promise((resolve, reject) => {
      const proc = spawn(command, args, { stdio: 'inherit' });
      proc.on('error', (err) => reject(err));
      proc.on('close', (code) => resolve(code ?? 0));
    });
  };

  const originalSetupVenv = (HomeAssistant.prototype as any).setupVenv;
  (HomeAssistant.prototype as any).setupVenv = async function() {
    // Call original setupVenv
    await originalSetupVenv.call(this);
    // After homeassistant is installed, downgrade josepy to 1.13.0 which has ComparableX509
    console.log('[GlobalSetup] Downgrading josepy to 1.13.0...');
    await runCommand(this.path_pip(), ['install', 'josepy==1.13.0']);
    console.log('[GlobalSetup] josepy downgrade complete');
  };

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

  // Wait for the integration to be loaded
  console.log('[GlobalSetup] Waiting for ev_trip_planner integration to load...');
  await new Promise(resolve => setTimeout(resolve, 10000));

  // NOTE: We intentionally do NOT create a config entry here.
  // The auth.setup.ts test will use the UI to add the integration.
  // Creating a config entry via storage write bypasses async_setup_entry
  // and can cause issues with the config flow UI.

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
