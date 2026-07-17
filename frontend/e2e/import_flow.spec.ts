import { test, expect, type Locator, type Page } from '@playwright/test';

// Unique per run so re-imports on a persistent dev DB never collide on dedup keys.
const runId = Date.now();

const csvContent = [
  'ID,Action,Time,Ticker,Name,Quantity,Price,Total,Currency',
  `T-${runId}-1,BUY,2026-01-15 10:30:00,NVDA,NVIDIA Corp,10,120.50,1205.00,USD`,
  `T-${runId}-2,SELL,2026-02-20 14:05:00,NVDA,NVIDIA Corp,5,130.00,650.00,USD`,
  `T-${runId}-3,DIVIDEND,2026-03-10 09:00:00,NVDA,NVIDIA Corp,,,12.34,USD`,
].join('\n');

// Second file of the same batch: columns reordered (rows are remapped by
// header name) plus an extra "Notes" column that file 1 lacks (broker period
// exports only carry the columns used in the period — merged as a union,
// missing cells read as empty). One row is duplicated from file 1 — still
// dropped by dedup at import since its extra Notes cell is empty — and one
// dividend is genuinely new.
const csvContent2 = [
  'Action,ID,Time,Ticker,Name,Quantity,Price,Total,Currency,Notes',
  `BUY,T-${runId}-1,2026-01-15 10:30:00,NVDA,NVIDIA Corp,10,120.50,1205.00,USD,`,
  `DIVIDEND,T-${runId}-4,2026-04-10 09:00:00,NVDA,NVIDIA Corp,,,15.00,USD,April payout`,
].join('\n');

// Custom dropdowns teleport their option panel to the body: open the trigger,
// then click the first option whose text matches.
async function pickOption(page: Page, trigger: Locator, optionLabel: string) {
  await trigger.click();
  const option = page.locator('div[data-option-index]', { hasText: optionLabel }).first();
  await expect(option).toBeVisible();
  await option.click();
}

// The wizard opens on an empty state (file dropzone + previously imported
// files); its hidden file input is the upload entry point.
async function openImportWizard(page: Page) {
  await page.click('#btn-add-position-component');
  await page.click('button:has-text("Import File")');
  await expect(page.getByTestId('import-file-dropzone')).toBeVisible();
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

  // ---- 3. Upload two CSVs at once through the wizard's empty state ----
  await openImportWizard(page);
  const importHeader = page.locator('h3', { hasText: 'Import Transactions' });
  await expect(importHeader).toBeVisible();
  await page.setInputFiles('input[type="file"]', [
    { name: 'e2e_broker_export.csv', mimeType: 'text/csv', buffer: Buffer.from(csvContent) },
    { name: 'e2e_broker_export_2.csv', mimeType: 'text/csv', buffer: Buffer.from(csvContent2) },
  ]);
  await expect(page.getByText('2 files imported as one batch')).toBeVisible();

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

  // ---- 5. Step 1: map raw actions to operation types ----
  const nextBtn = page.locator('button:has-text("Next: Configure Column Mappings")');
  await expect(nextBtn).toBeDisabled(); // nothing mapped yet
  await expect(page.getByText('3 unmapped')).toBeVisible();

  // Clicking a raw action's row count opens the matching raw file rows, with
  // per-file provenance since this batch merged two files.
  await page.getByTestId('optype-count-BUY').click();
  const rawRowsModal = page.getByTestId('raw-rows-modal');
  await expect(rawRowsModal).toBeVisible();
  await expect(rawRowsModal.locator('tbody tr')).toHaveCount(2); // one BUY per file
  await expect(rawRowsModal.getByText('e2e_broker_export.csv', { exact: true })).toBeVisible();
  await expect(rawRowsModal.getByText('e2e_broker_export_2.csv', { exact: true })).toBeVisible();
  await rawRowsModal.getByRole('button', { name: 'Close' }).click();
  await expect(rawRowsModal).not.toBeVisible();

  await pickOption(page, page.getByTestId('optype-row-BUY').locator('button').last(), 'trade');
  await expect(nextBtn).toBeEnabled(); // one mapped action is enough to proceed
  await pickOption(page, page.getByTestId('optype-row-SELL').locator('button').last(), 'trade');
  await pickOption(page, page.getByTestId('optype-row-DIVIDEND').locator('button').last(), 'dividend');
  // Panel auto-collapses once everything is mapped.
  await expect(page.getByText('3 mapped')).toBeVisible();

  // ---- 5b. Split mode round-trip: trade (BUY+SELL) can map each action separately ----
  const splitToggle = page.getByTestId('split-toggle-trade');
  await expect(splitToggle).toBeVisible(); // stays visible while the rows list is collapsed
  await splitToggle.check();
  await nextBtn.click();
  // One pill per raw action instead of a single trade pill.
  await expect(page.getByTestId('optype-pill-BUY')).toBeVisible();
  await expect(page.getByTestId('optype-pill-SELL')).toBeVisible();
  await expect(page.getByTestId('optype-pill-trade')).not.toBeVisible();
  await page.click('button:has-text("Back to Step 1")');
  await splitToggle.uncheck();

  await nextBtn.click();

  // Op type pills appear; trade is auto-selected and shows its row count.
  const tradePill = page.getByTestId('optype-pill-trade');
  const dividendPill = page.getByTestId('optype-pill-dividend');
  // Counts include both files' rows (the cross-file duplicate BUY counts here;
  // it's only dropped by dedup at import time).
  await expect(tradePill).toContainText('3 rows');
  await expect(tradePill).toContainText('0/7 required');
  await expect(dividendPill).toContainText('2 rows');

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

  // One CSV column can feed several DB fields: reuse "Currency" for price_currency
  // without clearing the existing currency mapping.
  await pickOption(page, page.getByTestId('field-slot-price_currency').locator('button').first(), 'Currency');
  await expect(mappedChip('price_currency', 'Currency')).toBeVisible();
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
  await expect(page.getByText('3/3 rows parse cleanly')).toBeVisible();

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
  await expect(page.getByText('3/3 rows parse cleanly')).toBeVisible();

  // ---- 8b. Extra fee groups: add creates suffixed slots, remove cleans them up ----
  await page.getByTestId('add-fee-group').click();
  await expect(page.getByTestId('field-slot-fee_amount__2')).toBeVisible();
  await expect(page.getByTestId('field-slot-fee_type__2')).toBeVisible();
  await page.getByTestId('remove-fee-group-2').click();
  await expect(page.getByTestId('field-slot-fee_amount__2')).not.toBeVisible();

  // ---- 8c. Multi-select pills: Ctrl+click adds a type; mappings apply to all ----
  await dividendPill.click({ modifiers: ['ControlOrMeta'] });
  // executed_at is mapped for trade but not dividend → the slot shows the divergence.
  await expect(page.getByTestId('field-slot-executed_at')).toContainText('varies per type');
  // One assignment maps the column for both selected types.
  await page.getByTestId('csv-chip-Currency').click();
  await page.getByTestId('field-slot-currency').click();
  await expect(mappedChip('currency', 'Currency')).toBeVisible(); // unified again
  // Plain click returns to single selection; both types kept the mapping.
  await dividendPill.click();
  await expect(mappedChip('currency', 'Currency')).toBeVisible();
  await tradePill.click();
  await expect(mappedChip('currency', 'Currency')).toBeVisible();

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
  await expect(page.getByText('2/2 rows parse cleanly')).toBeVisible();

  // ---- 10. Save as template and import ----
  const templateName = `E2E Import QA ${runId}`;
  await page.getByText('Save this configuration mapping as a template').click();
  await page.fill('input[placeholder="e.g. My Custom Broker CSV"]', templateName);
  await page.click('button:has-text("Save Template & Import")');

  await expect(page.getByText('successfully parsed and processed')).toBeVisible({ timeout: 15000 });
  // The stat value renders in the label's sibling div. 5 rows across both
  // files, minus the cross-file duplicate BUY caught by dedup.
  const importedStat = page
    .getByText('Transactions Imported', { exact: true })
    .locator('xpath=following-sibling::div');
  await expect(importedStat).toHaveText('4');
  const skippedStat = page
    .getByText('Skipped', { exact: true })
    .locator('xpath=following-sibling::div');
  await expect(skippedStat).toHaveText('1');
  await page.click('button:has-text("Done")');
  await expect(importHeader).not.toBeVisible();

  // The imported buy/sell trades materialized an NVDA position (10 bought − 5 sold).
  const nvdaRow = page.locator('.premium-table tbody tr', { hasText: 'NVDA' });
  await expect(nvdaRow).toBeVisible();

  // ---- 11. Stored-file round-trip: both files are listed and re-importable ----
  // Every uploaded file was persisted server-side; the wizard's empty state
  // lists them (most recently used first, so this run's files lead even on a
  // persistent dev DB carrying files from earlier runs).
  await openImportWizard(page);
  const previousImports = page.getByTestId('previous-imports-list');
  await expect(previousImports).toBeVisible();
  const storedRows = previousImports.locator('[data-testid^="previous-import-row-"]');
  await expect(storedRows.first()).toContainText(/e2e_broker_export(_2)?\.csv/);
  await expect(storedRows.nth(1)).toContainText(/e2e_broker_export(_2)?\.csv/);
  // File 1 produced 3 transactions (its BUY duplicated in file 2 counts on
  // whichever file imported first — file 1).
  const file1Row = storedRows.filter({ hasText: 'e2e_broker_export.csv' }).first();
  await expect(file1Row).toContainText('3 transactions');

  // Re-importing a stored file feeds it back through the wizard; row-level
  // dedup then skips everything, importing nothing twice.
  await file1Row.locator('button:has-text("Re-import")').click();
  await expect(page.getByText('✓ Autodetected format matching this file')).toBeVisible();
  await page.click('button:has-text("Import Transactions")');
  await expect(page.getByText('successfully parsed and processed')).toBeVisible({ timeout: 15000 });
  await expect(importedStat).toHaveText('0');
  await expect(skippedStat).toHaveText('3');
  await page.click('button:has-text("Done")');
  await expect(importHeader).not.toBeVisible();

  // ---- 12. Template round-trip: re-upload autodetects the saved template ----
  await openImportWizard(page);
  await page.setInputFiles('input[type="file"]', {
    name: 'e2e_broker_export.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csvContent),
  });
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

  // ---- 13. Delete the stored copies (file-only delete; transactions stay) ----
  // Also keeps the persistent dev DB from accumulating this run's files.
  await openImportWizard(page);
  await expect(previousImports).toBeVisible();
  for (const name of ['e2e_broker_export.csv', 'e2e_broker_export_2.csv']) {
    const rows = storedRows.filter({ hasText: name });
    const before = await rows.count();
    await rows.first().locator('button[title="Delete stored file"]').click();
    const deleteFileModal = page.locator('.fixed.inset-0', { hasText: 'Delete Stored File?' }).last();
    await expect(deleteFileModal).toContainText('Transactions already imported from it are kept');
    await deleteFileModal.locator('button:has-text("Delete File")').click();
    await expect(rows).toHaveCount(before - 1);
  }
  await page.click('button:has-text("Cancel")'); // empty state isn't dirty: closes directly
  await expect(importHeader).not.toBeVisible();
  // The transactions imported from the deleted files are untouched.
  await expect(nvdaRow).toBeVisible();

  // ---- 14. Delete the scratch portfolio ----
  await page.locator('button[title="Delete Portfolio"]').click();
  const deletePortfolioModal = page.locator('.fixed.inset-0', { hasText: 'Delete Strategy?' });
  await deletePortfolioModal.locator('button:has-text("Delete Strategy")').click();
  await expect(page.locator('h1')).toHaveText('Global Dashboard');
});
