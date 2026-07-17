<script setup lang="ts">
import CsvColumnChip from './CsvColumnChip.vue';
import { useChunkedRows } from './useChunkedRows';

const props = defineProps<{
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

// ~3.1rem per chip row (two text lines + padding + gap); rows cap at 22vh.
const chipRows = useChunkedRows(() => props.uiColumns, 3.1, 0.22);
</script>

<template>
  <div class="sticky top-0 z-10 -mx-1 px-1 pt-1 pb-2 bg-bg-secondary/95 backdrop-blur-sm border-b border-border-color">
    <div class="flex items-baseline justify-between mb-1.5">
      <span class="text-[0.7rem] font-bold uppercase tracking-wider text-text-secondary">CSV Columns</span>
      <span class="text-[0.65rem] text-text-tertiary">drag a column onto a field — or click it, then click a field</span>
    </div>
    <!-- Same layout rule as the type pills: chips pack back-to-back over at
         least 2 rows (more when the screen is tall enough) and overflow
         scrolls horizontally. -->
    <div class="flex flex-col items-start gap-1.5 overflow-x-auto overflow-y-hidden pb-0.5">
      <div v-for="(row, rowIdx) in chipRows" :key="rowIdx" class="flex items-start gap-1.5 w-max">
        <CsvColumnChip
          v-for="col in row"
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
  </div>
</template>
