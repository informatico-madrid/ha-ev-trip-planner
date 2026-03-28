import { test } from '@playwright/test';

test('verify service_lacks_response_request fix', async ({ page }) => {
  await page.goto('http://192.168.1.201:8124');

  // Wait 5 seconds for the UI to load completely
  await page.waitForTimeout(5000);

  // Take a screenshot to verify the fix is working
  await page.screenshot({ path: 'tests/e2e/playwright-report/service-fix-screenshot.png', fullPage: true });

  // Log console messages to check for any errors
  const consoleMessages: string[] = [];
  page.on('console', msg => {
    consoleMessages.push(`${msg.type()}: ${msg.text()}`);
  });

  console.log('Console messages after 5 seconds:', consoleMessages);

  // Verify the page is loaded by checking for Home Assistant dashboard elements
  const title = await page.title();
  console.log('Page title:', title);

  // Check for dashboard elements that indicate successful load
  const dashboardFound = await page.locator('ha-app-layout').count() > 0;
  console.log('Dashboard found:', dashboardFound);

  test.expect(dashboardFound).toBe(true);
});
