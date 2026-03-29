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

  // Create vehicle config entry using HA's internal API
  // This triggers async_setup_entry automatically - the CORRECT way
  console.log('[GlobalSetup] Creating vehicle config entry via HA internal API...');

  // Use hassInstance.hass.config_entries.async_create_entry
  // This is the proper HA API that triggers async_setup_entry
  const hassInternal = (hassInstance as any).hass || (hassInstance as any)._hass;

  if (hassInternal && hassInternal.config_entries) {
    // Create the config entry using HA's proper API
    // This will automatically trigger async_setup_entry() for the ev_trip_planner integration
    console.log('[GlobalSetup] Creating config entry for ev_trip_planner...');
    const result = await hassInternal.config_entries.async_create_entry(
      'ev_trip_planner',
      {
        vehicle_id: 'coche2',
        vehicle_name: 'Coche2',
        model: 'Model S',
        make: 'Tesla',
      }
    );
    console.log('[GlobalSetup] Config entry created, entry_id:', result.entry_id);
  } else {
    console.warn('[GlobalSetup] WARNING: Could not access HA config_entries API');
    console.warn('[GlobalSetup] Falling back to direct storage write (NOT RECOMMENDED)');

    // Fallback: direct storage write (this doesn't trigger async_setup_entry)
    const storagePath = path.join(wwwDir, '.storage', 'core.config_entries');
    fs.mkdirSync(path.dirname(storagePath), { recursive: true });

    let configEntries = [];
    if (fs.existsSync(storagePath)) {
      const existing = JSON.parse(fs.readFileSync(storagePath, 'utf-8'));
      configEntries = existing.entries || [];
    }

    const vehicleData = {
      version: 1,
      minor_version: 1,
      domain: "ev_trip_planner",
      title: "Coche2",
      data: {
        vehicle_id: "coche2",
        vehicle_name: "Coche2",
        model: "Model S",
        make: "Tesla",
      },
      options: {},
      entry_id: "coche2_entry",
    };

    configEntries.push(vehicleData);
    fs.writeFileSync(storagePath, JSON.stringify({ entries: configEntries }, null, 2));
    console.log('[GlobalSetup] Vehicle config entry written to storage (fallback)');
  }

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
