<script setup lang="ts">
import { CheckCircle } from '@lucide/vue';

defineProps<{
  opTypes: string[];
  selected: string;
  // Per op type: required-mapping progress + number of CSV rows of that type.
  stats: Record<string, { requiredMapped: number; requiredTotal: number; rowCount: number }>;
}>();

const emit = defineEmits<{
  (e: 'select', opType: string): void;
}>();
</script>

<template>
  <div class="flex flex-wrap gap-1.5">
    <button
      v-for="opType in opTypes"
      :key="opType"
      type="button"
      :data-testid="`optype-pill-${opType}`"
      class="flex items-center gap-1.5 py-1 px-2.5 rounded-full border text-[0.75rem] font-semibold transition-colors"
      :class="selected === opType
        ? 'border-accent bg-accent-light text-accent'
        : 'border-border-color bg-bg-primary text-text-secondary hover:border-accent/50'"
      @click="emit('select', opType)"
    >
      <span class="badge" :class="`badge-${opType}`">{{ opType }}</span>
      <span class="text-[0.65rem] text-text-tertiary font-normal">{{ stats?.[opType]?.rowCount ?? 0 }} rows</span>
      <CheckCircle
        v-if="stats?.[opType] && stats[opType].requiredMapped >= stats[opType].requiredTotal"
        class="w-3.5 h-3.5 text-success-color"
      />
      <span v-else class="text-[0.65rem] font-bold text-warning-color">
        {{ stats?.[opType]?.requiredMapped ?? 0 }}/{{ stats?.[opType]?.requiredTotal ?? 0 }} required
      </span>
    </button>
  </div>
</template>
