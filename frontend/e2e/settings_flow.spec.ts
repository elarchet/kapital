import { test, expect } from '@playwright/test';

test('verify settings page themes and component overrides', async ({ page }) => {
  // 1. Login
  await page.goto('/');
  await expect(page).toHaveURL(/.*\/login/);

  await page.fill('#email', 'test@example.com');
  await page.fill('#password', 'password123');
  await page.click('button:has-text("Access Platform")');

  // Verify dashboard navigation
  await expect(page).toHaveURL(/^(?!.*login).*$/);

  // 2. Navigate to Settings via Sidebar
  // 2. Navigate to Settings
  await page.goto('/settings');

  // Verify settings page loaded
  await expect(page).toHaveURL(/.*\/settings/);
  await expect(page.locator('.page-header h1')).toContainText('System Settings');

  // 3. Test Theme Change
  const slateDarkBtn = page.locator('button', { hasText: 'Slate Dark' });
  await expect(slateDarkBtn).toBeVisible();
  await slateDarkBtn.click();
  // Check that the checkmark icon appears (which has text-accent class)
  await expect(slateDarkBtn.locator('svg')).toBeVisible();

  // 4. Check UI Component Overrides Display
  const sidebarConfig = page.locator('.component-config-card', { hasText: 'Sidebar Nav' });
  await expect(sidebarConfig).toBeVisible();

  const chooseExtBtn = sidebarConfig.locator('button:has-text("Choose Extension")');
  await expect(chooseExtBtn).toBeVisible();
  await chooseExtBtn.click();

  // 5. Verify the Modal opens
  const modalHeader = page.locator('h3', { hasText: 'Extensions for: Sidebar Nav' });
  await expect(modalHeader).toBeVisible();

  // Close modal using the x button
  const closeBtn = page.locator('.modal-header button');
  await closeBtn.click();
  await expect(modalHeader).not.toBeVisible();
});
