<script setup lang="ts">
import { ref } from 'vue';
import MappingExampleTable from './MappingExampleTable.vue';
import SimulationVerificationModal from '../modals/SimulationVerificationModal.vue';

const props = defineProps<{
  importFileHeaders: string[];
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }>;
  operationTypeColumnIdx: number | null;
  columnConfigMap: Record<string, { global: any; typeSpecific: Record<string, any> }>;
  activeDbOpTypes: string[];
  uniqueOperationTypes: string[];
  operationTypeMappings: Record<string, string>;
  importFields: any[];
  exampleTransactions: any[];
  liveValidationStats: any;
  validationErrors: string[];
  saveMappingTemplate: boolean;
  mappingTemplateName: string;
}>();

const emit = defineEmits<{
  (e: 'update:saveMappingTemplate', val: boolean): void;
  (e: 'update:mappingTemplateName', val: string): void;
  (e: 'back'): void;
  (e: 'open-wizard', payload: { colId: string; opType: string | null; targets?: Array<{ colId: string; opType: string | null }> }): void;
  (e: 'prev-example', opType: string): void;
  (e: 'next-example', opType: string): void;
  (e: 'update-mapping', payload: { colId: string; opType: string | null; mapping: any }): void;
  (e: 'update-optype-mapping', payload: { rawAction: string; dbOpType: string }): void;
  (e: 'duplicate-column', colId: string): void;
  (e: 'delete-column', colId: string): void;
}>();

// Verification modal state
const showVerification = ref(false);
const selectedVerificationType = ref('');

const openVerificationModal = (dbOpType: string) => {
  selectedVerificationType.value = dbOpType;
  showVerification.value = true;
};
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 0.5rem;">
      <p style="font-size: 0.75rem; color: var(--text-secondary); margin: 0; flex: 1;">
        Click on any cell or column header to configure database field mappings for transaction types.
      </p>
      <button @click="emit('back')" class="btn btn-sm" style="flex-shrink: 0;">&larr; Back to Step 1</button>
    </div>

    <!-- Step 2 Mapping Table -->
    <MappingExampleTable
      :importFileHeaders="importFileHeaders"
      :uiColumns="uiColumns"
      :operationTypeColumnIdx="operationTypeColumnIdx"
      :columnConfigMap="columnConfigMap"
      :activeDbOpTypes="activeDbOpTypes"
      :uniqueOperationTypes="uniqueOperationTypes"
      :operationTypeMappings="operationTypeMappings"
      :importFields="importFields"
      :exampleTransactions="exampleTransactions"
      :liveValidationStats="liveValidationStats"
      @open-wizard="(payload: any) => emit('open-wizard', payload)"
      @prev-example="(opType: string) => emit('prev-example', opType)"
      @next-example="(opType: string) => emit('next-example', opType)"
      @update-mapping="(payload: any) => emit('update-mapping', payload)"
      @update-optype-mapping="(payload: any) => emit('update-optype-mapping', payload)"
      @duplicate-column="(colId: string) => emit('duplicate-column', colId)"
      @delete-column="(colId: string) => emit('delete-column', colId)"
      @show-verification="openVerificationModal"
    />

    <!-- Save template options -->
    <div style="border-top: 1px solid var(--border-color); padding-top: 0.5rem; margin-top: 0.5rem; display: flex; flex-direction: column; gap: 0.35rem;">
      <label style="display: flex; align-items: center; gap: 0.5rem; font-weight: 500; text-transform: none; font-size: 0.875rem;">
        <input 
          type="checkbox" 
          :checked="saveMappingTemplate" 
          @change="emit('update:saveMappingTemplate', ($event.target as HTMLInputElement).checked)" 
          style="width: 16px; height: 16px; cursor: pointer;" 
        />
        <span>Save this configuration mapping as a template</span>
      </label>
      <div v-if="saveMappingTemplate" class="form-group" style="margin-top: 0.5rem; margin-bottom: 0; max-width: 400px;">
        <label>Template Name</label>
        <input 
          :value="mappingTemplateName" 
          @input="emit('update:mappingTemplateName', ($event.target as HTMLInputElement).value)" 
          type="text" 
          class="form-control" 
          placeholder="e.g. My Custom Broker CSV" 
          required 
        />
      </div>
    </div>

    <!-- Simulation Verification Detail Modal Popup -->
    <SimulationVerificationModal
      :show="showVerification"
      :dbOpType="selectedVerificationType"
      :stats="liveValidationStats[selectedVerificationType]"
      @close="showVerification = false"
    />
  </div>
</template>
