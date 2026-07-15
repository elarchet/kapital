import { test, expect, type Locator, type Page } from '@playwright/test';

// Unique per run so re-imports on a persistent dev DB never collide on dedup keys.
const runId = Date.now();

const csvContent = [
  'ID,Action,Time,Ticker,Name,Quantity,Price,Total,Currency',
  `T-${runId}-1,BUY,2026-01-15 10:30:00,NVDA,NVIDIA Corp,10,120.50,1205.00,USD`,
  `T-${runId}-2,SELL,2026-02-20 14:05:00,NVDA,NVIDIA Corp,5,130.00,650.00,USD`,
  `T-${runId}-3,DIVIDEND,2026-03-10 09:00:00,NVDA,NVIDIA Corp,,,12.34,USD`,
].join('\n');

// Custom dropdowns teleport their option panel to the body: open the trigger,
// then click the first option whose text matches.
async function pickOption(page: Page, trigger: Locator, optionLabel: string) {
  await trigger.click();
  const option = page.locator('div[data-option-index]', { hasText: optionLabel }).first();
  await expect(option).toBeVisible();
  await option.click();
}

test('import wizard: full drag-and-drop mapping, formula, enums, auto-ID, template round-trip', async ({ page }) => {
  // One long realistic journey (~60 UI actions), not a unit test.
  test.setTimeout(120_000);
  // ---- 1. Login ----
  await page.goto('/');
  await expect(page).toHaveURL(/.*\/login/);
  await page.fill('#email', 'test@example.com');
  await page.fill('#password', 'password123');
  await page.click('button:has-text("Access Platform")');
  await expect(page.locator('h1')).toHaveText('Global Dashboard');

  // Self-heal: an aborted earlier run may have left templates behind whose
  // headers match this file and would win autodetection, plus scratch
  // portfolios. Remove them through the API before starting.
  const token = await page.evaluate(() => localStorage.getItem('kapital_token'));
  const auth = { Authorization: `Bearer ${token}` };
  const schemas = await (await page.request.get('/api/v1/import-file-schemas/', { headers: auth })).json();
  for (const s of schemas) {
    if (/^E2E Import QA /.test(s.name)) {
      await page.request.delete(`/api/v1/import-file-schemas/${s.id}`, { headers: auth });
    }
  }
  const portfolios = await (await page.request.get('/api/v1/portfolios/', { headers: auth })).json();
  for (const p of portfolios) {
    if (/^(Import QA Strategy|Dbg|QA E2E Strategy) /.test(p.name)) {
      await page.request.delete(`/api/v1/portfolios/${p.id}`, { headers: auth });
    }
  }
  await page.reload();
  await expect(page.locator('h1')).toHaveText('Global Dashboard');

  // ---- 2. Create a scratch portfolio ----
  const addPortfolioBtn = page.locator('button[title="Create Portfolio"]').first();
  await addPortfolioBtn.click();
  const renameInput = page.locator('.sidebar-nav input');
  await expect(renameInput).toBeVisible();
  const portfolioName = `Import QA Strategy ${runId}`;
  await renameInput.fill(portfolioName);
  await renameInput.press('Enter');
  await expect(page.locator('.page-header h1')).toContainText(portfolioName);

  // ---- 3. Upload the CSV through the hidden file input ----
  await page.setInputFiles('input[type="file"]', {
    name: 'e2e_broker_export.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csvContent),
  });
  const importHeader = page.locator('h3', { hasText: 'Import Transactions' });
  await expect(importHeader).toBeVisible();

  // Force a fresh custom mapping even if an earlier run left a matching template.
  const templateDropdown = page
    .locator('.form-group', { hasText: 'Template Schema' })
    .locator('button')
    .first();
  await pickOption(page, templateDropdown, 'Custom Mapping Template...');

  // ---- 4. Step 1: institution + transaction type column ----
  const institutionDropdown = page.locator('.form-group', { hasText: 'Institution' }).locator('button');
  await pickOption(page, institutionDropdown, 'Custom / Other');

  // Delimiter was auto-detected from the file.
  const delimiterDropdown = page.locator('.form-group', { hasText: 'Delimiter' }).locator('button');
  await expect(delimiterDropdown).toContainText('Comma');

  const typeColDropdown = page
    .locator('.form-group', { hasText: 'Transaction Type Column' })
    .locator('button');
  await pickOption(page, typeColDropdown, 'Action');

  await page.click('button:has-text("Next: Configure Column Mappings")');

  // ---- 5. Step 2: map raw actions to operation types ----
  await expect(page.getByText('3 unmapped')).toBeVisible();
  await pickOption(page, page.getByTestId('optype-row-BUY').locator('button'), 'trade');
  await pickOption(page, page.getByTestId('optype-row-SELL').locator('button'), 'trade');
  await pickOption(page, page.getByTestId('optype-row-DIVIDEND').locator('button'), 'dividend');
  // Panel auto-collapses once everything is mapped.
  await expect(page.getByText('3 mapped')).toBeVisible();

  // Op type pills appear; trade is auto-selected and shows its row count.
  const tradePill = page.getByTestId('optype-pill-trade');
  const dividendPill = page.getByTestId('optype-pill-dividend');
  await expect(tradePill).toContainText('2 rows');
  await expect(tradePill).toContainText('0/7 required');
  await expect(dividendPill).toContainText('1 rows');

  // ---- 6. Map trade fields via all three assignment paths ----
  // A mapped slot renders the source header as a chip with title=<header>.
  const mappedChip = (fieldKey: string, header: string) =>
    page.getByTestId(`field-slot-${fieldKey}`).locator(`span[title="${header}"]`);

  // (a) Native HTML5 drag and drop.
  await page.getByTestId('csv-chip-Time').dragTo(page.getByTestId('field-slot-executed_at'));
  await expect(mappedChip('executed_at', 'Time')).toBeVisible();

  // (b) Click-to-arm a chip, then click the destination slot.
  await page.getByTestId('csv-chip-Total').click();
  await expect(page.getByTestId('field-slot-total_amount')).toContainText('place here');
  await page.getByTestId('field-slot-total_amount').click();
  await expect(mappedChip('total_amount', 'Total')).toBeVisible();

  // Escape disarms without assigning.
  await page.getByTestId('csv-chip-Name').click();
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('field-slot-name')).not.toContainText('place here');

  // (c) Per-slot dropdown.
  await pickOption(page, page.getByTestId('field-slot-currency').locator('button').first(), 'Currency');
  await expect(mappedChip('currency', 'Currency')).toBeVisible();

  await page.getByTestId('csv-chip-Ticker').click();
  await page.getByTestId('field-slot-ticker').click();
  await expect(mappedChip('ticker', 'Ticker')).toBeVisible();
  await page.getByTestId('csv-chip-Quantity').click();
  await page.getByTestId('field-slot-quantity').click();
  await expect(mappedChip('quantity', 'Quantity')).toBeVisible();
  await page.getByTestId('csv-chip-Price').click();
  await page.getByTestId('field-slot-unit_price').click();
  await expect(mappedChip('unit_price', 'Price')).toBeVisible();
  await expect(tradePill).toContainText('6/7 required');

  // ---- 7. Enum field: modal auto-opens on assignment ----
  await page.getByTestId('csv-chip-Action').click();
  await page.getByTestId('field-slot-trade_side').click();
  const configModal = page.getByTestId('field-config-modal');
  await expect(configModal).toBeVisible();
  await expect(configModal).toContainText('Trade Side');
  await pickOption(page, configModal.locator('.grid', { hasText: 'BUY' }).locator('button'), 'buy');
  await pickOption(page, configModal.locator('.grid', { hasText: 'SELL' }).locator('button'), 'sell');
  await configModal.locator('button:has-text("Save")').click();
  await expect(configModal).not.toBeVisible();
  await expect(page.getByTestId('field-slot-trade_side')).toContainText('2 enums');

  // Dirty-check: an edited modal asks for confirmation before discarding.
  await page.getByTestId('field-slot-trade_side').locator('button[title*="Advanced settings"]').click();
  await expect(configModal).toBeVisible();
  await pickOption(page, configModal.locator('.grid', { hasText: 'SELL' }).locator('button'), 'buy');
  await page.keyboard.press('Escape');
  // .last() = innermost overlay; the modal nests inside the drawer overlays.
  const discardConfirm = page.locator('.fixed.inset-0', { hasText: 'Discard Unsaved Changes?' }).last();
  await expect(discardConfirm).toBeVisible();
  await discardConfirm.locator('button:has-text("Keep Editing")').click();
  await expect(discardConfirm).not.toBeVisible();
  await expect(configModal).toBeVisible();
  await configModal.locator('button:has-text("Cancel")').click();
  await discardConfirm.locator('button:has-text("Discard Changes")').click();
  await expect(configModal).not.toBeVisible();
  await expect(page.getByTestId('field-slot-trade_side')).toContainText('2 enums');

  // All 7 required trade fields are now mapped and every trade row parses.
  await expect(tradePill).not.toContainText('required');
  await expect(page.getByText('2/2 rows parse cleanly')).toBeVisible();

  // ---- 8. Formula builder: total_amount = Quantity × Price ----
  await page.getByTestId('field-slot-total_amount').locator('button[title*="Advanced settings"]').click();
  await expect(configModal).toBeVisible();
  await configModal.locator('button:has-text("Formula")').click();
  await pickOption(page, configModal.locator('button', { hasText: '+ Column…' }), 'Quantity');
  await configModal.locator('button:text-is("×")').click();
  await pickOption(page, configModal.locator('button', { hasText: '+ Column…' }), 'Price');
  await expect(configModal).toContainText('✓ On the current example row:');
  await configModal.locator('button:has-text("Save")').click();
  await expect(page.getByTestId('field-slot-total_amount')).toContainText('formula');
  await expect(page.getByText('2/2 rows parse cleanly')).toBeVisible();

  // ---- 9. Dividend op type: map required fields + auto-generated ID ----
  await dividendPill.click();
  await expect(mappedChip('executed_at', 'Time')).not.toBeVisible(); // per-op-type view

  await page.getByTestId('csv-chip-Time').click();
  await page.getByTestId('field-slot-executed_at').click();
  await expect(mappedChip('executed_at', 'Time')).toBeVisible();
  await page.getByTestId('csv-chip-Total').click();
  await page.getByTestId('field-slot-total_amount').click();
  await expect(mappedChip('total_amount', 'Total')).toBeVisible();
  await page.getByTestId('csv-chip-Currency').click();
  await page.getByTestId('field-slot-currency').click();
  await expect(mappedChip('currency', 'Currency')).toBeVisible();
  // Ticker isn't required for dividends, but name auto-enrichment (default
  // "when empty") needs it to resolve the asset name.
  await page.getByTestId('csv-chip-Ticker').click();
  await page.getByTestId('field-slot-ticker').click();
  await expect(mappedChip('ticker', 'Ticker')).toBeVisible();

  // Auto-ID with a hash-column subset, reachable on the unmapped Transaction ID slot.
  await page.getByTestId('field-slot-transaction_id').locator('button[title*="Advanced settings"]').click();
  await expect(configModal).toBeVisible();
  await expect(configModal).toContainText('Auto-generated Transaction ID');
  await configModal.locator('label', { hasText: 'Always' }).locator('input[type="radio"]').check();
  // Unchecking materializes an explicit subset; dedup-change warning appears.
  // Keep "ID" checked: dedup keys are per financial account (shared across
  // runs), and ID is this file's only run-unique column.
  await configModal.getByRole('checkbox', { name: 'Name', exact: true }).uncheck();
  await expect(configModal).toContainText('Changing this changes dedup keys');
  await configModal.locator('button:has-text("Save")').click();
  await expect(page.getByTestId('field-slot-transaction_id')).toContainText('auto-generated');

  await expect(dividendPill).not.toContainText('required');
  await expect(page.getByText('1/1 rows parse cleanly')).toBeVisible();

  // ---- 10. Save as template and import ----
  const templateName = `E2E Import QA ${runId}`;
  await page.getByText('Save this configuration mapping as a template').click();
  await page.fill('input[placeholder="e.g. My Custom Broker CSV"]', templateName);
  await page.click('button:has-text("Save Template & Import")');

  await expect(page.getByText('successfully parsed and processed')).toBeVisible({ timeout: 15000 });
  // The stat value renders in the label's sibling div.
  const importedStat = page
    .getByText('Transactions Imported', { exact: true })
    .locator('xpath=following-sibling::div');
  await expect(importedStat).toHaveText('3');
  await page.click('button:has-text("Done")');
  await expect(importHeader).not.toBeVisible();

  // The imported buy/sell trades materialized an NVDA position (10 bought − 5 sold).
  const nvdaRow = page.locator('.premium-table tbody tr', { hasText: 'NVDA' });
  await expect(nvdaRow).toBeVisible();

  // ---- 11. Template round-trip: re-upload autodetects the saved template ----
  await page.setInputFiles('input[type="file"]', {
    name: 'e2e_broker_export.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csvContent),
  });
  await expect(importHeader).toBeVisible();
  await expect(page.getByText('✓ Autodetected format matching this file')).toBeVisible();
  await expect(templateDropdown).toContainText(templateName);

  // Clean up the template through the wizard's own delete flow.
  await page.locator('button[title="Delete this template"]').click();
  const deleteTemplateModal = page.locator('.fixed.inset-0', { hasText: 'Delete Template?' });
  await deleteTemplateModal.locator('button:has-text("Delete Template")').click();
  await expect(deleteTemplateModal).not.toBeVisible();

  await page.click('button:has-text("Cancel")');
  const discardBtn = page.locator('button:has-text("Discard Changes")');
  await expect(discardBtn).toBeVisible();
  await discardBtn.click();
  await expect(importHeader).not.toBeVisible();

  // ---- 12. Delete the scratch portfolio ----
  await page.locator('button[title="Delete Portfolio"]').click();
  const deletePortfolioModal = page.locator('.fixed.inset-0', { hasText: 'Delete Strategy?' });
  await deletePortfolioModal.locator('button:has-text("Delete Strategy")').click();
  await expect(page.locator('h1')).toHaveText('Global Dashboard');
});
