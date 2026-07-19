<script setup lang="ts">
import { computed } from 'vue';
import { use } from 'echarts/core';
import { LineChart, PieChart } from 'echarts/charts';
import {
  DatasetComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import VChart from 'vue-echarts';
import type { EChartsOption } from 'echarts';
import { usePreferencesStore } from '../../store/preferences';
import { useChartTokens } from '../../composables/useChartTokens';

use([
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  DatasetComponent,
  CanvasRenderer,
]);

const props = withDefaults(
  defineProps<{
    option: EChartsOption;
    height?: string;
  }>(),
  { height: '20rem' }
);

const preferences = usePreferencesStore();
const tokens = useChartTokens();

// Token-derived base styling; the caller's option always wins field by field.
const mergedOption = computed<EChartsOption>(() => {
  const t = tokens.value;
  const base: EChartsOption = {
    backgroundColor: 'transparent',
    textStyle: { color: t.textSecondary, fontFamily: 'inherit' },
    tooltip: {
      backgroundColor: t.bgSecondary,
      borderColor: t.border,
      textStyle: { color: t.textPrimary, fontSize: 12 },
    },
    legend: { textStyle: { color: t.textSecondary } },
  };
  const option = props.option as Record<string, unknown>;
  const merged: Record<string, unknown> = { ...(base as Record<string, unknown>) };
  for (const [key, value] of Object.entries(option)) {
    const baseValue = merged[key];
    merged[key] =
      baseValue && typeof baseValue === 'object' && !Array.isArray(baseValue) &&
      value && typeof value === 'object' && !Array.isArray(value)
        ? { ...(baseValue as object), ...(value as object) }
        : value;
  }
  return merged as EChartsOption;
});
</script>

<template>
  <!-- Keyed on theme: a runtime theme swap re-mounts so every color re-reads. -->
  <VChart
    :key="preferences.theme"
    :option="mergedOption"
    :style="{ height: props.height, width: '100%' }"
    autoresize
  />
</template>

<style scoped></style>
