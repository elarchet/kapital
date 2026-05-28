<script setup lang="ts">
const transformationType = defineModel<'none' | 'divisor' | 'multiplier'>('transformationType', { required: true });
const transformationValue = defineModel<number | null>('transformationValue', { required: true });
</script>

<template>
  <div class="options-container">
    <h5 class="options-title">Numeric Data Transformations</h5>
    <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 1rem; align-items: center;">
      <select v-model="transformationType" class="form-control">
        <option value="none">No transformation (Direct parse)</option>
        <option value="divisor">Divide value by...</option>
        <option value="multiplier">Multiply value by...</option>
      </select>
      <div v-if="transformationType !== 'none'" style="display: flex; align-items: center; gap: 0.5rem;">
        <input 
          type="number" 
          v-model.number="transformationValue" 
          class="form-control" 
          placeholder="e.g. 100" 
          min="0.00001" 
          required
        />
        <span style="font-size: 0.75rem; color: var(--text-secondary); white-space: nowrap;">
          (e.g., scale GBX to GBP)
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.options-container {
  margin-top: 1.25rem;
  background-color: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 1rem;
}

.options-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}
</style>
