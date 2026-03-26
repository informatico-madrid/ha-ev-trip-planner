/**
 * Debug script to inspect HA integrations page DOM structure
 */
import { test, expect } from '@playwright/test';

test.describe('Debug HA Integrations DOM', () => {
  test('login first', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30000 });

    // Fill login form (hass-test-framework auto-logs in)
    // Hass-test-framework handles the login automatically

    // Wait for navigation to home
    await page.waitForURL('/home/**', { waitUntil: 'domcontentloaded', timeout: 30000 });
    console.log('Logged in successfully');
  });

  test('inspect integrations page structure', async ({ page }) => {
    // Navigate directly to integrations (relative URL)
    await page.goto('/config/integrations', { waitUntil: 'domcontentloaded', timeout: 30000 });

    // Wait for page to stabilize
    await page.waitForTimeout(1000);

    // Check if we're on auth page
    const isAuthPage = await page.$('ha-auth-flow');
    console.log('Is auth page:', isAuthPage !== null);

    if (isAuthPage) {
      // Get all elements to understand the auth flow
      const authInfo = await page.evaluate(() => {
        const authFlow = document.querySelector('ha-auth-flow');
        if (authFlow) {
          const shadow = authFlow.shadowRoot;
          if (shadow) {
            return {
              hasShadow: true,
              innerHTML: shadow.innerHTML.substring(0, 10000),
              children: Array.from(shadow.querySelectorAll('*')).map(el => el.tagName)
            };
          }
        }
        return { hasShadow: false };
      });

      console.log('Auth flow info:', JSON.stringify(authInfo, null, 2));

      // The auth page might need to be bypassed - try to click the authorize button
      const authorizeButton = await page.$('ha-button');
      if (authorizeButton) {
        await page.click('ha-button');
        await page.waitForTimeout(2000);
      }
    }

    // Now click add integration button - try different selectors
    console.log('Looking for add integration button...');

    // Take screenshot of the page to see what we have
    await page.screenshot({ path: 'test-results/integrations-before-add.png' });

    // Get all buttons and their attributes
    const buttonInfo = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button, ha-icon-button, ha-button'));
      return buttons.map(btn => ({
        tagName: btn.tagName,
        ariaLabel: btn.getAttribute('aria-label'),
        innerText: btn.innerText?.substring(0, 50),
        className: btn.className
      }));
    });

    console.log('Button info:', JSON.stringify(buttonInfo, null, 2));

    // Click the first ha-icon-button which should be the add button
    await page.locator('ha-icon-button').first().click();
    console.log('Clicked add integration');

    // Wait for dialog to appear
    await page.waitForTimeout(2000);

    // Get all elements after clicking
    const allElements = await page.evaluate(() => {
      const allTags = Array.from(document.querySelectorAll('*')).map(el => el.tagName);
      const inputs = Array.from(document.querySelectorAll('input')).map((input, i) => ({
        index: i,
        type: input.type,
        placeholder: input.placeholder,
        id: input.id,
        className: input.className
      }));

      const dialogs = Array.from(document.querySelectorAll('dialog, dialog-add-integration, ha-dialog')).map(el => ({
        tagName: el.tagName,
        hasShadow: el.shadowRoot !== null
      }));

      return {
        allTags,
        inputs,
        dialogs
      };
    });

    console.log('All element tags:', allElements.allTags.slice(0, 100).join(', '));
    console.log('Inputs found:', JSON.stringify(allElements.inputs, null, 2));
    console.log('Dialogs found:', JSON.stringify(allElements.dialogs, null, 2));

    // Fill search input
    if (allElements.inputs.length > 0) {
      const firstInput = allElements.inputs[0];
      console.log('Filling first input:', firstInput);

      // Try to fill the input
      await page.fill('input[type="text"]', 'EV Trip Planner');
      console.log('Filled search');
    }

    // Take screenshot
    await page.screenshot({ path: 'test-results/integrations-search.png', fullPage: true });
  });
});
