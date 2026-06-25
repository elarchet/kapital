<script setup lang="ts">
import { DollarSign, TrendingUp, Layers } from '@lucide/vue';

const props = defineProps<{
  value: number;
  positionsCount: number;
  isConsolidated: boolean;
  yieldMultiplier: number;
}>();

const formatCurrency = (val: number, cur: string = 'EUR') => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: cur }).format(val);
};
</script>

<template>
  <section class="metrics-grid !p-0">
    <!-- Card 1: Worth / Valuation -->
    <div class="card kpi-card">
      <div class="kpi-header">
        <span>{{ isConsolidated ? 'CONSOLIDATED NET WORTH' : 'PORTFOLIO VALUATION' }}</span>
        <DollarSign class="w-4 h-4 text-text-tertiary" />
      </div>
      <div class="kpi-value">{{ formatCurrency(value) }}</div>
      <div class="kpi-trend up">
        <TrendingUp class="w-3.5 h-3.5" />
        <span>+{{ isConsolidated ? '3.24%' : '4.12%' }} YTD</span>
      </div>
    </div>

    <!-- Card 2: Enrolled Assets -->
    <div class="card kpi-card">
      <div class="kpi-header">
        <span>{{ isConsolidated ? 'ACTIVE ASSETS' : 'ASSETS ENROLLED' }}</span>
        <Layers class="w-4 h-4 text-text-tertiary" />
      </div>
      <div class="kpi-value">{{ positionsCount }}</div>
      <p class="text-xs text-text-secondary mt-3">
        {{ isConsolidated 
          ? `Distributed across strategy folders`
          : 'Distinct holdings registered in this folder' 
        }}
      </p>
    </div>

    <!-- Card 3: Unrealized Gains / Yield -->
    <div class="card kpi-card">
      <div class="kpi-header">
        <span>{{ isConsolidated ? 'UNREALIZED GAINS' : 'PORTFOLIO YIELD (EST.)' }}</span>
        <TrendingUp class="w-4 h-4 text-text-tertiary" />
      </div>
      <div class="kpi-value text-color-success">
        +{{ formatCurrency(value * yieldMultiplier) }}
      </div>
      <div class="kpi-trend up bg-color-success-light text-color-success">
        <span>{{ isConsolidated ? 'Outperforming benchmarks' : 'Exceeding target allocations' }}</span>
      </div>
    </div>
  </section>
</template>
