<script setup lang="ts">
import { Grid, Trash2 } from '@lucide/vue';
import type { Position, Portfolio } from '../../store';

const props = defineProps<{
  positions: Position[];
  portfolios: Portfolio[];
}>();

const emit = defineEmits<{
  (e: 'deletePosition', id: number): void;
  (e: 'openAddModal'): void;
}>();

const formatCurrency = (val: number, cur: string = 'EUR') => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: cur }).format(val);
};

const getPortfolioName = (id: number) => {
  const p = props.portfolios.find(item => item.id === id);
  if (p) return p.name;
  const isUnassigned = props.positions.some(pos => pos.portfolio_id === id);
  return isUnassigned ? 'Unassigned Holdings' : 'Unknown';
};
</script>

<template>
  <section class="table-container">
    <div class="table-header-block">
      <h3 class="table-title">Aggregated Positions</h3>
      <span class="text-xs font-semibold text-text-secondary bg-bg-tertiary px-2 py-1 rounded border border-border-color">
        {{ positions.length }} holdings
      </span>
    </div>

    <div v-if="!positions.length" class="empty-state">
      <Grid class="empty-icon" />
      <h3>No asset positions found</h3>
      <p class="text-sm max-w-[320px] mt-2 mb-6">
        Get started by creating a portfolio and adding asset sheets, cash deposits, or stock tokens.
      </p>
      <button 
        @click="emit('openAddModal')" 
        class="btn btn-sm btn-primary"
        :disabled="!portfolios.length"
      >
        Add First Position
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
            <th>Est. Unit Price</th>
            <th>Current Value</th>
            <th>Strategy Folder</th>
            <th class="w-[50px]"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pos in positions" :key="pos.id">
            <td class="font-semibold">{{ pos.name }}</td>
            <td>
              <span class="badge" :class="'badge-' + pos.asset_type">
                {{ pos.asset_type }}
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
            <td class="font-mono text-sm">{{ pos.quantity }}</td>
            <td class="font-mono">{{ formatCurrency(pos.estimated_price || 0, pos.currency) }}</td>
            <td class="font-semibold font-mono">
              {{ formatCurrency(pos.estimated_value || 0, pos.currency) }}
            </td>
            <td>
              <router-link 
                :to="'/portfolio/' + pos.portfolio_id" 
                class="text-accent-color no-underline font-medium"
              >
                {{ getPortfolioName(pos.portfolio_id) }}
              </router-link>
            </td>
            <td>
              <button @click="emit('deletePosition', pos.id)" class="btn-logout p-1" title="Remove Position">
                <Trash2 class="w-3.5 h-3.5 text-text-tertiary" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
