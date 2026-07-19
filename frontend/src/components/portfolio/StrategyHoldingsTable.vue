<script setup lang="ts">
import { Grid, Trash2 } from '@lucide/vue';
import type { Portfolio } from '../../store';
import type { PositionValuation, PriceStatus } from '../../services/portfolioApi';
import { assetTypeLabel } from '../../config/assetTypes';

const props = defineProps<{
  positions: PositionValuation[];
  portfolioId: number | 'unassigned';
  portfolios: Portfolio[];
  currency: string;
}>();

const emit = defineEmits<{
  (e: 'deletePosition', position: PositionValuation): void;
  (e: 'movePosition', payload: { position: PositionValuation; targetPortfolioId: number }): void;
  (e: 'openAddModal'): void;
  (e: 'selectPosition', position: PositionValuation): void;
}>();

const formatCurrency = (val: string | number | null, cur?: string) => {
  if (val === null) return '—';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: cur || props.currency || 'EUR',
  }).format(Number(val));
};

const formatQuantity = (val: string) => {
  const num = Number(val);
  return Number.isInteger(num) ? String(num) : num.toLocaleString('fr-FR', { maximumFractionDigits: 8 });
};

const PRICE_STATUS_HINTS: Record<PriceStatus, string> = {
  ok: 'Live market close',
  stale: 'Last close is more than 3 days old',
  cost_fallback: 'No market price available — valued at cost',
  fixed: 'Cash — price is 1 by definition',
};

const gainClass = (gain: string) =>
  Number(gain) >= 0 ? 'text-color-success' : 'text-color-danger';
</script>

<template>
  <section class="table-container">
    <div class="table-header-block">
      <h3 class="table-title">Portfolio Repartition</h3>
      <span class="text-xs font-semibold text-text-secondary bg-bg-tertiary px-2 py-1 rounded border border-border-color">
        {{ positions.length }} asset{{ positions.length === 1 ? '' : 's' }}
      </span>
    </div>

    <div v-if="!positions.length" class="empty-state">
      <Grid class="empty-icon" />
      <h3>This strategy folder is empty</h3>
      <p class="text-sm max-w-[320px] mt-2 mb-6">
        No financial sheet registered here. Record stocks, cash, or crypto tokens using the button below.
      </p>
      <button @click="emit('openAddModal')" class="btn btn-sm btn-primary">
        Add Strategy Holding
      </button>
    </div>

    <div v-else class="table-wrapper">
      <table class="premium-table">
        <thead>
          <tr>
            <th>Asset Name</th>
            <th>Class</th>
            <th>Ticker / ISIN</th>
            <th>Quantity</th>
            <th>Price</th>
            <th>Market Value</th>
            <th>Invested</th>
            <th>P&amp;L</th>
            <th v-if="portfolioId === 'unassigned'">Assign to Strategy</th>
            <th class="w-[50px]"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="pos in positions"
            :key="pos.position_id"
            class="cursor-pointer hover:bg-bg-tertiary/60 transition-colors"
            :title="'View transactions of ' + (pos.name || pos.ticker || 'this position')"
            @click="emit('selectPosition', pos)"
          >
            <td class="font-semibold">
              {{ pos.name || pos.ticker || '—' }}
              <span
                v-if="pos.position_ids.length > 1"
                class="badge ml-1.5 !text-[9px] bg-bg-tertiary text-text-tertiary"
                :title="pos.position_ids.length + ' positions aggregated into this asset'"
              >
                ×{{ pos.position_ids.length }}
              </span>
            </td>
            <td>
              <span class="badge" :class="'badge-' + pos.asset_type">
                {{ assetTypeLabel(pos.asset_type) }}
              </span>
            </td>
            <td>
              <code class="text-xs bg-bg-tertiary px-1.5 py-0.5 rounded">
                {{ pos.ticker || '—' }}
              </code>
              <span v-if="pos.isin" class="text-text-secondary text-[10px] ml-2">
                {{ pos.isin }}
              </span>
            </td>
            <td class="font-mono text-sm">{{ formatQuantity(pos.quantity) }}</td>
            <td class="font-mono">
              <span>{{ pos.price !== null ? formatCurrency(pos.price, pos.currency) : '—' }}</span>
              <span
                v-if="pos.price_status !== 'ok' && pos.price_status !== 'fixed'"
                class="badge ml-1.5 !text-[9px] uppercase"
                :class="pos.price_status === 'stale' ? 'bg-color-warning-light text-color-warning' : 'bg-bg-tertiary text-text-tertiary'"
                :title="PRICE_STATUS_HINTS[pos.price_status]"
              >
                {{ pos.price_status === 'stale' ? 'stale' : 'cost' }}
              </span>
              <span
                v-if="pos.fx_approximate"
                class="badge ml-1 !text-[9px] uppercase bg-bg-tertiary text-text-tertiary"
                title="Converted with a transaction-implied FX rate (approximate)"
              >
                fx≈
              </span>
            </td>
            <td class="font-semibold font-mono">{{ formatCurrency(pos.market_value) }}</td>
            <td class="font-mono text-text-secondary">{{ formatCurrency(pos.total_invested) }}</td>
            <td class="font-mono" :class="gainClass(pos.gain)">
              {{ Number(pos.gain) >= 0 ? '+' : '' }}{{ formatCurrency(pos.gain) }}
              <span v-if="pos.gain_pct !== null" class="text-[10px] opacity-80 ml-1">
                ({{ Number(pos.gain_pct) >= 0 ? '+' : '' }}{{ Number(pos.gain_pct).toFixed(1) }}%)
              </span>
            </td>
            <td v-if="portfolioId === 'unassigned'" @click.stop>
              <select
                @change="emit('movePosition', { position: pos, targetPortfolioId: Number(($event.target as HTMLSelectElement).value) })"
                class="bg-bg-tertiary border border-border-color rounded text-xs px-2 py-1 text-text-primary focus:outline-none focus:border-accent-color cursor-pointer max-w-[180px]"
              >
                <option value="" disabled selected>Select active strategy...</option>
                <option v-for="p in portfolios" :key="p.id" :value="p.id">
                  {{ p.name }}
                </option>
              </select>
            </td>
            <td @click.stop>
              <button @click="emit('deletePosition', pos)" class="btn-logout p-1" title="Remove Asset">
                <Trash2 class="w-3.5 h-3.5 text-text-tertiary" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped></style>
