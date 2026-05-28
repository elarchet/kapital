<script setup lang="ts">
import { AlertTriangle } from '@lucide/vue';
import MappingExampleTable from './MappingExampleTable.vue';
import VerificationPanel from './VerificationPanel.vue';

defineProps<{
  importFileHeaders: string[];
  operationTypeColumnIdx: number | null;
  columnConfigMap: Record<number, { global: any; typeSpecific: Record<string, any> }>;
  activeDbOpTypes: string[];
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
  (e: 'open-wizard', payload: { colIdx: number; opType: string | null }): void;
  (e: 'prev-example', opType: string): void;
  (e: 'next-example', opType: string): void;
}>();
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
      <h4 style="font-size: 0.95rem; font-weight: 600; margin: 0;">Step 2: Configure Column Mappings</h4>
      <button @click="emit('back')" class="btn btn-sm">&larr; Back to Step 1</button>
    </div>

    <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 1.25rem;">
      Click on any cell in the table below to configure its database field mapping. You can configure mappings globally or specifically for each transaction type.
    </p>

    <MappingExampleTable
      :importFileHeaders="importFileHeaders"
      :operationTypeColumnIdx="operationTypeColumnIdx"
      :columnConfigMap="columnConfigMap"
      :activeDbOpTypes="activeDbOpTypes"
      :importFields="importFields"
      :exampleTransactions="exampleTransactions"
      :liveValidationStats="liveValidationStats"
      @open-wizard="(payload) => emit('open-wizard', payload)"
      @prev-example="(opType) => emit('prev-example', opType)"
      @next-example="(opType) => emit('next-example', opType)"
    />

    <!-- Verification Panel -->
    <VerificationPanel
      :activeDbOpTypes="activeDbOpTypes"
      :liveValidationStats="liveValidationStats"
    />

    <!-- Validation Warnings Banner -->
    <div v-if="validationErrors.length > 0" class="validation-alert" style="margin-bottom: 1.5rem; display: flex; gap: 0.75rem; background-color: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); padding: 1rem; border-radius: var(--radius-sm);">
      <AlertTriangle style="color: #ef4444; width: 20px; height: 20px; flex-shrink: 0; margin-top: 0.15rem;" />
      <div>
        <div style="font-weight: 600; font-size: 0.85rem; color: #ef4444; margin-bottom: 0.25rem;">Template Validation Errors</div>
        <ul style="margin: 0; padding-left: 1.25rem; font-size: 0.75rem; color: var(--text-secondary); display: flex; flex-direction: column; gap: 0.15rem;">
          <li v-for="err in validationErrors" :key="err">{{ err }}</li>
        </ul>
      </div>
    </div>

    <!-- Save template options -->
    <div style="border-top: 1px solid var(--border-color); padding-top: 1rem; display: flex; flex-direction: column; gap: 0.5rem;">
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
  </div>
</template>
