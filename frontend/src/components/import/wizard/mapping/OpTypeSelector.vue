<script setup lang="ts">
import { CheckCircle } from '@lucide/vue';

// One pill per mapping variant: merged types get one pill (key = opType);
// split types get one pill per raw file action (key = the raw action string).
export interface MappingVariant {
  opType: string;
  key: string;
  rawAction?: string;
}

defineProps<{
  variants: MappingVariant[];
  selected: string;
  // Per variant key: required-mapping progress + number of CSV rows it covers.
  stats: Record<string, { requiredMapped: number; requiredTotal: number; rowCount: number }>;
}>();

const emit = defineEmits<{
  (e: 'select', key: string): void;
}>();
</script>

<template>
  <div class="flex flex-wrap gap-1.5">
    <button
      v-for="variant in variants"
      :key="variant.key"
      type="button"
      :data-testid="`optype-pill-${variant.key}`"
      class="flex items-center gap-1.5 py-1 px-2.5 rounded-full border text-[0.75rem] font-semibold transition-colors"
      :class="selected === variant.key
        ? 'border-accent bg-accent-light text-accent'
        : 'border-border-color bg-bg-primary text-text-secondary hover:border-accent/50'"
      @click="emit('select', variant.key)"
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
</template>
