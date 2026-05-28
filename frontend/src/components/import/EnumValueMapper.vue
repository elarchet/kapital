<script setup lang="ts">
defineProps<{
  selectedField: {
    key: string;
    label: string;
    is_required: boolean;
    type: string;
    enum_values?: string[];
  };
  uniqueCsvValues: string[];
}>();

const enumMappings = defineModel<Record<string, string>>('enumMappings', { required: true });
</script>

<template>
  <div class="options-container">
    <h5 class="options-title">Map Unique CSV Values to Database Enums</h5>
    <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
      The file column contains raw labels. Map each unique label below to standard database option.
    </p>
    <div class="enum-scroll-list">
      <div v-for="val in uniqueCsvValues" :key="val" class="enum-row">
        <span class="enum-raw-badge" :title="val">{{ val || '—' }}</span>
        <select 
          v-model="enumMappings[val]" 
          class="form-control" 
          style="font-size: 0.75rem; padding: 0.25rem 0.5rem; height: auto;"
        >
          <option value="">-- Choose Option --</option>
          <option v-for="opt in selectedField.enum_values || []" :key="opt" :value="opt">
            {{ opt }}
          </option>
        </select>
      </div>
      <div v-if="uniqueCsvValues.length === 0" style="text-align: center; padding: 1rem; color: var(--text-tertiary); font-size: 0.8rem;">
        No unique values found in this column.
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

.enum-scroll-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 160px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0.5rem;
  background-color: var(--bg-secondary);
}

.enum-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  align-items: center;
}

.enum-raw-badge {
  font-size: 0.75rem;
  font-family: monospace;
  background-color: var(--bg-tertiary);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid var(--border-color);
}
</style>
