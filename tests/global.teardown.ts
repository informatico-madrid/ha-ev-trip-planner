/**
 * Global Teardown - Server Lifecycle
 *
 * This file is executed once after all tests.
 * It only destroys the ephemeral HA server - NO browser interactions.
 */

import * as fs from 'fs';
import * as path from 'path';

// Cerrar el archivo de logs
const logFilePath = path.join('/tmp', 'ha-logs.txt');
if (fs.existsSync(logFilePath)) {
  console.log(`[GlobalTeardown] Logs saved to: ${logFilePath}`);
}

async function globalTeardown() {
  console.log('[GlobalTeardown] Cleaning up...');

  const rootDir = '/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner';
  const authDir = path.join(rootDir, 'playwright', '.auth');

  // Get the server info path from global
  const serverInfoPath = (global as any).__serverInfoPath;

  if (serverInfoPath && fs.existsSync(serverInfoPath)) {
    try {
      const serverInfo = JSON.parse(fs.readFileSync(serverInfoPath, 'utf-8'));
      console.log('[GlobalTeardown] Cleaning up server at:', serverInfo.link);
    } catch (e) {
      // Ignore errors reading
    }
  }

  // Only clean up server-info.json - keep user.json for debugging
  if (fs.existsSync(authDir)) {
    const files = fs.readdirSync(authDir);
    for (const file of files) {
      if (file === 'server-info.json') {
        fs.unlinkSync(path.join(authDir, file));
        console.log('[GlobalTeardown] Deleted:', file);
      }
      // Keep user.json - it's the authentication state
    }
  }

  console.log('[GlobalTeardown] Cleanup complete!');
}

export default globalTeardown;
