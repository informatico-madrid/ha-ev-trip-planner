/**
 * Global teardown for Playwright E2E tests.
 * Cleans up state files and performs final cleanup after all tests complete.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Cleanup state files created during test execution.
 */
function cleanupStateFiles() {
  const stateFiles = ["server-info.json"];

  for (const file of stateFiles) {
    const filePath = path.join(__dirname, file);
    if (fs.existsSync(filePath)) {
      try {
        fs.unlinkSync(filePath);
        console.log(`[globalTeardown] Removed state file: ${file}`);
      } catch (error) {
        console.error(`[globalTeardown] Failed to remove ${file}:`, error);
      }
    }
  }
}

/**
 * Main global teardown function.
 * Called after all Playwright tests have completed.
 */
async function globalTeardown() {
  console.log("[globalTeardown] Starting global teardown...");

  cleanupStateFiles();

  console.log("[globalTeardown] Global teardown complete.");
}

export default globalTeardown;