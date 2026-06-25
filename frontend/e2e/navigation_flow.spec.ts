import { test, expect } from '@playwright/test';

test('verify sidebar layout, settings navigation, global view return, and logout flow', async ({ page }) => {
  // 1. Login via the root URL
  await page.goto('/');
  await expect(page).toHaveURL(/.*\/login/);

  await page.fill('#email', 'test@example.com');
  await page.fill('#password', 'password123');
  await page.click('button:has-text("Access Platform")');

  // 2. Verify navigation to the Global Dashboard
  await expect(page).toHaveURL(/^(?!.*login).*$/);
  await expect(page.locator('h1')).toHaveText('Global Dashboard');

  // 3. Verify that collapsing the sidebar works:
  const sidebar = page.locator('aside.sidebar');
  const collapseBtn = page.locator('.btn-collapse');
  await expect(collapseBtn).toBeVisible();

  // - Click it
  await collapseBtn.click();

  // - Assert that the sidebar now has the "collapsed" class
  await expect(sidebar).toHaveClass(/collapsed/);

  // - Click it again (title is now "Expand Sidebar")
  await collapseBtn.click();

  // - Assert that the sidebar no longer has the "collapsed" class
  await expect(sidebar).not.toHaveClass(/collapsed/);

  // 4. Test profile menu settings navigation:
  // - Click the profile menu button (using the direct child button or text selector)
  const profileMenuBtn = page.locator('.sidebar-profile > button');
  await expect(profileMenuBtn).toBeVisible();
  await profileMenuBtn.click();

  // - Click the "Settings" link inside the profile menu
  const settingsLink = page.locator('.sidebar-profile a:has-text("Settings")');
  await expect(settingsLink).toBeVisible();
  await settingsLink.click();

  // - Verify that the URL changes to /settings and the page header has text "System Settings"
  await expect(page).toHaveURL(/.*\/settings/);
  await expect(page.locator('.page-header h1')).toContainText('System Settings');

  // 5. Test navigation back to dashboard:
  // - Click the "Global View" link in the sidebar
  const globalViewLink = page.locator('.sidebar-nav a:has-text("Global View")');
  await expect(globalViewLink).toBeVisible();
  await globalViewLink.click();

  // - Verify that the URL is back to / and page header is "Global Dashboard"
  await expect(page).toHaveURL(/^(?!.*(login|settings)).*$/);
  await expect(page.locator('h1')).toHaveText('Global Dashboard');

  // 6. Test Logout flow:
  // - Click the profile menu button
  await profileMenuBtn.click();

  // - Click the "Sign Out" button
  const signOutBtn = page.locator('.sidebar-profile button:has-text("Sign Out")');
  await expect(signOutBtn).toBeVisible();
  await signOutBtn.click();

  // - Verify that the URL redirects to /login and the "Welcome to Kapital" heading is visible
  await expect(page).toHaveURL(/.*\/login/);
  await expect(page.locator('h2')).toContainText('Welcome to Kapital');
});
