import { test, expect } from '@playwright/test';

test('verify full portfolio and position lifecycle flow with custom modals', async ({ page }) => {
  // 1. Login
  await page.goto('/');
  await expect(page).toHaveURL(/.*\/login/);

  await page.fill('#email', 'test@example.com');
  await page.fill('#password', 'password123');
  await page.click('button:has-text("Access Platform")');

  // Verify dashboard navigation
  await expect(page).toHaveURL(/^(?!.*login).*$/);
  await expect(page.locator('h1')).toHaveText('Global Dashboard');

  // 2. Create Portfolio Strategy Folder via Sidebar
  const addPortfolioBtn = page.locator('button[title="Create Portfolio"]');
  await expect(addPortfolioBtn).toBeVisible();
  await addPortfolioBtn.click();

  // Modal forms
  const nameInput = page.locator('#portfolioName');
  const descInput = page.locator('#portfolioDesc');
  const submitBtn = page.locator('button:has-text("Create Portfolio")');

  await nameInput.fill('QA E2E Strategy');
  await descInput.fill('Formulated via Playwright E2E runner.');
  await submitBtn.click();

  // 3. Navigate to the new Portfolio
  const portfolioLink = page.locator('.sidebar-nav a', { hasText: 'QA E2E Strategy' });
  await expect(portfolioLink).toBeVisible();
  await portfolioLink.click();

  // Verify portfolio page loaded
  await expect(page.locator('.page-header h1')).toContainText('QA E2E Strategy');

  // 4. Open Add Position dropdown
  const addPositionBtn = page.locator('#btn-add-position-component');
  await expect(addPositionBtn).toBeVisible();
  await addPositionBtn.click();

  // Click Manual Entry
  const manualEntryBtn = page.locator('button:has-text("Manual Entry")');
  await expect(manualEntryBtn).toBeVisible();
  await manualEntryBtn.click();

  // Fill in holding details
  await page.selectOption('#posAsset', 'stock');
  await page.selectOption('#posCurrency', 'USD');
  await page.fill('#posName', 'NVIDIA Corporation');
  await page.fill('#posTicker', 'NVDA');
  await page.fill('#posIsin', 'US67066G1040');
  await page.fill('#posQuantity', '10');

  // Submit holding
  await page.click('button:has-text("Record Holding")');

  // Verify NVDA position appears in the holdings list
  const nvdaRow = page.locator('.premium-table tbody tr', { hasText: 'NVIDIA Corporation' });
  await expect(nvdaRow).toBeVisible();
  await expect(nvdaRow).toContainText('NVDA');

  // 5. Delete Position (Verifying our new base-confirm-modal)
  const deleteBtn = nvdaRow.locator('button[title="Remove Position"]');
  await expect(deleteBtn).toBeVisible();
  await deleteBtn.click();

  // Confirm delete modal is visible and verify details
  const confirmModal = page.locator('.fixed.inset-0', { hasText: 'Delete Position?' });
  await expect(confirmModal).toBeVisible();
  await expect(confirmModal).toContainText('Are you sure you want to permanently delete this asset position');

  // Click cancel first to verify it doesn't delete
  await confirmModal.locator('button:has-text("Cancel")').click();
  await expect(confirmModal).not.toBeVisible();
  await expect(nvdaRow).toBeVisible();

  // Trigger delete again
  await deleteBtn.click();
  await expect(confirmModal).toBeVisible();

  // Click confirm to delete
  await confirmModal.locator('button:has-text("Delete Position")').click();
  await expect(confirmModal).not.toBeVisible();
  await expect(nvdaRow).not.toBeVisible();
});
