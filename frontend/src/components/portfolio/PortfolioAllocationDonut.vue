<script setup lang="ts">
import { computed } from 'vue';
import type { EChartsOption } from 'echarts';
import { PieChart as PieChartIcon } from '@lucide/vue';
import ThemedChart from '../charts/ThemedChart.vue';
import { useChartTokens } from '../../composables/useChartTokens';
import { assetTypeColor, assetTypeLabel } from '../../config/assetTypes';
import type { AssetTypeSlice } from '../../services/portfolioApi';

const props = defineProps<{
  allocation: AssetTypeSlice[];
  currency: string;
}>();

const tokens = useChartTokens();

const formatCurrency = (val: number) =>
  new Intl.NumberFormat('fr-FR', { style: 'currency', currency: props.currency || 'EUR' }).format(val);

// Negative buckets (e.g. overdrawn cash) can't be drawn as slices; the
// backend already excludes them from percentages — list them below instead.
const positiveSlices = computed(() => props.allocation.filter(s => Number(s.market_value) > 0));
const negativeSlices = computed(() => props.allocation.filter(s => Number(s.market_value) < 0));

const option = computed<EChartsOption>(() => {
  const t = tokens.value;
  return {
    tooltip: {
      trigger: 'item',
      valueFormatter: (value: unknown) => formatCurrency(Number(value)),
    },
    series: [
      {
        type: 'pie',
        radius: ['58%', '82%'],
        center: ['50%', '50%'],
        itemStyle: { borderColor: t.bgSecondary, borderWidth: 2, borderRadius: 4 },
        label: { show: false },
        emphasis: { scaleSize: 4 },
        data: positiveSlices.value.map(slice => ({
          name: assetTypeLabel(slice.asset_type),
          value: Number(slice.market_value),
          itemStyle: { color: assetTypeColor(slice.asset_type) },
        })),
      },
    ],
  };
});
</script>

<template>
  <section class="card flex flex-col gap-3 p-5">
    <div>
      <h3 class="text-sm font-bold text-text-primary tracking-tight">Allocation by Asset Type</h3>
      <p class="text-xs text-text-tertiary mt-0.5">Current market value share per asset class</p>
    </div>

    <div v-if="!positiveSlices.length" class="empty-state py-10">
      <PieChartIcon class="empty-icon" />
      <h3>Nothing to allocate yet</h3>
      <p class="text-sm max-w-[280px] mt-2">Holdings will break down here by asset class.</p>
    </div>

    <template v-else>
      <ThemedChart :option="option" height="13rem" />

      <ul class="flex flex-col gap-1.5" aria-label="Allocation legend">
        <li
          v-for="slice in positiveSlices"
          :key="slice.asset_type"
          class="flex items-center gap-2 text-xs"
        >
          <span
            class="w-2.5 h-2.5 rounded-sm shrink-0"
            :style="{ backgroundColor: assetTypeColor(slice.asset_type) }"
            aria-hidden="true"
          ></span>
          <span class="text-text-secondary font-medium flex-1">{{ assetTypeLabel(slice.asset_type) }}</span>
          <span class="font-mono text-text-primary">{{ formatCurrency(Number(slice.market_value)) }}</span>
          <span class="font-mono text-text-tertiary w-12 text-right">{{ Number(slice.percentage).toFixed(1) }}%</span>
        </li>
        <li
          v-for="slice in negativeSlices"
          :key="slice.asset_type"
          class="flex items-center gap-2 text-xs opacity-70"
          title="Negative balance — excluded from the chart"
        >
          <span
            class="w-2.5 h-2.5 rounded-sm shrink-0 border border-border-color"
            :style="{ backgroundColor: assetTypeColor(slice.asset_type) }"
            aria-hidden="true"
          ></span>
          <span class="text-text-secondary font-medium flex-1">{{ assetTypeLabel(slice.asset_type) }}</span>
          <span class="font-mono text-color-danger">{{ formatCurrency(Number(slice.market_value)) }}</span>
          <span class="font-mono text-text-tertiary w-12 text-right">—</span>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped></style>
