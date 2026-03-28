import { test, expect } from '@playwright/test';

test('verify panel loads correctly after HA restart', async ({ page }) => {
  console.log('=== Starting panel verification ===');

  // Navigate to the panel
  const haUrl = 'http://192.168.1.201:8124/ev-trip-planner-chispitas';
  console.log(`Navigating to: ${haUrl}`);

  await page.goto(haUrl, { waitUntil: 'networkidle', timeout: 30000 });

  console.log('Page loaded, checking state...');

  // Check for console messages
  const consoleMessages: string[] = [];
  page.on('console', msg => {
    const text = msg.text();
    consoleMessages.push(text);
    if (text.includes('EV Trip Planner Panel') || text.includes('console.log')) {
      console.log(`Console: ${text}`);
    }
  });

  // Take initial snapshot
  console.log('Taking initial snapshot...');
  const snapshot1 = await page.content();
  console.log(`Initial HTML size: ${snapshot1.length} bytes`);

  // Wait for JS to execute and check for errors
  console.log('Waiting for JS execution...');
  await page.waitForTimeout(3000);

  const snapshot2 = await page.content();
  console.log(`HTML after wait: ${snapshot2.length} bytes`);

  // Check for error patterns
  const hasError = snapshot2.includes('error') || snapshot2.includes('Error') || snapshot2.includes('extra keys');
  console.log(`Has error pattern: ${hasError}`);

  // Check for success patterns
  const hasSuccess = snapshot2.includes('EV Trip Planner') || snapshot2.includes('trips');
  console.log(`Has success pattern: ${hasSuccess}`);

  // Print console messages
  console.log('=== Console Messages ===');
  consoleMessages.forEach(msg => {
    if (msg.includes('EV Trip Planner Panel') || msg.includes('ERROR') || msg.includes('console.log')) {
      console.log(msg);
    }
  });

  // Check specific error we were looking for
  const hasReturnResponseError = snapshot2.includes("extra keys not allowed @ data['target']['return_response']");
  console.log(`Has return_response error: ${hasReturnResponseError}`);

  // Take screenshot
  await page.screenshot({ path: '/tmp/panel-screenshot.png', fullPage: true });
  console.log('Screenshot saved to /tmp/panel-screenshot.png');

  // Print final status
  console.log('=== Final Status ===');
  console.log(`Panel loaded: ${snapshot1.length > 0}`);
  console.log(`Errors found: ${hasError}`);
  console.log(`Success patterns: ${hasSuccess}`);
  console.log(`Return response error: ${hasReturnResponseError}`);
});
