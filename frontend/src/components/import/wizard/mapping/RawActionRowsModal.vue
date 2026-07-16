<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue';
import { X } from '@lucide/vue';

const props = defineProps<{
  show: boolean;
  rawAction: string;
  headers: string[];
  // Raw file rows whose transaction-type cell equals rawAction, with the name
  // of the file each row came from (multi-file batches merge rows client-side).
  rows: Array<{ cells: string[]; source: string }>;
  highlightColumnIdx: number | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const MAX_ROWS = 100;
const visibleRows = computed(() => props.rows.slice(0, MAX_ROWS));

// Only label rows with their file when the batch merged several files.
const showSource = computed(() => new Set(props.rows.map(r => r.source)).size > 1);

// Capture-phase window listener: Escape closes this modal without bubbling to
// the drawer's own Escape handler.
const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    e.stopPropagation();
    emit('close');
  }
};
watch(() => props.show, (open) => {
  if (open) window.addEventListener('keydown', onKeydown, true);
  else window.removeEventListener('keydown', onKeydown, true);
});
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown, true));
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 bg-slate-900/20 backdrop-blur-[2px] flex items-center justify-center z-[200]"
    @click.self="emit('close')"
  >
    <div data-testid="raw-rows-modal" class="bg-bg-primary border border-border-color rounded-md shadow-xl max-w-[94vw] max-h-[88vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center gap-2 py-2.5 px-4 border-b border-border-color">
        <span class="text-[0.72rem] font-mono bg-bg-tertiary border border-border-color rounded-sm py-0.5 px-1.5 truncate max-w-[40vw]" :title="rawAction">
          {{ rawAction }}
        </span>
        <span class="text-[0.78rem] text-text-secondary">
          {{ rows.length }} row{{ rows.length === 1 ? '' : 's' }} in your file{{ showSource ? 's' : '' }}
        </span>
        <button type="button" aria-label="Close" class="ml-auto p-1 rounded-sm text-text-secondary hover:text-text-primary" @click="emit('close')">
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Raw rows, exactly as they appear in the file -->
      <div class="flex-1 overflow-auto">
        <table class="border-collapse text-[0.7rem] font-mono whitespace-nowrap">
          <thead>
            <tr>
              <th v-if="showSource" class="sticky top-0 bg-bg-tertiary text-left font-bold py-1.5 px-2 border-b border-border-color text-text-secondary">
                File
              </th>
              <th
                v-for="(header, idx) in headers"
                :key="idx"
                class="sticky top-0 text-left font-bold py-1.5 px-2 border-b border-border-color"
                :class="idx === highlightColumnIdx ? 'bg-accent-light text-accent' : 'bg-bg-tertiary text-text-secondary'"
              >
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIdx) in visibleRows" :key="rowIdx" class="border-b border-border-color last:border-b-0">
              <td v-if="showSource" class="py-1 px-2 text-text-tertiary">{{ row.source }}</td>
              <td
                v-for="(_, colIdx) in headers"
                :key="colIdx"
                class="py-1 px-2"
                :class="colIdx === highlightColumnIdx ? 'bg-accent-light text-accent font-semibold' : ''"
              >
                {{ row.cells[colIdx] ?? '' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="rows.length > MAX_ROWS" class="py-1.5 px-4 border-t border-border-color text-[0.7rem] text-text-tertiary">
        Showing the first {{ MAX_ROWS }} of {{ rows.length }} rows.
      </div>
    </div>
  </div>
</template>
