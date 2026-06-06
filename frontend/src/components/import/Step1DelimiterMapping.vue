<script setup lang="ts">
import { computed } from 'vue';
import CustomDropdown from './CustomDropdown.vue';

const props = defineProps<{
  importFileHeaders: string[];
  uniqueOperationTypes: string[];
  importFields: any[];
  activeDbOpTypes: string[];
}>();

const delimiter = defineModel<string>('delimiter', { required: true });
const decimalSeparator = defineModel<string>('decimalSeparator', { required: true });
const operationTypeColumnIdx = defineModel<number | null>('operationTypeColumnIdx', { required: true });
const operationTypeMappings = defineModel<Record<string, string>>('operationTypeMappings', { required: true });

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

const dbOpOptions = computed(() => {
  const enumVals = props.importFields.find(f => f.key === 'operation_type')?.enum_values || [];
  return enumVals.map((opt: string) => ({
    value: opt,
    label: opt
  }));
});
</script>

<template>
  <div>
    <div style="display: flex; flex-wrap: wrap; gap: 1rem; align-items: start; width: 100%; min-height: auto;">
      <!-- Left Column: Delimiter details and Transaction Type column select -->
      <div style="flex: 1 1 350px; min-width: 0;">
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

      <!-- Right Column: Map File Actions to Database Transaction Types -->
      <div style="flex: 1 1 350px; min-width: 0;">
        <div v-if="operationTypeColumnIdx !== null && uniqueOperationTypes.length > 0">
          <h5 style="font-size: 0.8rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.35rem;">
            Map File Actions to Database Transaction Types
          </h5>
          <div style="display: flex; flex-direction: column; gap: 0.35rem; border: 1px solid var(--border-color); padding: 0.5rem; border-radius: var(--radius-sm); background-color: var(--bg-secondary); max-height: 240px; overflow-y: auto;">
            <div v-for="val in uniqueOperationTypes" :key="val" style="display: grid; grid-template-columns: 1fr 1.2fr; gap: 0.5rem; align-items: center;">
              <span style="font-size: 0.75rem; font-family: monospace; background-color: var(--bg-primary); padding: 0.2rem 0.4rem; border-radius: var(--radius-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="val">
                {{ val }}
              </span>
              <div style="margin-bottom: 0;">
                <CustomDropdown
                  v-model="operationTypeMappings[val]"
                  :options="dbOpOptions"
                  :searchable="false"
                  :showClear="true"
                  :compact="true"
                  clearLabel="-- Choose DB Operation --"
                  placeholder="-- Choose DB Operation --"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div style="margin-top: 0.75rem; display: flex; justify-content: flex-end;">
      <button 
        @click="goToStep2" 
        class="btn btn-primary" 
        :disabled="operationTypeColumnIdx === null || activeDbOpTypes.length === 0"
      >
        Next: Configure Column Mappings &rarr;
      </button>
    </div>
  </div>
</template>
