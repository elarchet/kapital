<script setup lang="ts">
import { Layers } from '@lucide/vue';

// Summary bar for the loaded batch; changing which files make up the batch
// happens in the tick-based file selector the parent opens on demand.
defineProps<{
  files: File[];
}>();

const emit = defineEmits<{
  (e: 'change-files'): void;
  (e: 'remove'): void;
}>();
</script>

<template>
  <div class="flex justify-between items-center gap-3 bg-bg-tertiary py-2 px-3 rounded-sm border border-border-color mb-3">
    <div class="flex items-center gap-x-2 gap-y-0.5 min-w-0 flex-wrap">
      <Layers class="w-4 h-4 text-accent shrink-0" />
      <span v-for="f in files" :key="f.name" class="flex items-baseline gap-1 min-w-0">
        <span class="text-[0.9rem] font-semibold truncate">{{ f.name }}</span>
        <span class="text-xs text-text-secondary">({{ (f.size / 1024).toFixed(1) }} KB)</span>
      </span>
      <span v-if="files.length > 1" class="text-xs text-text-secondary">
        — {{ files.length }} files imported as one batch; rows appearing in several files are only imported once
      </span>
    </div>
    <div class="flex items-center gap-3 shrink-0">
      <button
        @click="emit('change-files')"
        class="bg-transparent border-none text-accent cursor-pointer text-[0.8rem] font-semibold"
        title="Add more files to this batch or change which files are in it"
        data-testid="change-files-button"
      >
        Add / change files
      </button>
      <button @click="emit('remove')" class="bg-transparent border-none text-danger-color cursor-pointer text-[0.8rem] font-semibold">Remove</button>
    </div>
  </div>
</template>
