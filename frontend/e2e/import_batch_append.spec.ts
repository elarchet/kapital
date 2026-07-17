import { test, expect, type Locator, type Page } from '@playwright/test';

// Covers composing a batch from mixed sources in the tick-based file selector:
// uploads join the list ticked and flagged "New", previously stored files can
// be ticked in, re-uploads merge instead of duplicating, growing the batch
// preserves Step 1 mapping work, and the drawer header shows the variant
// currently being mapped in Step 2.

// Unique per run so re-imports on a persistent dev DB never collide on dedup keys.
const runId = Date.now();

const csvContent = [
  'ID,Action,Time,Ticker,Name,Quantity,Price,Total,Currency',
  `A-${runId}-1,BUY,2026-01-15 10:30:00,NVDA,NVIDIA Corp,10,120.50,1205.00,USD`,
  `A-${runId}-2,SELL,2026-02-20 14:05:00,NVDA,NVIDIA Corp,5,130.00,650.00,USD`,
].join('\n');

// Same format, columns reordered plus an extra "Notes" column: merged by
// header name into the batch union.
const csvContent2 = [
  'Action,ID,Time,Ticker,Name,Quantity,Price,Total,Currency,Notes',
  `BUY,A-${runId}-3,2026-03-15 10:30:00,NVDA,NVIDIA Corp,2,110.00,220.00,USD,march buy`,
].join('\n');

// Loaded (and thereby stored) in an earlier wizard session, then ticked into
// the live batch from the selector.
const csvContent3 = [
  'ID,Action,Time,Ticker,Name,Quantity,Price,Total,Currency',
  `A-${runId}-4,DIVIDEND,2026-04-10 09:00:00,NVDA,NVIDIA Corp,,,15.00,USD`,
].join('\n');

async function pickOption(page: Page, trigger: Locator, optionLabel: string) {
  await trigger.click();
  const option = page.locator('div[data-option-index]', { hasText: optionLabel }).first();
  await expect(option).toBeVisible();
  await option.click();
}

async function openImportWizard(page: Page) {
  await page.click('#btn-add-position-component');
  await page.click('button:has-text("Import File")');
  await expect(page.getByTestId('import-file-dropzone')).toBeVisible();
}

test('import wizard: batch composed from ticked uploads and stored files, header shows mapped type', async ({ page }) => {
  test.setTimeout(120_000);
  // ---- 1. Login + self-heal leftovers from aborted runs ----
  await page.goto('/');
  await expect(page).toHaveURL(/.*\/login/);
  await page.fill('#email', 'test@example.com');
  await page.fill('#password', 'password123');
  await page.click('button:has-text("Access Platform")');
  await expect(page.locator('h1')).toHaveText('Global Dashboard');

  const token = await page.evaluate(() => localStorage.getItem('kapital_token'));
  const auth = { Authorization: `Bearer ${token}` };
  const portfolios = await (await page.request.get('/api/v1/portfolios/', { headers: auth })).json();
  for (const p of portfolios) {
    if (/^Batch Append QA /.test(p.name)) {
      await page.request.delete(`/api/v1/portfolios/${p.id}`, { headers: auth });
    }
  }
  const storedFiles = await (await page.request.get('/api/v1/imported-files/', { headers: auth })).json();
  for (const f of storedFiles) {
    if (/^e2e_append_/.test(f.filename)) {
      await page.request.delete(`/api/v1/imported-files/${f.id}`, { headers: auth });
    }
  }
  await page.reload();
  await expect(page.locator('h1')).toHaveText('Global Dashboard');

  // ---- 2. Scratch portfolio ----
  await page.locator('button[title="Create Portfolio"]').first().click();
  const renameInput = page.locator('.sidebar-nav input');
  await expect(renameInput).toBeVisible();
  const portfolioName = `Batch Append QA ${runId}`;
  await renameInput.fill(portfolioName);
  await renameInput.press('Enter');
  await expect(page.locator('.page-header h1')).toContainText(portfolioName);

  // ---- 3. Load a file once and abandon: it is stored for later re-use ----
  await openImportWizard(page);
  const importHeader = page.locator('h3', { hasText: 'Import Transactions' });
  await page.setInputFiles('input[type="file"]', {
    name: 'e2e_append_stored.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csvContent3),
  });
  const storedRow = page.getByTestId('import-file-row-e2e_append_stored.csv');
  await expect(storedRow).toBeVisible();
  await expect(storedRow.locator('input[type="checkbox"]')).toBeChecked();
  // No batch was built: Cancel closes directly, the file stays stored.
  await page.click('button:has-text("Cancel")');
  await expect(importHeader).not.toBeVisible();

  // ---- 4. Start a batch with file 1 ----
  await openImportWizard(page);
  await page.setInputFiles('input[type="file"]', {
    name: 'e2e_append_main.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csvContent),
  });
  await page.getByTestId('continue-with-files').click();
  await expect(page.getByText('e2e_append_main.csv')).toBeVisible();

  // Force a fresh custom mapping and do some Step 1 work BEFORE growing the
  // batch, to prove appending preserves it.
  const templateDropdown = page
    .locator('.form-group', { hasText: 'Template Schema' })
    .locator('button')
    .first();
  await pickOption(page, templateDropdown, 'Custom Mapping Template...');
  const typeColDropdown = page
    .locator('.form-group', { hasText: 'Transaction Type Column' })
    .locator('button');
  await pickOption(page, typeColDropdown, 'Action');
  await pickOption(page, page.getByTestId('optype-row-BUY').locator('button').last(), 'trade');

  // ---- 5. Reopen the selector: the batch file is ticked, uploads join ticked ----
  await page.getByTestId('change-files-button').click();
  const mainRow = page.getByTestId('import-file-row-e2e_append_main.csv');
  await expect(mainRow).toBeVisible();
  await expect(mainRow.locator('input[type="checkbox"]')).toBeChecked();
  await expect(mainRow.getByText('New')).toBeVisible(); // loaded this session

  await page.setInputFiles('input[type="file"]', {
    name: 'e2e_append_extra.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csvContent2),
  });
  const extraRow = page.getByTestId('import-file-row-e2e_append_extra.csv');
  await expect(extraRow.locator('input[type="checkbox"]')).toBeChecked();
  await expect(extraRow.getByText('New')).toBeVisible();

  // Re-uploading a file already in the list merges instead of duplicating.
  await page.setInputFiles('input[type="file"]', {
    name: 'e2e_append_main.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csvContent),
  });
  await expect(
    page.getByTestId('import-file-list').locator('[data-testid^="import-file-row-"]').filter({ hasText: 'e2e_append_main.csv' })
  ).toHaveCount(1);

  // ---- 6. Tick the stored file in as well and continue: batch grows to 3 ----
  await storedRow.click();
  await page.getByTestId('continue-with-files').click();
  await expect(page.getByText('3 files imported as one batch')).toBeVisible();
  await expect(page.getByText('e2e_append_stored.csv')).toBeVisible();

  // Step 1 work survived the append...
  await expect(typeColDropdown).toContainText('Action');
  await expect(page.getByTestId('optype-row-BUY').locator('button').last()).toContainText('trade');
  // ...and the added files' rows joined the pool: the stored file brought a
  // new DIVIDEND raw action to map.
  await expect(page.getByTestId('optype-row-DIVIDEND')).toBeVisible();
  await pickOption(page, page.getByTestId('optype-row-DIVIDEND').locator('button').last(), 'dividend');

  // ---- 7. Step 2: the drawer header pins the variant being mapped ----
  await page.click('button:has-text("Next: Configure Column Mappings")');
  const headerVariant = page.getByTestId('header-mapping-variant');
  await expect(headerVariant).toContainText('trade'); // auto-selected first pill
  // Both files' BUY rows count toward the pill (SELL was left unmapped).
  await expect(page.getByTestId('optype-pill-trade')).toContainText('2 rows');
  await page.getByTestId('optype-pill-dividend').click();
  await expect(headerVariant).toContainText('dividend');

  // ---- 8. Cleanup: abandon, delete stored copies and the portfolio ----
  await page.click('button:has-text("Cancel")');
  await page.locator('button:has-text("Discard Changes")').click();
  await expect(importHeader).not.toBeVisible();

  const cleanupFiles = await (await page.request.get('/api/v1/imported-files/', { headers: auth })).json();
  for (const f of cleanupFiles) {
    if (/^e2e_append_/.test(f.filename)) {
      await page.request.delete(`/api/v1/imported-files/${f.id}`, { headers: auth });
    }
  }
  await page.locator('button[title="Delete Portfolio"]').click();
  const deletePortfolioModal = page.locator('.fixed.inset-0', { hasText: 'Delete Strategy?' });
  await deletePortfolioModal.locator('button:has-text("Delete Strategy")').click();
  await expect(page.locator('h1')).toHaveText('Global Dashboard');
});
