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
  <div class="mt-5 bg-bg-primary border border-border-color rounded-sm p-4">
    <h5 class="text-[0.8rem] font-bold uppercase text-text-secondary tracking-wider mb-3">Map Unique CSV Values to Database Enums</h5>
    <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
      The file column contains raw labels. Map each unique label below to standard database option.
    </p>
    <div class="flex flex-col gap-2 max-h-[160px] overflow-y-auto border border-border-color rounded-sm p-2 bg-bg-secondary">
      <div v-for="val in uniqueCsvValues" :key="val" class="grid grid-cols-2 gap-3 items-center">
        <span class="text-[0.75rem] font-mono bg-bg-tertiary py-1 px-2 rounded-sm overflow-hidden text-ellipsis whitespace-nowrap border border-border-color" :title="val">{{ val || '—' }}</span>
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
