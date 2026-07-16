<script setup lang="ts">
import { computed } from 'vue';
import DynamicComponent from '../../DynamicComponent.vue';
import OperationTypeMappingPanel from './mapping/OperationTypeMappingPanel.vue';
import { INSTITUTION_OPTIONS } from '../../../services/import';

const props = defineProps<{
  importFileHeaders: string[];
  uniqueOperationTypes: string[];
  importFields: any[];
  activeDbOpTypes: string[];
  allRawRows: string[][];
  splitOpTypes: string[];
}>();

const delimiter = defineModel<string>('delimiter', { required: true });
const decimalSeparator = defineModel<string>('decimalSeparator', { required: true });
const operationTypeColumnIdx = defineModel<number | null>('operationTypeColumnIdx', { required: true });
const institutionKey = defineModel<string>('institutionKey', { required: true });
const operationTypeMappings = defineModel<Record<string, string>>('operationTypeMappings', { required: true });

const emit = defineEmits<{
  (e: 'column-change'): void;
  (e: 'update-optype-mapping', payload: { rawAction: string; dbOpType: string }): void;
  (e: 'toggle-split', payload: { opType: string; enabled: boolean }): void;
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

const rowCountsByRawAction = computed<Record<string, number>>(() => {
  const counts: Record<string, number> = {};
  if (operationTypeColumnIdx.value === null) return counts;
  props.allRawRows.forEach(row => {
    const raw = row[operationTypeColumnIdx.value!]?.trim();
    if (raw) counts[raw] = (counts[raw] || 0) + 1;
  });
  return counts;
});

// Step 2 maps columns per DB type: entering it with zero mapped actions
// would show an empty board, so require at least one mapping here.
const canGoNext = computed(() =>
  operationTypeColumnIdx.value !== null && props.activeDbOpTypes.length > 0
);

const delimiterOptions = [
  { value: ',', label: 'Comma (,)' },
  { value: ';', label: 'Semicolon (;)' },
  { value: '\t', label: 'Tab' }
];

const decimalSeparatorOptions = [
  { value: '.', label: 'Dot (.)' },
  { value: ',', label: 'Comma (,)' }
];

const institutionOptions = INSTITUTION_OPTIONS;
</script>

<template>
  <div>
    <div style="display: flex; flex-wrap: wrap; gap: 1rem; align-items: start; width: 100%; min-height: auto;">
      <!-- Main Content: Delimiter details and Transaction Type column select -->
      <div style="flex: 1 1 100%; min-width: 0; max-width: 500px; margin: 0 auto;">
        <div style="margin-bottom: 0.75rem;">
          <DynamicComponent
            componentKey="custom-dropdown"
            v-model="institutionKey"
            :options="institutionOptions"
            :searchable="false"
            placeholder="Choose institution..."
            label="Institution"
          />
          <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">
            The broker or bank this file comes from. All rows in the file are assumed to originate from this institution.
          </p>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem;">
          <div style="margin-bottom: 0;">
            <DynamicComponent
              componentKey="custom-dropdown"
              v-model="delimiter"
              :options="delimiterOptions"
              :searchable="false"
              placeholder="Choose delimiter..."
              label="Delimiter"
            />
          </div>
          <div style="margin-bottom: 0;">
            <DynamicComponent
              componentKey="custom-dropdown"
              v-model="decimalSeparator"
              :options="decimalSeparatorOptions"
              :searchable="false"
              placeholder="Choose separator..."
              label="Decimal Separator"
            />
          </div>
        </div>

        <div style="margin-bottom: 0;">
          <DynamicComponent
            componentKey="custom-dropdown"
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

        <!-- Raw action -> DB type mapping -->
        <div v-if="operationTypeColumnIdx !== null" style="margin-top: 0.75rem;">
          <OperationTypeMappingPanel
            :uniqueOperationTypes="uniqueOperationTypes"
            :operationTypeMappings="operationTypeMappings"
            :importFields="importFields"
            :rowCountsByRawAction="rowCountsByRawAction"
            :splitOpTypes="splitOpTypes"
            @update-optype-mapping="(payload) => emit('update-optype-mapping', payload)"
            @toggle-split="(payload) => emit('toggle-split', payload)"
          />
          <p v-if="!activeDbOpTypes.length" class="text-[0.75rem] text-warning-color mt-1 mb-0">
            Map at least one of your file's actions to a transaction type to continue.
          </p>
        </div>
      </div>
    </div>

    <div style="margin-top: 0.75rem; display: flex; justify-content: flex-end;">
      <button
        @click="goToStep2"
        class="btn btn-primary"
        :disabled="!canGoNext"
      >
        Next: Configure Column Mappings &rarr;
      </button>
    </div>
  </div>
</template>
