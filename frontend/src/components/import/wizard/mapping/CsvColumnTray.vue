<script setup lang="ts">
import CsvColumnChip from './CsvColumnChip.vue';

defineProps<{
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string }>;
  exampleRow: string[];
  usedColIds: Set<string>;
  armedColId: string | null;
}>();

const emit = defineEmits<{
  (e: 'chip-dragstart', payload: { colId: string; event: DragEvent }): void;
  (e: 'chip-dragend'): void;
  (e: 'chip-arm', colId: string): void;
}>();
</script>

<template>
  <div class="sticky top-0 z-10 -mx-1 px-1 pt-1 pb-2 bg-bg-secondary/95 backdrop-blur-sm border-b border-border-color">
    <div class="flex items-baseline justify-between mb-1.5">
      <span class="text-[0.7rem] font-bold uppercase tracking-wider text-text-secondary">CSV Columns</span>
      <span class="text-[0.65rem] text-text-tertiary">drag a column onto a field — or click it, then click a field</span>
    </div>
    <!-- Wraps on tall screens (capped so field slots keep priority), single scrollable row on short screens -->
    <div
      class="flex flex-wrap content-start items-start gap-1.5 min-h-[6rem] max-h-[22vh] overflow-y-auto overflow-x-hidden [@media(max-height:700px)]:flex-nowrap [@media(max-height:700px)]:min-h-0 [@media(max-height:700px)]:overflow-x-auto [@media(max-height:700px)]:overflow-y-hidden pb-0.5"
    >
      <CsvColumnChip
        v-for="col in uiColumns"
        :key="col.id"
        :colId="col.id"
        :name="col.name"
        :exampleValue="exampleRow?.[col.colIdx]"
        :used="usedColIds.has(col.id)"
        :armed="armedColId === col.id"
        class="shrink-0"
        @dragstart="(e: DragEvent) => emit('chip-dragstart', { colId: col.id, event: e })"
        @dragend="emit('chip-dragend')"
        @arm="emit('chip-arm', col.id)"
      />
    </div>
  </div>
</template>
