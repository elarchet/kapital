import { test, expect } from '@playwright/test';

test('has title and displays login heading', async ({ page }) => {
  await page.goto('/');

  // Expect a title "frontend" or similar, or redirect to login.
  // The login page has a heading "Welcome to Kapital"
  await expect(page.locator('h2')).toContainText('Welcome to Kapital');
});
