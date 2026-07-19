<script setup lang="ts">
import { computed } from 'vue';
import { Loader, Receipt, Scissors } from '@lucide/vue';
import DynamicComponent from '../DynamicComponent.vue';
import { assetTypeLabel } from '../../config/assetTypes';
import type { Allocation, PositionValuation, RawTransaction } from '../../services/portfolioApi';

const props = defineProps<{
  position: PositionValuation;
  transactions: RawTransaction[];
  allocationsByTransaction: Record<number, Allocation[]>;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'openSplit', transaction: RawTransaction): void;
}>();

const formatCurrency = (val: string | number | null, cur: string) => {
  if (val === null) return '—';
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: cur || 'EUR' }).format(Number(val));
};

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('fr-FR', { year: 'numeric', month: 'short', day: 'numeric' });

const operationLabel = (tx: RawTransaction) => {
  if (tx.operation_type === 'trade') return tx.trade_side === 'sell' ? 'Sell' : 'Buy';
  return tx.operation_type.replace(/_/g, ' ');
};

const operationClass = (tx: RawTransaction) => {
  if (tx.operation_type === 'trade') {
    return tx.trade_side === 'sell' ? 'bg-color-danger-light text-color-danger' : 'bg-color-success-light text-color-success';
  }
  return 'bg-bg-tertiary text-text-secondary';
};

// A transaction shows as "split" when it carries more than one allocation or
// a single non-default one (i.e. the user already touched it).
const isSplit = (tx: RawTransaction) => {
  const allocations = props.allocationsByTransaction[tx.id];
  if (!allocations) return false;
  return allocations.length > 1 || allocations.some(a => !a.is_default);
};

const sortedTransactions = computed(() =>
  [...props.transactions].sort(
    (a, b) => new Date(b.executed_at).getTime() - new Date(a.executed_at).getTime()
  )
);

const totalAmount = computed(() =>
  props.transactions.reduce((sum, tx) => sum + Number(tx.total_amount || 0), 0)
);
</script>

<template>
  <DynamicComponent
    componentKey="right-panel-drawer"
    :show="true"
    :minWidth="520"
    :initialWidth="760"
    @close="emit('close')"
  >
    <template #header>
      <div class="flex items-center gap-2.5 min-w-0">
        <Receipt class="w-4 h-4 text-text-tertiary shrink-0" />
        <h3 class="text-sm font-bold text-text-primary truncate">
          {{ position.name || position.ticker || 'Position' }}
        </h3>
        <span class="badge shrink-0" :class="'badge-' + position.asset_type">
          {{ assetTypeLabel(position.asset_type) }}
        </span>
        <code v-if="position.ticker" class="text-xs bg-bg-tertiary px-1.5 py-0.5 rounded shrink-0">
          {{ position.ticker }}
        </code>
      </div>
    </template>

    <template #body>
      <div v-if="loading" class="empty-state flex-1">
        <Loader class="animate-spin w-8 h-8 text-accent" />
        <p class="mt-3 text-sm font-medium">Loading transactions…</p>
      </div>

      <div v-else-if="!sortedTransactions.length" class="empty-state flex-1">
        <Receipt class="empty-icon" />
        <h3>No transactions</h3>
        <p class="text-sm max-w-[320px] mt-2">
          Nothing has been routed to this position yet. Transactions appear here after a CSV import.
        </p>
      </div>

      <div v-else class="table-wrapper">
        <table class="premium-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Quantity</th>
              <th>Unit Price</th>
              <th>Amount</th>
              <th>Allocation</th>
              <th class="w-[80px]"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tx in sortedTransactions" :key="tx.id">
              <td class="font-mono text-xs whitespace-nowrap">{{ formatDate(tx.executed_at) }}</td>
              <td>
                <span class="badge capitalize" :class="operationClass(tx)">{{ operationLabel(tx) }}</span>
              </td>
              <td class="font-mono text-sm">{{ tx.quantity !== null ? Number(tx.quantity) : '—' }}</td>
              <td class="font-mono text-sm">{{ formatCurrency(tx.unit_price, tx.currency) }}</td>
              <td class="font-semibold font-mono">{{ formatCurrency(tx.total_amount, tx.currency) }}</td>
              <td>
                <span
                  v-if="isSplit(tx)"
                  class="badge bg-accent-light text-accent !text-[10px]"
                  :title="(allocationsByTransaction[tx.id]?.length || 0) + ' allocation lines'"
                >
                  split ×{{ allocationsByTransaction[tx.id]?.length }}
                </span>
                <span v-else class="text-xs text-text-tertiary">full</span>
              </td>
              <td>
                <button
                  class="btn btn-sm bg-bg-tertiary border border-border-color text-text-secondary hover:text-text-primary flex items-center gap-1"
                  title="Split this transaction across portfolios"
                  @click="emit('openSplit', tx)"
                >
                  <Scissors class="w-3 h-3" />
                  <span>Split</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <template #footer>
      <div class="flex items-center justify-between w-full text-xs text-text-secondary">
        <span>{{ sortedTransactions.length }} transaction{{ sortedTransactions.length === 1 ? '' : 's' }}</span>
        <span class="font-mono font-semibold text-text-primary">
          Total {{ formatCurrency(totalAmount, position.currency) }}
        </span>
      </div>
    </template>
  </DynamicComponent>
</template>

<style scoped></style>
