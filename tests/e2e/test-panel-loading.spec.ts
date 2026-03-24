/**
 * E2E Test: Panel Loading
 *
 * Usage:
 *   npx playwright test test-panel-loading.spec.ts
 */

import { test, expect } from './test-base.spec';

test.describe('EV Trip Planner Panel Loading', () => {
  test('should load panel at correct URL', async ({ tripPanel }) => {
    await tripPanel.login('tests', 'tests');
    await tripPanel.navigateToPanel();
    await tripPanel.verifyPanelHeader('Coche2');
  });

  test('should display vehicle name in panel header', async ({ tripPanel }) => {
    await tripPanel.login('tests', 'tests');
    await tripPanel.navigateToPanel();
    await tripPanel.verifyPanelHeader('Coche2');
  });

  test('should show sensors section after panel loads', async ({ tripPanel }) => {
    await tripPanel.login('tests', 'tests');
    await tripPanel.navigateToPanel();
    await tripPanel.verifySensorsSectionVisible();
  });

  test('should show trips section after panel loads', async ({ tripPanel }) => {
    await tripPanel.login('tests', 'tests');
    await tripPanel.navigateToPanel();
    await tripPanel.verifyTripsSectionVisible();
  });
});
