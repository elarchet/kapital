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

  // 2. Create Portfolio Strategy Folder via Sidebar (directly creates and sets in rename mode)
  const addPortfolioBtn = page.locator('button[title="Create Portfolio"]').first();
  await expect(addPortfolioBtn).toBeVisible();
  await addPortfolioBtn.click();

  // Wait for the inline renaming input to appear in the sidebar
  const renameInput = page.locator('.sidebar-nav input');
  await expect(renameInput).toBeVisible();

  // Rename the portfolio inline
  const portfolioName = `QA E2E Strategy ${Date.now()}`;
  await renameInput.fill(portfolioName);
  await renameInput.press('Enter');

  // Verify rename input is gone and the sidebar link is updated
  await expect(renameInput).not.toBeVisible();
  const portfolioLink = page.locator('.sidebar-nav a', { hasText: portfolioName });
  await expect(portfolioLink).toBeVisible();

  // Verify portfolio page loaded and has the new name
  await expect(page.locator('.page-header h1')).toContainText(portfolioName);

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

  // 4b. Valuation widgets render: KPI pill, value-over-time chart, donut
  await expect(page.locator('[data-testid="kpi-market-value"]')).toBeVisible();
  const chartCard = page.locator('section', { hasText: 'Portfolio value' }).first();
  await expect(chartCard).toBeVisible();
  for (const label of ['1M', '3M', '6M', '1Y', 'YTD', 'ALL']) {
    await expect(chartCard.locator('button', { hasText: label }).first()).toBeVisible();
  }
  await expect(page.locator('section', { hasText: 'Allocation by Asset Type' }).first()).toBeVisible();

  // 4c. Row click opens the transactions drawer (manual position: empty state)
  await nvdaRow.click();
  const drawer = page.locator('.z-\\[100\\]');
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText('NVIDIA Corporation');
  await expect(drawer).toContainText('No transactions');
  // Close via backdrop click (left of the right-aligned panel)
  await drawer.click({ position: { x: 8, y: 8 } });
  await expect(drawer).not.toBeVisible();

  // 5. Delete Asset (Verifying our new base-confirm-modal)
  const deleteBtn = nvdaRow.locator('button[title="Remove Asset"]');
  await expect(deleteBtn).toBeVisible();
  await deleteBtn.click();

  // Confirm delete modal is visible and verify details
  const confirmModal = page.locator('.fixed.inset-0', { hasText: 'Delete Asset?' });
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

  // 6. Delete Portfolio Strategy (Clean up)
  const deletePortfolioBtn = page.locator('button[title="Delete Portfolio"]');
  await expect(deletePortfolioBtn).toBeVisible();
  await deletePortfolioBtn.click();

  const deletePortfolioModal = page.locator('.fixed.inset-0', { hasText: 'Delete Strategy?' });
  await expect(deletePortfolioModal).toBeVisible();
  await deletePortfolioModal.locator('button:has-text("Delete Strategy")').click();

  await expect(deletePortfolioModal).not.toBeVisible();
  await expect(page.locator('h1')).toHaveText('Global Dashboard');
});
