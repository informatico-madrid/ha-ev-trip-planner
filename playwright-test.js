const { chromium } = require('@playwright/test');

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  console.log('Navigating to Home Assistant...');
  await page.goto('http://homeassistant.local:8123');
  
  // Wait for page to load
  await page.waitForLoadState('networkidle');
  
  // Get the title
  const title = await page.title();
  console.log('Page title:', title);
  
  // Check if login form exists
  const loginForm = await page.$('form[id="login_form"]');
  if (loginForm) {
    console.log('✓ Login form found - Home Assistant login page detected!');
  } else {
    console.log('Login form not found');
  }
  
  // Get current URL
  const url = page.url();
  console.log('Current URL:', url);
  
  await browser.close();
  console.log('Done!');
}

main().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
