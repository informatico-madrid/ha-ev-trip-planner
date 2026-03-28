import { test, expect } from '@playwright/test';

test.describe('EV Trip Planner Panel Verification', () => {
  test.use({
    storageState: undefined,
  });

  test('verify panel loads without service_lacks_response_request error', async ({ page }) => {
    console.log('Starting panel verification test...');

    // Navigate to Home Assistant
    console.log('Navigating to: http://192.168.1.201:8124');
    await page.goto('http://192.168.1.201:8124', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    await page.waitForLoadState('domcontentloaded');
    await page.waitForLoadState('networkidle');

    // Take screenshots
    await page.screenshot({
      path: 'tests/e2e/playwright-report/panel-verify-1.png',
      fullPage: true
    });
    console.log('Screenshot 1 taken');

    // Capture console messages
    const consoleMessages: string[] = [];
    page.on('console', msg => {
      const msgText = `${msg.type()}: ${msg.text()}`;
      consoleMessages.push(msgText);
      if (msg.type() === 'error') {
        console.error(`[ERROR] ${msg.text()}`);
      } else if (msg.text().includes('EV Trip Planner') || msg.text().includes('ev_trip_planner')) {
        console.log(`[HA LOG] ${msg.text()}`);
      }
    });

    console.log('\n=== Console Messages ===');
    consoleMessages.forEach((msg, i) => console.log(`[${i}] ${msg}`));
    console.log('=== End Console Messages ===\n');

    const title = await page.title();
    console.log(`Page title: ${title}`);

    await page.screenshot({
      path: 'tests/e2e/playwright-report/panel-verify-2.png',
      fullPage: true
    });
    console.log('Screenshot 2 taken');

    await page.screenshot({
      path: 'tests/e2e/playwright-report/panel-verify-3.png',
      fullPage: true
    });
    console.log('Screenshot 3 taken');

    await expect(page).toHaveTitle(/Home Assistant/i, { timeout: 5000 });
    console.log('✓ Page title verified');

    const hasError = consoleMessages.some(msg =>
      msg.toLowerCase().includes('service_lacks_response_request')
    );

    if (hasError) {
      console.log('\n⚠️  WARNING: service_lacks_response_request error detected!');
    } else {
      console.log('\n✓ No service_lacks_response_request error found');
    }

    console.log('\n=== SUMMARY ===');
    console.log(`URL: http://192.168.1.201:8124`);
    console.log(`Title: ${title}`);
    console.log(`Console messages: ${consoleMessages.length}`);
    console.log(`Errors found: ${hasError ? 'YES' : 'NO'}`);
    console.log('=== END SUMMARY ===');
  });
});
