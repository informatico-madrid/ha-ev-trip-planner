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
    
    // Use data-testid or reliable selectors for HA
    this.usernameInput = page.getByLabel(/username|user|email/i);
    this.passwordInput = page.getByLabel(/password/i);
    this.loginButton = page.getByRole('button', { name: /login|sign in|entrar/i });
    this.errorMessage = page.getByRole('alert');
    this.rememberMeCheckbox = page.getByLabel(/remember me|recordar/i);
  }

  /**
   * Navigate to the login page
   */
  async goto() {
    await this.page.goto('/auth/login');
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
