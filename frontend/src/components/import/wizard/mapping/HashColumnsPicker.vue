<script setup lang="ts">
import { computed } from 'vue';
import { AlertTriangle } from '@lucide/vue';

const props = defineProps<{
  headers: string[];
}>();

// Selected subset of CSV columns fed into the generated transaction ID and
// dedup key. Empty selection = all columns (backend default).
const hashColumns = defineModel<string[]>('hashColumns', { required: true });

const isChecked = (header: string) =>
  hashColumns.value.length === 0 || hashColumns.value.includes(header);

const toggle = (header: string) => {
  if (hashColumns.value.length === 0) {
    // Currently "all": unchecking one materializes the explicit subset.
    hashColumns.value = props.headers.filter(h => h !== header);
  } else if (hashColumns.value.includes(header)) {
    hashColumns.value = hashColumns.value.filter(h => h !== header);
  } else {
    const next = [...hashColumns.value, header];
    // Selecting every column collapses back to the "all columns" default.
    hashColumns.value = next.length === props.headers.length ? [] : next;
  }
};

const selectedCount = computed(() =>
  hashColumns.value.length === 0 ? props.headers.length : hashColumns.value.length
);
const tooFew = computed(() => selectedCount.value < 2);
</script>

<template>
  <div class="flex flex-col gap-2">
    <p class="text-[0.72rem] text-text-secondary m-0">
      Columns included in the generated ID ({{ selectedCount }}/{{ headers.length }}).
      Rows identical on these columns are treated as duplicates.
    </p>
    <div class="grid grid-cols-2 gap-x-3 gap-y-1 max-h-[140px] overflow-y-auto border border-border-color rounded-sm p-2 bg-bg-secondary">
      <label
        v-for="header in headers"
        :key="header"
        class="flex items-center gap-1.5 text-[0.72rem] font-mono truncate cursor-pointer"
        :title="header"
      >
        <input
          type="checkbox"
          class="w-3.5 h-3.5 shrink-0 cursor-pointer"
          :checked="isChecked(header)"
          @change="toggle(header)"
        />
        <span class="truncate">{{ header }}</span>
      </label>
    </div>
    <div v-if="tooFew" class="flex items-center gap-1.5 text-[0.72rem] text-danger-color font-semibold">
      <AlertTriangle class="w-3.5 h-3.5 shrink-0" /> Select at least 2 columns — fewer makes rows collide as duplicates.
    </div>
    <div v-else class="flex items-center gap-1.5 text-[0.7rem] text-warning-color">
      <AlertTriangle class="w-3 h-3 shrink-0" /> Changing this changes dedup keys: already-imported rows may be re-imported.
    </div>
  </div>
</template>
