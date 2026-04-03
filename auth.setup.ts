import { FullConfig } from "@playwright/test";

const HA_URL = "http://localhost:8123";
const HA_STARTUP_TIMEOUT_MS = 120_000;

async function waitForHA(): Promise<void> {
  const start = Date.now();

  while (Date.now() - start < HA_STARTUP_TIMEOUT_MS) {
    try {
      const response = await fetch(HA_URL);
      if (response.ok) {
        console.log(`Home Assistant is ready at ${HA_URL}`);
        return;
      }
    } catch (error) {
      console.error(`[auth.setup] HA connection failed: ${error instanceof Error ? error.message : String(error)}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }

  throw new Error(`Home Assistant did not start within ${HA_STARTUP_TIMEOUT_MS}ms`);
}

async function globalSetup(config: FullConfig): Promise<void> {
  console.log("[auth.setup] Waiting for Home Assistant to be ready...");
  await waitForHA();
  console.log("[auth.setup] Global setup complete");
}

export default globalSetup;
