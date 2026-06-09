<script setup lang="ts">
import { computed } from 'vue';
import CustomDropdown from '../../CustomDropdown.vue';

const dateFormat = defineModel<string>('dateFormat', { required: true });

const dropdownOptions = [
  { value: 'auto', label: 'ISO 8601 / Auto-detect', rightLabel: 'Auto', rightBadgeClass: 'bg-slate-100 text-slate-600' },
  { value: '%Y-%m-%d %H:%M:%S', label: 'YYYY-MM-DD HH:mm:ss', rightLabel: '2026-06-01 15:30:00', rightBadgeClass: 'bg-blue-50 text-blue-600' },
  { value: '%d/%m/%Y %H:%M:%S', label: 'DD/MM/YYYY HH:mm:ss', rightLabel: '01/06/2026 15:30:00', rightBadgeClass: 'bg-blue-50 text-blue-600' },
  { value: '%m/%d/%Y %H:%M:%S', label: 'MM/DD/YYYY HH:mm:ss', rightLabel: '06/01/2026 15:30:00', rightBadgeClass: 'bg-blue-50 text-blue-600' },
  { value: '%Y-%m-%d', label: 'YYYY-MM-DD', rightLabel: '2026-06-01', rightBadgeClass: 'bg-emerald-50 text-emerald-600' },
  { value: '%d/%m/%Y', label: 'DD/MM/YYYY', rightLabel: '01/06/2026', rightBadgeClass: 'bg-emerald-50 text-emerald-600' },
  { value: '%m/%d/%Y', label: 'MM/DD/YYYY', rightLabel: '06/01/2026', rightBadgeClass: 'bg-emerald-50 text-emerald-600' },
  { value: '%d.%m.%Y %H:%M:%S', label: 'DD.MM.YYYY HH:mm:ss', rightLabel: '01.06.2026 15:30:00', rightBadgeClass: 'bg-blue-50 text-blue-600' },
  { value: '%d.%m.%Y', label: 'DD.MM.YYYY', rightLabel: '01.06.2026', rightBadgeClass: 'bg-emerald-50 text-emerald-600' },
  { value: 'custom', label: 'Custom Python format...', rightLabel: 'Custom', rightBadgeClass: 'bg-amber-50 text-amber-600' }
];

const selectedOption = computed({
  get() {
    const isCommon = dropdownOptions.some(o => o.value === dateFormat.value && o.value !== 'custom');
    return isCommon ? dateFormat.value : 'custom';
  },
  set(val: string) {
    if (val !== 'custom') {
      dateFormat.value = val;
    } else {
      dateFormat.value = ''; // Let user define the custom format
    }
  }
});
</script>

<template>
  <div class="mt-5 bg-bg-primary border border-border-color rounded-sm p-4">
    <h5 class="text-[0.8rem] font-bold uppercase text-text-secondary tracking-wider mb-3">Date Parser Configuration</h5>
    <div style="display: flex; flex-direction: column; gap: 1rem;">
      <CustomDropdown
        v-model="selectedOption"
        :options="dropdownOptions"
        :searchable="false"
        placeholder="Select date format..."
        label="Date Format Template"
      />

      <div v-if="selectedOption === 'custom'" class="form-group mb-0 animate-[fadeIn_0.15s_ease-out]">
        <label class="text-[0.75rem] font-semibold text-text-secondary mb-1 block">Set Custom Format</label>
        <input
          type="text"
          v-model="dateFormat"
          class="form-control"
          placeholder="e.g. %Y-%m-%d %H:%M:%S"
          required
        />
        <span style="font-size: 0.65rem; color: var(--text-secondary); margin-top: 0.25rem; display: block;">
          Enter format using Python strptime codes (e.g. %Y=year, %m=month, %d=day, %H=hour, %M=minute, %S=second)
        </span>
      </div>
    </div>
  </div>
</template>
