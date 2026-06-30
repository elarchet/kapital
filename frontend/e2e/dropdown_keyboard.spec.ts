import { test, expect } from '@playwright/test';

test('verify custom dropdown keyboard navigation and filtering', async ({ page }) => {
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
  const addPortfolioBtn = page.locator('button[title="Create Portfolio"]').first();
  await expect(addPortfolioBtn).toBeVisible();
  await addPortfolioBtn.click();

  // Wait for the inline renaming input to appear in the sidebar
  const renameInput = page.locator('.sidebar-nav input');
  await expect(renameInput).toBeVisible();

  // Rename the portfolio inline
  const portfolioName = `Dropdown QA Strategy ${Date.now()}`;
  await renameInput.fill(portfolioName);
  await renameInput.press('Enter');

  // Verify rename input is gone and the sidebar link is updated
  await expect(renameInput).not.toBeVisible();
  const portfolioLink = page.locator('.sidebar-nav a', { hasText: portfolioName });
  await expect(portfolioLink).toBeVisible();

  // Verify portfolio page loaded
  await expect(page.locator('.page-header h1')).toContainText(portfolioName);

  // 3. Trigger Import modal by setting files on the hidden input
  await page.setInputFiles('input[type="file"]', '../from_2026-01-01_to_2026-05-25_MTc3OTczMDI0NzIwNw.csv');

  // Verify the Import Transactions Modal is open (as a drawer)
  const importHeader = page.locator('h3', { hasText: 'Import Transactions' });
  await expect(importHeader).toBeVisible();

  // --- Test Non-Searchable Dropdown (Delimiter) ---
  const delimiterDropdown = page.locator('.form-group', { hasText: 'Delimiter' }).locator('button');
  await expect(delimiterDropdown).toBeVisible();

  // Focus the Delimiter dropdown button
  await delimiterDropdown.focus();

  // Press key 's' to filter options to Semicolon
  await page.keyboard.press('s');

  // The dropdown panel should be open. Since options are teleported, query globally
  // Wait for the dropdown options to appear
  const semicolonOption = page.locator('div[data-option-index="0"]', { hasText: 'Semicolon' });
  await expect(semicolonOption).toBeVisible();

  // Press Enter to select
  await page.keyboard.press('Enter');

  // Verify it selected Semicolon (;)
  await expect(delimiterDropdown).toContainText('Semicolon (;)');

  // --- Test Searchable Dropdown (Transaction Type Column) ---
  const typeColDropdown = page.locator('.form-group', { hasText: 'Transaction Type Column' }).locator('button');
  await expect(typeColDropdown).toBeVisible();

  // Focus the Transaction Type Column dropdown button
  await typeColDropdown.focus();

  // Press key 'a' to open dropdown and focus search input
  await page.keyboard.press('a');

  // The search input in the teleported panel should be focused and have value 'a'
  const searchInput = page.locator('input[placeholder="Search..."]');
  await expect(searchInput).toBeFocused();
  await expect(searchInput).toHaveValue('a');

  // Type 'c' to search for 'ac' (matches 'Action')
  await page.keyboard.press('c');
  await expect(searchInput).toHaveValue('ac');

  // Press ArrowDown to navigate (highlight) the first matched option
  await page.keyboard.press('ArrowDown');

  // Press Enter to select
  await page.keyboard.press('Enter');

  // Verify it selected "Action"
  await expect(typeColDropdown).toContainText('Action');

  // Close the import modal (click Cancel or close button)
  const cancelBtn = page.locator('button:has-text("Cancel")');
  await cancelBtn.click();

  // Handle the confirmation dialog since changes were made
  const confirmDiscardBtn = page.locator('button:has-text("Discard Changes")');
  await expect(confirmDiscardBtn).toBeVisible();
  await confirmDiscardBtn.click();

  await expect(importHeader).not.toBeVisible();

  // 4. Delete Portfolio Strategy (Clean up)
  const deletePortfolioBtn = page.locator('button[title="Delete Portfolio"]');
  await expect(deletePortfolioBtn).toBeVisible();
  await deletePortfolioBtn.click();

  const deletePortfolioModal = page.locator('.fixed.inset-0', { hasText: 'Delete Strategy?' });
  await expect(deletePortfolioModal).toBeVisible();
  await deletePortfolioModal.locator('button:has-text("Delete Strategy")').click();

  await expect(deletePortfolioModal).not.toBeVisible();
  await expect(page.locator('h1')).toHaveText('Global Dashboard');
});
