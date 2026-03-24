/**
 * Home Assistant Login Page Object
 * 
 * Provides methods to interact with the HA login page.
 * Used for authentication testing in E2E tests.
 */

import { Page, Locator } from '@playwright/test';

export class HALoginPage {
  readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly errorMessage: Locator;
  readonly rememberMeCheckbox: Locator;

  constructor(page: Page) {
    this.page = page;

    // Use reliable selectors for HA login page
    // HA uses inputs with type="text" and type="password" in the form
    this.usernameInput = page.locator('input[type="text"]');
    this.passwordInput = page.locator('input[type="password"]');
    this.loginButton = page.locator('paper-button:not([disabled])');
    this.errorMessage = page.locator('ha-alert');
    this.rememberMeCheckbox = page.locator('paper-checkbox');
  }

  /**
   * Navigate to the login page
   * @param baseUrl - Optional base URL to use for navigation
   */
  async goto(baseUrl?: string) {
    const url = baseUrl || this.page.url().substring(0, this.page.url().lastIndexOf('/'));
    await this.page.goto(`${url}/auth/login`);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Perform login with username and password
   */
  async login(username: string, password: string, rememberMe: boolean = false) {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    
    if (rememberMe) {
      await this.rememberMeCheckbox.check();
    }
    
    await this.loginButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get error message if login fails
   */
  async getErrorMessage(): Promise<string> {
    const error = this.errorMessage;
    if (await error.isVisible()) {
      return await error.textContent() || '';
    }
    return '';
  }

  /**
   * Check if login was successful (redirected away from login page)
   */
  async isLoggedIn(): Promise<boolean> {
    const currentUrl = this.page.url();
    return !currentUrl.includes('/auth/login');
  }
}
