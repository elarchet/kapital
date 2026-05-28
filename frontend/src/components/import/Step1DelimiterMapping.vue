<script setup lang="ts">

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
</script>

<template>
  <div>
    <h4 style="font-size: 0.95rem; margin-bottom: 1.25rem; font-weight: 600;">Step 1: Identify Delimiters & Transaction Type Column</h4>
    
    <div style="display: flex; flex-wrap: wrap; gap: 2rem; align-items: start; width: 100%;">
      <!-- Left Column: Delimiter details and Transaction Type column select -->
      <div style="flex: 1 1 350px; min-width: 0;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
          <div class="form-group" style="margin-bottom: 0;">
            <label>Delimiter</label>
            <select v-model="delimiter" class="form-control">
              <option value=",">Comma (,)</option>
              <option value=";">Semicolon (;)</option>
              <option value="&#9;">Tab</option>
            </select>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label>Decimal Separator</label>
            <select v-model="decimalSeparator" class="form-control">
              <option value=".">Dot (.)</option>
              <option value=",">Comma (,)</option>
            </select>
          </div>
        </div>

        <div class="form-group" style="margin-bottom: 0;">
          <label>Transaction Type Column</label>
          <select v-model="operationTypeColumnIdx" class="form-control" @change="onColumnChange">
            <option :value="null">-- Select Column --</option>
            <option v-for="(h, idx) in importFileHeaders" :key="idx" :value="idx">{{ h }}</option>
          </select>
          <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">
            Select the column in your CSV file that contains the transaction action type (e.g. "Buy", "Sell", "Dividend").
          </p>
        </div>
      </div>

      <!-- Right Column: Map File Actions to Database Transaction Types -->
      <div style="flex: 1 1 350px; min-width: 0;">
        <div v-if="operationTypeColumnIdx !== null && uniqueOperationTypes.length > 0">
          <h5 style="font-size: 0.8rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.75rem;">
            Map File Actions to Database Transaction Types
          </h5>
          <div style="display: flex; flex-direction: column; gap: 0.75rem; border: 1px solid var(--border-color); padding: 1rem; border-radius: var(--radius-sm); background-color: var(--bg-secondary); max-height: 250px; overflow-y: auto;">
            <div v-for="val in uniqueOperationTypes" :key="val" style="display: grid; grid-template-columns: 1fr 1.2fr; gap: 1rem; align-items: center;">
              <span style="font-size: 0.75rem; font-family: monospace; background-color: var(--bg-primary); padding: 0.25rem 0.5rem; border-radius: var(--radius-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="val">
                {{ val }}
              </span>
              <select v-model="operationTypeMappings[val]" class="form-control" style="font-size: 0.75rem; padding: 0.25rem 0.5rem; height: auto;">
                <option value="">-- Choose DB Operation --</option>
                <option v-for="opt in importFields.find(f => f.key === 'operation_type')?.enum_values || []" :key="opt" :value="opt">
                  {{ opt }}
                </option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div style="margin-top: 1.5rem; display: flex; justify-content: flex-end;">
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
