<script setup lang="ts">
defineProps<{
  parsedPreviewRows: Array<{
    time: string;
    action: string;
    opType: string;
    ticker: string;
    name: string;
    isin: string;
    quantity: string;
    price: string;
    total: string;
    currency: string;
    fees: string;
    merchant: string;
  }>;
}>();
</script>

<template>
  <div>
    <h4 style="font-size: 1rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
      <span>Mapped Output Preview</span>
      <span style="font-size: 0.7rem; background-color: var(--accent-light); color: var(--accent-color); padding: 0.15rem 0.4rem; border-radius: 4px; font-weight: 600;">Real-time</span>
    </h4>
    <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 1rem;">
      This shows exactly how the first few lines of your CSV will be parsed and loaded into the database according to your selected template.
    </p>

    <div v-if="parsedPreviewRows.length === 0" style="border: 1px dashed var(--border-color); border-radius: var(--radius-md); padding: 3rem 1.5rem; text-align: center; color: var(--text-tertiary); font-size: 0.85rem;">
      Select a template to see the parsed transactions preview here.
    </div>

    <div v-else style="overflow-x: auto; border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
      <table class="preview-table" style="margin-top: 0; font-size: 0.7rem; width: 100%;">
        <thead>
          <tr>
            <th>Time</th>
            <th>Type</th>
            <th>Asset Name (Ticker/ISIN)</th>
            <th>Qty</th>
            <th>Price</th>
            <th>Total</th>
            <th>Fees/Taxes</th>
            <th>Merchant</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in parsedPreviewRows" :key="idx">
            <td>{{ row.time || '—' }}</td>
            <td>
              <span class="badge" :class="'badge-' + row.opType" style="padding: 0.15rem 0.35rem; font-size: 0.65rem; text-transform: uppercase;">
                {{ row.opType }}
              </span>
            </td>
            <td>
              <div style="font-weight: 600; color: var(--text-primary);">{{ row.name || 'Asset' }}</div>
              <span style="color: var(--text-secondary); font-size: 0.65rem;">
                {{ row.ticker }}{{ row.ticker && row.isin ? '/' : '' }}{{ row.isin }}
              </span>
            </td>
            <td style="font-family: monospace;">{{ row.quantity }}</td>
            <td style="font-family: monospace;">{{ row.price }} {{ row.currency }}</td>
            <td style="font-family: monospace; font-weight: 600;">{{ row.total }} {{ row.currency }}</td>
            <td>
              <span style="color: var(--text-secondary);">{{ row.fees }}</span>
            </td>
            <td>
              <span style="color: var(--text-secondary);">{{ row.merchant }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

