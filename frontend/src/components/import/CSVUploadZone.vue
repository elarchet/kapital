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
    <label class="upload-zone">
      <Plus style="width: 24px; height: 24px; color: var(--text-tertiary); margin: 0 auto 0.5rem auto;" />
      <p style="font-weight: 500; font-size: 0.9rem;">Click to upload or drag & drop CSV file</p>
      <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">Standard CSV files supported</p>
      <input type="file" accept=".csv" @change="handleFileChange" style="display: none;" />
    </label>
  </div>
</template>

<style scoped>
.upload-zone {
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-md);
  padding: 2.5rem 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  background-color: var(--bg-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.upload-zone:hover {
  border-color: var(--accent-color);
  background-color: var(--accent-light);
}
</style>
