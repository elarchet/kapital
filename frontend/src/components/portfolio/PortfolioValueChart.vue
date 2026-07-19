<script setup lang="ts">
import { computed } from 'vue';
import type { EChartsOption } from 'echarts';
import { LineChart as LineChartIcon, TrendingDown, TrendingUp } from '@lucide/vue';
import ThemedChart from '../charts/ThemedChart.vue';
import { useChartTokens } from '../../composables/useChartTokens';
import type { CurrentTotals, RangeKey, ValuationPoint } from '../../services/portfolioApi';

const props = defineProps<{
  series: ValuationPoint[];
  current: CurrentTotals | null;
  currency: string;
  loading: boolean;
  range: RangeKey;
}>();

const emit = defineEmits<{
  (e: 'update:range', range: RangeKey): void;
}>();

const RANGES: { key: RangeKey; label: string }[] = [
  { key: '1m', label: '1M' },
  { key: '3m', label: '3M' },
  { key: '6m', label: '6M' },
  { key: '1y', label: '1Y' },
  { key: 'ytd', label: 'YTD' },
  { key: 'all', label: 'ALL' },
];

const tokens = useChartTokens();

const formatCurrency = (val: number) =>
  new Intl.NumberFormat('fr-FR', { style: 'currency', currency: props.currency || 'EUR' }).format(val);

// Headline figures — the single KPI strip of the page.
const marketValue = computed(() => Number(props.current?.market_value ?? 0));
const netInvested = computed(() => Number(props.current?.net_invested ?? 0));
const gain = computed(() => Number(props.current?.gain ?? 0));
const gainPct = computed(() =>
  props.current?.gain_pct != null ? Number(props.current.gain_pct) : null
);
const isUp = computed(() => gain.value >= 0);

const option = computed<EChartsOption>(() => {
  const t = tokens.value;
  const dates = props.series.map(p => p.date);
  const marketValues = props.series.map(p => Number(p.market_value));
  const netInvestedSeries = props.series.map(p => Number(p.net_invested));

  return {
    grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: t.textTertiary, type: 'dashed' } },
      valueFormatter: (value: unknown) => formatCurrency(Number(value)),
    },
    legend: {
      top: 0,
      left: 0,
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 3,
      data: ['Market value', 'Net invested'],
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: t.border } },
      axisLabel: { color: t.textTertiary, hideOverlap: true },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLabel: {
        color: t.textTertiary,
        formatter: (value: number) => formatCurrency(value),
      },
      splitLine: { lineStyle: { color: t.border, opacity: 0.6 } },
    },
    series: [
      {
        name: 'Market value',
        type: 'line',
        data: marketValues,
        showSymbol: false,
        lineStyle: { width: 2, color: t.accent },
        itemStyle: { color: t.accent },
        areaStyle: { opacity: 0.08, color: t.accent },
        emphasis: { focus: 'series' },
      },
      {
        name: 'Net invested',
        type: 'line',
        step: 'end',
        data: netInvestedSeries,
        showSymbol: false,
        lineStyle: { width: 2, color: t.textTertiary, type: 'dashed' },
        itemStyle: { color: t.textTertiary },
        emphasis: { focus: 'series' },
      },
    ],
  };
});
</script>

<template>
  <section class="card flex flex-col gap-4 p-5">
    <!-- Headline strip: value, P&L pill and net invested in one line -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div class="min-w-0">
        <span class="text-[11px] font-bold uppercase tracking-wider text-text-tertiary">
          Portfolio value
        </span>
        <div class="flex items-center gap-3 flex-wrap mt-1">
          <span
            class="text-[2.1rem] leading-none font-bold tracking-tight text-text-primary"
            style="font-family: 'Outfit', sans-serif"
            data-testid="kpi-market-value"
          >
            {{ formatCurrency(marketValue) }}
          </span>
          <span
            class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold"
            :class="isUp ? 'bg-color-success-light text-color-success' : 'bg-color-danger-light text-color-danger'"
            :title="'Unrealized P&L vs net invested capital'"
          >
            <component :is="isUp ? TrendingUp : TrendingDown" class="w-3.5 h-3.5" />
            <span>{{ isUp ? '+' : '' }}{{ formatCurrency(gain) }}</span>
            <span v-if="gainPct !== null" class="opacity-80">({{ isUp ? '+' : '' }}{{ gainPct.toFixed(2) }}%)</span>
          </span>
        </div>
        <p class="text-xs text-text-tertiary mt-1.5">
          Net invested
          <span class="font-mono font-semibold text-text-secondary">{{ formatCurrency(netInvested) }}</span>
          — the gap to market value is your unrealized P&amp;L
        </p>
      </div>

      <div class="flex items-center gap-1 bg-bg-tertiary rounded-md p-0.5 border border-border-color" role="tablist" aria-label="Chart time range">
        <button
          v-for="r in RANGES"
          :key="r.key"
          role="tab"
          :aria-selected="props.range === r.key"
          class="px-2 py-1 text-[11px] font-semibold rounded transition-colors cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          :class="props.range === r.key
            ? 'bg-bg-secondary text-text-primary shadow-sm'
            : 'text-text-tertiary hover:text-text-secondary'"
          @click="emit('update:range', r.key)"
        >
          {{ r.label }}
        </button>
      </div>
    </div>

    <div v-if="!props.loading && !props.series.length" class="empty-state py-10 flex-1">
      <LineChartIcon class="empty-icon" />
      <h3>No valuation history yet</h3>
      <p class="text-sm max-w-[320px] mt-2">
        Import transactions into this portfolio to chart its value over time.
      </p>
    </div>
    <ThemedChart v-else :option="option" height="21rem" />
  </section>
</template>

<style scoped></style>
