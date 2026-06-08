<script setup lang="ts">
import { computed } from 'vue';
import CustomDropdown from './CustomDropdown.vue';

const transformationType = defineModel<'none' | 'divisor' | 'multiplier'>('transformationType', { required: true });
const transformationValue = defineModel<number | null>('transformationValue', { required: true });

const options = [
  { value: 'none', label: 'No transformation (Direct parse)' },
  { value: 'divisor', label: 'Divide value by...' },
  { value: 'multiplier', label: 'Multiply value by...' }
];

const selectedType = computed({
  get() {
    return transformationType.value;
  },
  set(val: string) {
    transformationType.value = val as 'none' | 'divisor' | 'multiplier';
  }
});
</script>

<template>
  <div class="mt-5 bg-bg-primary border border-border-color rounded-sm p-4">
    <h5 class="text-[0.8rem] font-bold uppercase text-text-secondary tracking-wider mb-3">Numeric Data Transformations</h5>
    <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 1rem; align-items: center;">
      <CustomDropdown
        v-model="selectedType"
        :options="options"
        :searchable="false"
        placeholder="Select transformation..."
        :compact="true"
      />
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
