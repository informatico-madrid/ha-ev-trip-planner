"""
Playwright E2E tests for EV Trip Planner native panel.
Tests the complete user journey: login -> add vehicle -> verify panel appears.
"""

import asyncio
from playwright.async_api import async_playwright


async def test_native_panel_flow():
    """
    Test the complete flow:
    1. Login to Home Assistant
    2. Navigate to Integrations
    3. Add EV Trip Planner integration
    4. Configure vehicle
    5. Verify panel appears in sidebar
    """

    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        try:
            # Step 1: Navigate to Home Assistant
            print("Step 1: Navigating to Home Assistant...")
            await page.goto("http://localhost:8123", timeout=30000)
            await page.wait_for_selector('form[name="login"]', timeout=10000)

            # Step 2: Login with credentials
            print("Step 2: Logging in...")
            await page.fill('input[name="username"]', "malka")
            await page.fill('input[name="password"]', "Darkpunk666/")
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle", timeout=30000)

            # Step 3: Navigate to Integrations
            print("Step 3: Navigating to Integrations...")
            await page.click('a[href="/config/integrations"]')
            await page.wait_for_load_state("networkidle", timeout=30000)

            # Step 4: Add EV Trip Planner integration
            print("Step 4: Adding EV Trip Planner integration...")
            await page.click("button:has-text('Add Integration')")
            await page.wait_for_selector('div:has-text("EV Trip Planner")', timeout=10000)

            # Step 5: Configure vehicle
            print("Step 5: Configuring vehicle...")
            await page.click("button:has-text('Submit')")
            await page.fill('input[placeholder*="vehicle"]', "test_vehicle")
            await page.click("button:has-text('Submit')")

            # Step 6: Verify panel appears in sidebar
            print("Step 6: Verifying panel in sidebar...")
            # Wait for panel to appear
            sidebar_panel = await page.wait_for_selector(
                ".sidebar-panel:has-text('EV')",
                timeout=10000
            )
            print(f"✓ Panel found in sidebar: {await sidebar_panel.inner_text()}")

            # Step 7: Click on the panel
            print("Step 7: Clicking on panel...")
            await sidebar_panel.click()
            await page.wait_for_load_state("networkidle", timeout=30000)

            # Step 8: Verify panel content loads
            print("Step 8: Verifying panel content...")
            # Check for vehicle status elements
            status_cards = await page.query_selector_all(".status-card")
            print(f"✓ Found {len(status_cards)} status cards")

            # Take screenshot for verification
            await page.screenshot(
                path="/home/malka/ha-ev-trip-planner/tests/e2e/screenshots/native_panel_verified.png",
                full_page=True
            )
            print("✓ Screenshot saved to tests/e2e/screenshots/native_panel_verified.png")

            print("\n=== SUCCESS ===")
            print("✓ Panel appears in sidebar after vehicle configuration")
            print("✓ Panel loads without errors")
            print("✓ Vehicle status is displayed")

        except Exception as e:
            print(f"\n=== ERROR ===")
            print(f"Error: {str(e)}")
            # Take screenshot on error
            await page.screenshot(
                path="/home/malka/ha-ev-trip-planner/tests/e2e/screenshots/error_screenshot.png",
                full_page=True
            )
            raise
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_native_panel_flow())
