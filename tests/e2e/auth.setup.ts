/**
 * E2E Auth Setup - Login and Config Flow for EV Trip Planner
 *
 * Este archivo se ejecuta como setup de Playwright para:
 * 1. Iniciar el servidor ephemeral de Home Assistant
 * 2. Login automático con credenciales dev/dev
 * 3. Configurar EV Trip Planner con todos los pasos del Config Flow
 * 4. Guardar el estado de autenticación para reutilizar en tests
 *
 * Patrón de desarrollo:
 * - Selectores del test-config-flow.spec.ts (ya verificados como funcionales)
 * - Logs detallados en cada paso para debugging
 * - Mejores prácticas de Playwright (auto-waiting, web-first locators cuando sea posible)
 *
 * Uso:
 *   npx playwright test auth.setup.ts
 */

import { test as setup, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath, URL } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const AUTH_DIR = path.join(__dirname, '..', '..', 'playwright', '.auth');
const SERVER_INFO_PATH = path.join(AUTH_DIR, 'server-info.json');

setup.describe('Authentication Setup', () => {
  setup('authenticate and complete EV Trip Planner config flow', async ({ page }) => {
    console.log('='.repeat(60));
    console.log('[AuthSetup] Starting authentication and config flow...');
    console.log('='.repeat(60));

    // 1. Cargar información del servidor
    const serverInfo = JSON.parse(fs.readFileSync(SERVER_INFO_PATH, 'utf-8'));
    const hassUrl = serverInfo.link;
    const baseUrl = new URL(hassUrl).origin;

    console.log(`[AuthSetup] Server URL: ${hassUrl}`);
    console.log(`[AuthSetup] Base URL (origin only): ${baseUrl}`);

    // 2. Navegar al dashboard de integraciones
    console.log('\n[Step 1/10] Navigating to integrations dashboard...');
    await page.goto(`${baseUrl}/config/integrations/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    // 3. Verificar si estamos en la página de login o si ya estamos autenticados
    console.log('[Step 2/10] Checking for login form...');

    // Intentar detectar el sidebar de navegación (solo visible si estamos autenticados)
    const sidebarVisible = await page
      .locator('ha-sidebar, [role="navigation"]')
      .isVisible({ timeout: 3000 })
      .catch(() => false);

    if (!sidebarVisible) {
      // No estamos autenticados, intentar hacer login
      console.log('[Login] Sidebar not found, attempting login...');

      // Login con credenciales admin/admin1234 usando getByRole (Web-First locators)
      await page.getByRole('textbox', { name: /Username/i }).fill('dev');
      await page.getByRole('textbox', { name: /Password/i }).fill('dev');

      // Usar getByRole para el botón de login
      await page.getByRole('button', { name: /log in/i }).click();

      // Verificar que el sidebar aparece (solo visible después del login exitoso)
      await expect(page.locator('ha-sidebar, [role="navigation"]')).toBeVisible({ timeout: 10000 });
      console.log('[Login] Successfully logged in - sidebar visible');
    } else {
      console.log('[Login] Already authenticated, sidebar visible');
    }

    // 4. Navegar a Settings
    console.log('\n[Step 3/10] Clicking Settings in sidebar...');
    await page.click('text="Settings"');

    // 5. Navegar a Devices & Services
    console.log('[Step 4/10] Clicking Devices & services...');
    await page.click('text="Devices & services"');

    // 7. Hacer clic en "Add integration"
    console.log('[Step 7/10] Clicking Add integration...');
    await page.getByRole('button', { name: /Add integration/i }).click();

    // 8. Buscar EV Trip Planner en el dialog
    console.log('[Step 8/10] Searching for EV Trip Planner in brand selection...');
    await page.getByRole('textbox', { name: /Search for a brand name/i }).fill('EV Trip Planner');
    // Use .first() because 'EV Trip Planner' matches both the heading AND the list item
    await expect(page.getByText('EV Trip Planner').first()).toBeVisible({ timeout: 5000 });

    // 9. Seleccionar EV Trip Planner
    console.log('[Step 9/10] Clicking EV Trip Planner...');
    // Use .first() to avoid strict mode violation when integration is already configured
    await page.locator('text="EV Trip Planner"').first().click();

    // 10. Esperar el dialog de configuración
    console.log('[Step 10/10] Waiting for EV Trip Planner dialog...');
    // The heading in HA 2026.3.4 is a generic element, not a heading role
    // Use getByText to match the dialog title
    const dialogHeading = page.getByText('EV Trip Planner');
    await dialogHeading.waitFor({ state: 'visible', timeout: 15000 });
    console.log('[Config] Dialog visible, proceeding with configuration...');

    // CI may have slower rendering - wait additional time for Shadow DOM form to render
    console.log('[Config] Waiting for form to fully render (CI workaround)...');
    await page.waitForTimeout(3000);

    // 11. Completar el Config Flow
    console.log('\n[Config Flow] Filling Config Flow...');

    // Debug: Check if form fields are present
    const formFields = await page.locator('input').count();
    console.log('  [Config] Form input fields found:', formFields);

    // Debug: Log ALL input field names to help debug CI issues
    const allInputs = await page.locator('input').all();
    const inputInfo = await Promise.all(allInputs.map(async (input) => {
      const name = await input.getAttribute('name');
      const type = await input.getAttribute('type');
      const placeholder = await input.getAttribute('placeholder');
      return { name, type, placeholder };
    }));
    console.log('  [Config] Input details:', JSON.stringify(inputInfo));

    // CRITICAL FIX: Use locator with input[name] selector instead of getByRole('textbox')
    // getByRole('textbox') may not recognize the element in CI due to Shadow DOM rendering
    // Use click first to focus, then type() which is more reliable for Shadow DOM inputs
    console.log('  [Config] Waiting for vehicle_name input to be ready...');
    const vehicleNameField = page.locator('input[name="vehicle_name"]');
    await vehicleNameField.waitFor({ state: 'visible', timeout: 30000 });
    console.log('  [Config] vehicle_name field is ready, focusing and typing...');

    // Click to focus first, then type character by character
    await vehicleNameField.click();
    const vehicleName = 'Coche2';
    await vehicleNameField.type(vehicleName, { delay: 50 });
    console.log('  [Config] vehicle_name value typed, proceeding...');

    // Step 1: Vehicle name submitted
    console.log('  [Config Step 1/4] Submitting vehicle_name...');
    await page.getByRole('button', { name: 'Submit' }).click();

    // Wait for step 2 form to render
    console.log('  [Config] Waiting for Step 2 form to render...');
    await page.waitForTimeout(2000);

    // Step 2: Sensors
    // Inputs in step 2 have type="numeric" - use nth() to get specific fields
    console.log('  [Config Step 2/4] Filling sensors...');

    // Debug: Log all inputs to see their types
    const allStep2Inputs = await page.locator('input').all();
    const step2Info = await Promise.all(allStep2Inputs.map(async (input) => {
      const type = await input.getAttribute('type');
      const labelledby = await input.getAttribute('aria-labelledby');
      return { type, labelledby };
    }));
    console.log('  [Config Step 2] All inputs:', JSON.stringify(step2Info));

    // Find numeric inputs - use type="number" not type="numeric"
    const numericInputs = page.locator('input[type="number"]');
    const count = await numericInputs.count();
    console.log('  [Config Step 2] Found', count, 'numeric inputs');

    // Fill the 4 numeric fields: battery_capacity, charging_power, consumption, safety_margin
    if (count >= 4) {
      await numericInputs.nth(0).click();
      await numericInputs.nth(0).type('75.0', { delay: 30 });
      await numericInputs.nth(1).click();
      await numericInputs.nth(1).type('11.0', { delay: 30 });
      await numericInputs.nth(2).click();
      await numericInputs.nth(2).type('0.17', { delay: 30 });
      await numericInputs.nth(3).click();
      await numericInputs.nth(3).type('15', { delay: 30 });
    }

    await page.getByRole('button', { name: 'Submit' }).click();

    // Step 3: EMHASS (optional)
    console.log('  [Config Step 3/4] Submitting EMHASS (optional)...');
    await page.getByRole('button', { name: 'Submit' }).click();

    // Step 4: Presence sensors - wait for presence form to render
    console.log('  [Config Step 4/4] Selecting presence sensors...');

    // Wait for presence form to be visible (it shows after async_step_presence is called)
    console.log('  [Config] Waiting for presence form to render...');
    await page.waitForTimeout(2000);

    // Check if there's a validation error BEFORE trying to submit
    // (this error would appear if form was pre-filled and invalid)
    const validationError = page.locator('text="Not all required fields are filled in"');
    const hasValidationError = await validationError
      .isVisible({ timeout: 2000 })
      .catch(() => false);

    if (hasValidationError) {
      console.log('  [Config] Validation error detected before presence submit, clicking Submit...');
      await page.getByRole('button', { name: /Submit|Next/i }).click();
    }

    // Presence sensors - backend will auto-select if none selected
    // Skip UI selection since dropdown may not populate in CI
    console.log('  [Config] Presence step - backend will auto-select entities...');

    // Submit presence step - wait for the button to be enabled and click it
    console.log('  [Config] Submitting presence step...');
    const presenceSubmitButton = page.getByRole('button', { name: /Submit|Next/i });
    await presenceSubmitButton.waitFor({ state: 'visible', timeout: 10000 });
    await presenceSubmitButton.click();

    // The presence form might need to be submitted twice due to JavaScript errors in HA's dialog
    // Wait a moment and check if the form redisplayed (user_input=None case)
    await page.waitForTimeout(1000);
    const presenceFormRedisplayed = await page.getByRole('button', { name: /Submit|Next/i }).isVisible().catch(() => false);
    if (presenceFormRedisplayed) {
      console.log('  [Config] Presence form redisplayed - submitting again...');
      await page.getByRole('button', { name: /Submit|Next/i }).click();
      await page.waitForTimeout(1000);
    }

    // Wait for notifications form to appear (step 5)
    console.log('  [Config] Waiting for notifications form to appear...');
    await page.waitForTimeout(2000);

    // The notifications form might also need to be submitted twice due to JavaScript errors
    const notificationsSubmitButton = page.getByRole('button', { name: /Submit|Next/i });
    const notificationsFormVisible = await notificationsSubmitButton.isVisible({ timeout: 5000 }).catch(() => false);
    if (notificationsFormVisible) {
      console.log('  [Config] Submitting notifications form...');
      await notificationsSubmitButton.click();
      await page.waitForTimeout(1000);

      // Check if form redisplayed (user_input=None case for notifications)
      const notificationsFormRedisplayed = await page.getByRole('button', { name: /Submit|Next/i }).isVisible().catch(() => false);
      if (notificationsFormRedisplayed) {
        console.log('  [Config] Notifications form redisplayed - submitting again...');
        await page.getByRole('button', { name: /Submit|Next/i }).click();
        await page.waitForTimeout(1000);
      }
    }

    // 11. Esperar mensaje de éxito o verificar integración
    console.log('\n[Step 10/10] Waiting for success message or checking integrations...');

    // Esperar que la página de integraciones se actualice después del Config Flow
    await expect(page.getByRole('button', { name: /Add integration/i })).toBeVisible({ timeout: 10000 });

    // Verificar si el dialog de configuración sigue abierto
    const dialogStillOpen = await page.getByRole('heading', { name: /EV Trip Planner/i }).isVisible().catch(() => false);
    if (dialogStillOpen) {
      console.log('[Config] Dialog still open, taking screenshot for debugging...');
      // Tomar screenshot del dialog
      await page.screenshot({ path: '/tmp/config-flow-dialog.png' });
      console.log('[Config] Dialog screenshot saved to /tmp/config-flow-dialog.png');
      // Buscar errores específicos EN EL DIALOG usando getByRole para dialog
      const dialogBox = page.getByRole('dialog', { name: /EV Trip Planner/i });
      const dialogError = await dialogBox.locator('text=/error|failed|invalid|required/i').allTextContents().catch(() => []);
      if (dialogError.length > 0) {
        console.log('[Config] ERROR in dialog:', dialogError);
        throw new Error(`Config Flow dialog error: ${dialogError.join(', ')}`);
      } else {
        console.log('[Config] Dialog still open but no errors found - checking form state...');
        // Si el dialog sigue abierto, intentar hacer submit nuevamente
        const submitButton = await page.getByRole('button', { name: /Submit|Next/i }).first().isVisible().catch(() => false);
        if (submitButton) {
          console.log('[Config] Submit button still visible, clicking again...');
          await page.getByRole('button', { name: /Submit|Next/i }).first().click();
          await expect(page.getByRole('button', { name: /Add integration/i })).toBeVisible({ timeout: 5000 });
        }
      }
    } else {
      console.log('[Config] Dialog closed, checking for success...');
    }

    // Navegar a la página de integraciones para verificar el estado
    console.log('[Config] Navigating to integrations page to verify...');
    await page.goto(`${baseUrl}/config/integrations`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    // Esperar a que el diálogo se cierre y la página de integraciones cargue completamente
    // El diálogo puede tardar en cerrarse después de _async_create_entry
    console.log('[Config] Waiting for dialog to close...');
    await page.waitForTimeout(2000);

    // Verificar si "EV Trip Planner" aparece en la lista de integraciones configuradas
    // El título de la integración en la lista es "EV Trip Planner", no el nombre del vehículo
    const integrationName = 'EV Trip Planner';
    const vehicleIntegrationLink = page.locator(`text="${integrationName}"`).first();
    const vehicleIntegrationVisible = await vehicleIntegrationLink.waitFor({ state: 'visible', timeout: 10000 }).then(() => true).catch(() => false);

    if (vehicleIntegrationVisible) {
      console.log(`[Config] ✓ Integration "${integrationName}" found in configured list!`);
    } else {
      console.log(`[Config] ✗ Integration "${integrationName}" NOT found in configured list!`);
      throw new Error(`Config Flow failed: Integration "${integrationName}" was not created`);
    }

    // 12. Navegar al dashboard para establecer sesión
    console.log('\n[Navigating] Establishing session at dashboard...');
    await page.goto(`${baseUrl}/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    // 13. Guardar estado de autenticación
    console.log('[AuthSetup] Saving authentication state...');
    const storageStatePath = path.join(AUTH_DIR, 'user.json');
    await page.context().storageState({ path: storageStatePath });
    console.log(`[AuthSetup] Storage state saved to: ${storageStatePath}`);

    // 14. Verificar que la integración se configuró correctamente
    // Nota: El panel webcomponent puede no renderizarse inmediatamente en entornos ephemeral
    // pero la integración debe aparecer en la lista de configuradas
    const vehicleId = 'coche2';
    const panelUrl = `${baseUrl}/ev-trip-planner-${vehicleId}`;

    console.log(`[Config] Integration configured successfully for ${vehicleName}`);
    console.log(`[Config] Panel URL would be: ${panelUrl}`);

    // Guardar URL del panel para tests
    const panelUrlPath = path.join(AUTH_DIR, 'panel-url.txt');
    fs.writeFileSync(panelUrlPath, panelUrl);
    console.log(`[AuthSetup] Panel URL saved to: ${panelUrlPath}`);
    console.log(`[AuthSetup] Panel URL: ${panelUrl}`);

    console.log('\n' + '='.repeat(60));
    console.log('[AuthSetup] Authentication and config flow complete!');
    console.log('='.repeat(60));
  });
});
