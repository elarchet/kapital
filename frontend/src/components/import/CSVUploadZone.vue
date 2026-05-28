<script setup lang="ts">
import { Plus } from '@lucide/vue';

const emit = defineEmits<{
  (e: 'file-selected', file: File): void;
}>();

const handleFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    emit('file-selected', target.files[0]);
  }
};
</script>

<template>
  <div class="form-group">
    <label>Select CSV File</label>
    <label class="border-2 border-dashed border-border-color rounded-md py-10 px-6 text-center cursor-pointer transition-all duration-150 ease-in-out bg-bg-primary flex flex-col items-center justify-center hover:border-accent hover:bg-accent-light">
      <Plus style="width: 24px; height: 24px; color: var(--text-tertiary); margin: 0 auto 0.5rem auto;" />
      <p style="font-weight: 500; font-size: 0.9rem;">Click to upload or drag & drop CSV file</p>
      <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">Standard CSV files supported</p>
      <input type="file" accept=".csv" @change="handleFileChange" style="display: none;" />
    </label>
  </div>
</template>
