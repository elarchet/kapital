<script setup lang="ts">
import { CheckCircle } from '@lucide/vue';
import type { MappingVariant } from './useFieldSlots';

defineProps<{
  variants: MappingVariant[];
  selected: string[];
  // Per variant key: required-mapping progress + number of CSV rows it covers.
  stats: Record<string, { requiredMapped: number; requiredTotal: number; rowCount: number }>;
}>();

const emit = defineEmits<{
  // additive = Ctrl/Cmd/Shift held: toggle the pill in the selection instead
  // of replacing it, so shared columns can be mapped for several types at once.
  (e: 'select', payload: { key: string; additive: boolean }): void;
}>();

const onPillClick = (key: string, event: MouseEvent) => {
  emit('select', { key, additive: event.ctrlKey || event.metaKey || event.shiftKey });
};
</script>

<template>
  <div>
    <!-- Same layout rule as the CSV column tray: wraps with a 2-row minimum,
         scrolls beyond the cap. -->
    <div class="flex flex-wrap content-start items-start gap-1.5 min-h-[4rem] max-h-[18vh] overflow-y-auto overflow-x-hidden">
      <button
        v-for="variant in variants"
        :key="variant.key"
        type="button"
        :data-testid="`optype-pill-${variant.key}`"
        class="flex items-center gap-1.5 py-1 px-2.5 rounded-full border text-[0.75rem] font-semibold transition-colors shrink-0"
        :class="selected.includes(variant.key)
          ? 'border-accent bg-accent-light text-accent'
          : 'border-border-color bg-bg-primary text-text-secondary hover:border-accent/50'"
        @click="onPillClick(variant.key, $event)"
      >
        <span class="badge" :class="`badge-${variant.opType}`">{{ variant.opType }}</span>
        <span
          v-if="variant.rawAction"
          class="max-w-[140px] truncate text-[0.68rem] font-mono font-normal"
          :title="variant.rawAction"
        >{{ variant.rawAction }}</span>
        <span class="text-[0.65rem] text-text-tertiary font-normal">{{ stats?.[variant.key]?.rowCount ?? 0 }} rows</span>
        <CheckCircle
          v-if="stats?.[variant.key] && stats[variant.key].requiredMapped >= stats[variant.key].requiredTotal"
          class="w-3.5 h-3.5 text-success-color"
        />
        <span v-else class="text-[0.65rem] font-bold text-warning-color">
          {{ stats?.[variant.key]?.requiredMapped ?? 0 }}/{{ stats?.[variant.key]?.requiredTotal ?? 0 }} required
        </span>
      </button>
    </div>
    <p class="m-0 mt-1 text-[0.65rem] text-text-tertiary">
      Ctrl+click to select several types and map their shared columns in one go.
    </p>
  </div>
</template>
