import { test, expect } from '@playwright/test';

test('verify position creation and deletion from global dashboard flow', async ({ page }) => {
  // 1. Login via root URL
  await page.goto('/');
  await expect(page).toHaveURL(/.*\/login/);

  await page.fill('#email', 'test@example.com');
  await page.fill('#password', 'password123');
  await page.click('button:has-text("Access Platform")');

  // Verify dashboard navigation
  await expect(page).toHaveURL(/^(?!.*login).*$/);
  await expect(page.locator('h1')).toHaveText('Global Dashboard');

  // 2. Create Portfolio Strategy Folder via Sidebar to ensure we have a portfolio strategy
  const addPortfolioBtn = page.locator('button[title="Create Portfolio"]');
  await expect(addPortfolioBtn).toBeVisible();
  await addPortfolioBtn.click();

  const portfolioNameInput = page.locator('#portfolioName');
  const portfolioDescInput = page.locator('#portfolioDesc');
  const createPortfolioSubmitBtn = page.locator('button:has-text("Create Portfolio")');

  const portfolioName = `Dashboard Portfolio ${Date.now()}`;
  await portfolioNameInput.fill(portfolioName);
  await portfolioDescInput.fill('E2E Strategy created from Dashboard Flow.');
  await createPortfolioSubmitBtn.click();

  // Navigate explicitly back to "/" (Global Dashboard) to make sure we are there
  await page.goto('/');
  await expect(page.locator('h1')).toHaveText('Global Dashboard');

  // 3. Click "Add Asset Position" on the dashboard header
  const addAssetPositionBtn = page.locator('button:has-text("Add Asset Position")');
  await expect(addAssetPositionBtn).toBeVisible();
  await expect(addAssetPositionBtn).not.toBeDisabled();
  await addAssetPositionBtn.click();

  // 4. Fill in the create position modal
  const uniqueAssetName = `Dashboard Corp ${Date.now()}`;
  await page.selectOption('#posPortfolio', { label: portfolioName });
  await page.selectOption('#posAsset', 'stock');
  await page.fill('#posName', uniqueAssetName);
  await page.fill('#posTicker', 'DBC');
  await page.fill('#posIsin', 'US1234567890');
  await page.fill('#posQuantity', '100');
  await page.selectOption('#posCurrency', 'USD');

  // 5. Submit the position
  await page.click('button:has-text("Record Holding")');

  // 6. Verify the position appears in the "Aggregated Positions" table on the dashboard
  const positionRow = page.locator('.premium-table tbody tr', { hasText: uniqueAssetName });
  await expect(positionRow).toBeVisible();
  await expect(positionRow).toContainText('DBC');
  await expect(positionRow).toContainText('US1234567890');

  // 7. Click the "Remove Position" button for that row in the table
  const deleteBtn = positionRow.locator('button[title="Remove Position"]');
  await expect(deleteBtn).toBeVisible();
  await deleteBtn.click();

  // 8. Confirm the deletion in the confirm modal
  const confirmModal = page.locator('.fixed.inset-0', { hasText: 'Delete Position?' });
  await expect(confirmModal).toBeVisible();
  await confirmModal.locator('button:has-text("Delete Position")').click();

  // 9. Verify the row is no longer present
  await expect(confirmModal).not.toBeVisible();
  await expect(positionRow).not.toBeVisible();

  // 10. Navigate to the newly created portfolio via the sidebar link (Clean up)
  const portfolioLink = page.locator('.sidebar-nav a', { hasText: portfolioName });
  await expect(portfolioLink).toBeVisible();
  await portfolioLink.click();

  // Verify portfolio page loaded
  await expect(page.locator('.page-header h1')).toContainText(portfolioName);

  // Click "Delete Portfolio"
  const deletePortfolioBtn = page.locator('button[title="Delete Portfolio"]');
  await expect(deletePortfolioBtn).toBeVisible();
  await deletePortfolioBtn.click();

  // Wait for the confirmation modal with text "Delete Strategy?"
  const deletePortfolioModal = page.locator('.fixed.inset-0', { hasText: 'Delete Strategy?' });
  await expect(deletePortfolioModal).toBeVisible();

  // Click the "Delete Strategy" button
  await deletePortfolioModal.locator('button:has-text("Delete Strategy")').click();

  // Verify redirect back to Dashboard
  await expect(deletePortfolioModal).not.toBeVisible();
  await expect(page.locator('h1')).toHaveText('Global Dashboard');
});
