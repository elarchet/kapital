import { test, expect } from '@playwright/test';

test('verify UI Component overrides interface', async ({ page }) => {
  // 1. Navigate to `/` (which redirects to `/login`).
  await page.goto('/');

  // Verify redirection to /login
  await expect(page).toHaveURL(/.*\/login/);

  // 2. Fill in the login form with `test@example.com` and `password123` and click "Access Platform".
  await page.fill('#email', 'test@example.com');
  await page.fill('#password', 'password123');
  await page.click('button:has-text("Access Platform")');

  // Wait for login to complete and navigate to dashboard
  await expect(page).toHaveURL(/^(?!.*login).*$/);
  await expect(page.locator('h1')).toHaveText('Global Dashboard');

  // 3. Navigate to `/settings`.
  await page.goto('/settings');

  // 4. Assert that the "System Settings" title is visible.
  await expect(page.locator('h1')).toHaveText('System Settings');

  // 5. Assert that the "Granular UI Component Overrides" section is visible.
  await expect(page.locator('h2:has-text("Granular UI Component Overrides")')).toBeVisible();

  // 6. Verify that the settings page lists components like "Sidebar Nav" and shows their active state as "Default (Built-in)".
  const sidebarCard = page.locator('.component-config-card', { hasText: 'Sidebar Nav' });
  await expect(sidebarCard).toBeVisible();
  await expect(sidebarCard).toContainText('Active:');
  await expect(sidebarCard).toContainText('Default (Built-in)');
});
