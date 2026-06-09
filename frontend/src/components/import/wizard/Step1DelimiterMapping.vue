<script setup lang="ts">
import { computed } from 'vue';
import CustomDropdown from '../../CustomDropdown.vue';

const props = defineProps<{
  importFileHeaders: string[];
  uniqueOperationTypes: string[];
  importFields: any[];
  activeDbOpTypes: string[];
}>();

const delimiter = defineModel<string>('delimiter', { required: true });
const decimalSeparator = defineModel<string>('decimalSeparator', { required: true });
const operationTypeColumnIdx = defineModel<number | null>('operationTypeColumnIdx', { required: true });

const emit = defineEmits<{
  (e: 'column-change'): void;
  (e: 'next'): void;
}>();

const onColumnChange = () => {
  emit('column-change');
};

const goToStep2 = () => {
  emit('next');
};

const colIdxString = computed({
  get() {
    return operationTypeColumnIdx.value !== null ? String(operationTypeColumnIdx.value) : '';
  },
  set(val: string) {
    if (val === '') {
      operationTypeColumnIdx.value = null;
    } else {
      operationTypeColumnIdx.value = Number(val);
    }
    onColumnChange();
  }
});

const columnOptions = computed(() => {
  return props.importFileHeaders.map((h, idx) => ({
    value: String(idx),
    label: h
  }));
});

const delimiterOptions = [
  { value: ',', label: 'Comma (,)' },
  { value: ';', label: 'Semicolon (;)' },
  { value: '\t', label: 'Tab' }
];

const decimalSeparatorOptions = [
  { value: '.', label: 'Dot (.)' },
  { value: ',', label: 'Comma (,)' }
];
</script>

<template>
  <div>
    <div style="display: flex; flex-wrap: wrap; gap: 1rem; align-items: start; width: 100%; min-height: auto;">
      <!-- Main Content: Delimiter details and Transaction Type column select -->
      <div style="flex: 1 1 100%; min-width: 0; max-width: 500px; margin: 0 auto;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem;">
          <div style="margin-bottom: 0;">
            <CustomDropdown
              v-model="delimiter"
              :options="delimiterOptions"
              :searchable="false"
              placeholder="Choose delimiter..."
              label="Delimiter"
            />
          </div>
          <div style="margin-bottom: 0;">
            <CustomDropdown
              v-model="decimalSeparator"
              :options="decimalSeparatorOptions"
              :searchable="false"
              placeholder="Choose separator..."
              label="Decimal Separator"
            />
          </div>
        </div>

        <div style="margin-bottom: 0;">
          <CustomDropdown
            v-model="colIdxString"
            :options="columnOptions"
            :searchable="true"
            :showClear="true"
            clearLabel="-- Select Column --"
            placeholder="-- Select Column --"
            label="Transaction Type Column"
          />
          <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">
            Select the column in your CSV file that contains the transaction action type (e.g. "Buy", "Sell", "Dividend").
          </p>
        </div>
      </div>
    </div>

    <div style="margin-top: 0.75rem; display: flex; justify-content: flex-end;">
      <button 
        @click="goToStep2" 
        class="btn btn-primary" 
        :disabled="operationTypeColumnIdx === null"
      >
        Next: Configure Column Mappings &rarr;
      </button>
    </div>
  </div>
</template>
