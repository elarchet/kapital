<script setup lang="ts">
const props = withDefaults(defineProps<{
  allocations: { type: string; value: number; percentage: number; color: string }[];
  portfolioName?: string;
  title?: string;
  description?: string;
}>(), {
  title: 'Strategy Asset Allocation',
  description: 'Local distribution of asset weight'
});

const formatCurrency = (val: number, cur: string = 'EUR') => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: cur }).format(val);
};
</script>

<template>
  <section class="card" v-if="allocations.length > 0">
    <h3 class="table-title" style="font-size: 1rem; margin-bottom: 0.25rem;">{{ title }}</h3>
    <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 1rem;">
      {{ description }} <span v-if="portfolioName">inside {{ portfolioName }}</span>
    </p>

    <div class="allocation-bar-container">
      <div class="allocation-bar">
        <div 
          v-for="alloc in allocations" 
          :key="alloc.type"
          class="allocation-segment"
          :style="{ width: alloc.percentage + '%', backgroundColor: alloc.color }"
          :title="alloc.type.toUpperCase() + ': ' + alloc.percentage.toFixed(1) + '%'"
        ></div>
      </div>

      <div class="allocation-legend">
        <div v-for="alloc in allocations" :key="alloc.type" class="legend-item">
          <span class="legend-color" :style="{ backgroundColor: alloc.color }"></span>
          <span style="text-transform: capitalize; font-weight: 500;">
            {{ alloc.type }}: {{ alloc.percentage.toFixed(1) }}% ({{ formatCurrency(alloc.value) }})
          </span>
        </div>
      </div>
    </div>
  </section>
</template>
