<script setup lang="ts">
import { Grid, Trash2 } from '@lucide/vue';
import type { Position, Portfolio } from '../../store';

const props = defineProps<{
  positions: Position[];
  portfolioId: number | 'unassigned';
  portfolios: Portfolio[];
}>();

const emit = defineEmits<{
  (e: 'deletePosition', id: number): void;
  (e: 'movePosition', payload: { posId: number; targetPortfolioId: number }): void;
  (e: 'openAddModal'): void;
}>();

const formatCurrency = (val: number, cur: string = 'EUR') => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: cur }).format(val);
};
</script>

<template>
  <section class="table-container">
    <div class="table-header-block">
      <h3 class="table-title">Strategy Holdings</h3>
      <span class="text-xs font-semibold text-text-secondary bg-bg-tertiary px-2 py-1 rounded border border-border-color">
        {{ positions.length }} items
      </span>
    </div>

    <div v-if="!positions.length" class="empty-state">
      <Grid class="empty-icon" />
      <h3>This strategy folder is empty</h3>
      <p class="text-sm max-w-[320px] mt-2 mb-6">
        No financial sheet registered here. Record stock stocks, cash, or crypto tokens using the button below.
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
            <th>Est. Unit Price</th>
            <th>Current Value</th>
            <th v-if="portfolioId === 'unassigned'">Assign to Strategy</th>
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
            <td v-if="portfolioId === 'unassigned'">
              <select 
                @change="emit('movePosition', { posId: pos.id, targetPortfolioId: Number(($event.target as HTMLSelectElement).value) })"
                class="bg-bg-tertiary border border-border-color rounded text-xs px-2 py-1 text-text-primary focus:outline-none focus:border-accent-color cursor-pointer max-w-[180px]"
              >
                <option value="" disabled selected>Select active strategy...</option>
                <option v-for="p in portfolios" :key="p.id" :value="p.id">
                  {{ p.name }}
                </option>
              </select>
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
