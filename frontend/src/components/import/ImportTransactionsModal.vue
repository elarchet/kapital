<script setup lang="ts">
import { computed } from 'vue';
import { Layers, Loader, Trash2 } from '@lucide/vue';

// Composables & services
import { useImportWizard } from './useImportWizard';

// Subcomponents - nested subdirectories & globals
import ColumnMappingWizard from './wizard/ColumnMappingWizard.vue';
import Step1DelimiterMapping from './wizard/Step1DelimiterMapping.vue';
import Step2ColumnMapping from './wizard/Step2ColumnMapping.vue';
import ParsedPreviewTable from './wizard/ParsedPreviewTable.vue';

import OverwriteTemplateConfirmModal from './modals/OverwriteTemplateConfirmModal.vue';
import DeleteTemplateConfirmModal from './modals/DeleteTemplateConfirmModal.vue';
import DiscardChangesConfirmModal from './modals/DiscardChangesConfirmModal.vue';

import ImportSuccessSummary from './ImportSuccessSummary.vue';

import DynamicComponent from '../DynamicComponent.vue';

const props = defineProps<{
  portfolio: {
    id: number;
    name: string;
  };
  initialFile?: File | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'success'): void;
}>();

const {
  importFile,
  importFileHeaders,
  availableSchemas,
  selectedSchemaId,
  autodetectedSchemaId,
  isCustomMapping,
  isImporting,
  importError,
  importSuccessSummary,
  mappingTemplateName,
  saveMappingTemplate,
  importDelimiter,
  importDecimalSep,
  importFields,
  currentStep,
  operationTypeColumnIdx,
  operationTypeMappings,
  columnConfigMap,
  uiColumns,
  isWizardOpen,
  wizardCsvHeaderName,
  wizardExampleValue,
  wizardActiveOpType,
  wizardUniqueValues,
  wizardInitialMapping,
  showExitConfirm,
  showOverwriteConfirm,
  showDeleteConfirm,
  selectedSchema,
  selectedSchemaIdString,
  panelWidth,
  handleDuplicateColumn,
  handleDeleteColumn,
  handleUpdateOpTypeMapping,
  handleImport,
  handleDeleteTemplate,
  handleUpdateMapping,
  openWizard,
  handleWizardSave,
  handleWizardClear,
  requestClose,
  validationErrors,
  isValidCustomMapping,
  parsedPreviewRows,
  uniqueOperationTypes,
  activeDbOpTypes,
  exampleTransactions,
  liveValidationStats,
  prevExampleForType,
  nextExampleForType,
  hasConfirmedOverwrite,
  handleColumnChange,
} = useImportWizard(props, emit);

const isSchemaIncomplete = (schema: any) => {
  return schema ? !!schema.is_incomplete : false;
};

const schemaOptions = computed(() => {
  const options = availableSchemas.value.map(schema => {
    let rightLabel = schema.is_public ? 'Public' : 'Saved';
    if (isSchemaIncomplete(schema)) {
      rightLabel = 'Incomplete';
    }
    const rightBadgeClass = isSchemaIncomplete(schema)
      ? 'bg-amber-50 text-amber-600'
      : schema.is_public
        ? 'bg-blue-50 text-blue-600'
        : 'bg-emerald-50 text-emerald-600';

    return {
      value: String(schema.id),
      label: schema.name,
      rightLabel,
      rightBadgeClass
    };
  });

  options.push({
    value: '-1',
    label: 'Custom Mapping Template...',
    rightLabel: 'Custom',
    rightBadgeClass: 'bg-slate-100 text-slate-600'
  });

  return options;
});

const promptDeleteTemplate = () => {
  if (selectedSchema.value && !selectedSchema.value.is_public) {
    showDeleteConfirm.value = true;
  }
};

const onConfirmOverwrite = () => {
  showOverwriteConfirm.value = false;
  hasConfirmedOverwrite.value = true;
  handleImport();
};
</script>

<template>
  <DynamicComponent
    componentKey="right-panel-drawer"
    :show="true"
    :initialWidth="panelWidth"
    :minWidth="500"
    @close="requestClose"
  >
    <template #header>
      <h3 class="table-title !text-base !m-0">Import Transactions to "{{ portfolio.name }}"</h3>
    </template>

    <template #body>
        <div v-if="importError" class="login-error" style="margin-bottom: 0.5rem;">
          {{ importError }}
        </div>

        <!-- Success State -->
        <ImportSuccessSummary
          v-if="importSuccessSummary"
          :importSuccessSummary="importSuccessSummary"
          :mappingTemplateName="mappingTemplateName"
        />

        <template v-else-if="importFile">
          <div>
            <div v-if="!isCustomMapping || currentStep === 1" style="display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-tertiary); padding: 0.5rem 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); margin-bottom: 0.75rem;">
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <Layers style="width: 16px; height: 16px; color: var(--accent-color);" />
                <span style="font-weight: 600; font-size: 0.9rem;">{{ importFile.name }}</span>
                <span style="font-size: 0.75rem; color: var(--text-secondary);">({{ (importFile.size / 1024).toFixed(1) }} KB)</span>
              </div>
              <button @click="requestClose" style="background: none; border: none; color: var(--color-danger); cursor: pointer; font-size: 0.8rem; font-weight: 600;">Remove</button>
            </div>

            <div style="display: flex; flex-direction: column; gap: 0.75rem; width: 100%;">
              <div>
                <!-- Template select -->
                <div v-if="!isCustomMapping || currentStep === 1" class="form-group !mb-3" style="max-width: 450px;">
                  <label>Template Schema</label>
                  <div style="display: flex; gap: 0.5rem; align-items: stretch; margin-bottom: 0.25rem;">
                    <div style="flex: 1; min-width: 0;">
                      <DynamicComponent
                        componentKey="custom-dropdown"
                        v-model="selectedSchemaIdString"
                        :options="schemaOptions"
                        placeholder="Select schema template..."
                        label=""
                        style="margin-bottom: 0;"
                      />
                    </div>
                    <button
                      v-if="selectedSchema && !selectedSchema.is_public"
                      @click="promptDeleteTemplate"
                      type="button"
                      class="btn"
                      title="Delete this template"
                      style="padding: 0 0.75rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1px solid var(--border-color); background-color: var(--bg-secondary);"
                    >
                      <Trash2 style="width: 16px; height: 16px; color: var(--color-danger);" />
                    </button>
                  </div>
                  <p v-if="autodetectedSchemaId && selectedSchemaId === autodetectedSchemaId" style="font-size: 0.75rem; color: var(--color-success); margin-top: 0.25rem; font-weight: 500;">
                    ✓ Autodetected format matching this file
                  </p>
                </div>

                <!-- Custom mapping builder form -->
                <div v-if="isCustomMapping" style="border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 0.75rem; margin-top: 0.5rem; background-color: var(--bg-primary);">
                  
                  <!-- STEP 1: Delimiter & OpType mapping -->
                  <Step1DelimiterMapping
                    v-if="currentStep === 1"
                    v-model:delimiter="importDelimiter"
                    v-model:decimalSeparator="importDecimalSep"
                    v-model:operationTypeColumnIdx="operationTypeColumnIdx"
                    v-model:operationTypeMappings="operationTypeMappings"
                    :importFileHeaders="importFileHeaders"
                    :uniqueOperationTypes="uniqueOperationTypes"
                    :importFields="importFields"
                    :activeDbOpTypes="activeDbOpTypes"
                    @column-change="handleColumnChange"
                    @next="currentStep = 2"
                  />

                  <!-- STEP 2: Columns mapping & live stats verification -->
                  <Step2ColumnMapping
                    v-else-if="currentStep === 2"
                    v-model:saveMappingTemplate="saveMappingTemplate"
                    v-model:mappingTemplateName="mappingTemplateName"
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
                    :validationErrors="validationErrors"
                    @back="currentStep = 1"
                    @open-wizard="(payload: any) => openWizard(payload.colId, payload.opType, payload.targets, payload.rawAction)"
                    @prev-example="prevExampleForType"
                    @next-example="nextExampleForType"
                    @update-mapping="handleUpdateMapping"
                    @update-optype-mapping="handleUpdateOpTypeMapping"
                    @duplicate-column="handleDuplicateColumn"
                    @delete-column="handleDeleteColumn"
                  />
                </div>
              </div>

              <!-- REAL-TIME PARSED DATA PREVIEW (Only shown when not actively designing custom mappings) -->
              <ParsedPreviewTable
                v-if="!isCustomMapping"
                :parsedPreviewRows="parsedPreviewRows"
              />
            </div>
          </div>
        </template>
    </template>

    <template #footer>
        <button @click="requestClose" class="btn btn-sm">Cancel</button>
        <button 
          v-if="!importSuccessSummary && isCustomMapping && saveMappingTemplate && !isValidCustomMapping"
          @click="handleImport"
          class="btn btn-sm btn-primary"
          :disabled="isImporting || !mappingTemplateName.trim()"
          style="background-color: var(--color-warning); border-color: var(--color-warning); color: white;"
        >
          <Loader v-if="isImporting" style="animation: spin 1.5s linear infinite; width: 14px; height: 14px;" />
          <span v-if="isImporting">Saving template...</span>
          <span v-else>Save Incomplete Template</span>
        </button>
        <button 
          v-else-if="!importSuccessSummary"
          @click="handleImport" 
          class="btn btn-sm btn-primary" 
          :disabled="isImporting || !importFile || (isCustomMapping && !isValidCustomMapping) || (isCustomMapping && saveMappingTemplate && !mappingTemplateName.trim())"
        >
          <Loader v-if="isImporting" style="animation: spin 1.5s linear infinite; width: 14px; height: 14px;" />
          <span v-if="isImporting">Importing data...</span>
          <span v-else-if="isCustomMapping && saveMappingTemplate">Save Template & Import</span>
          <span v-else>Import Transactions</span>
        </button>
        <button 
          v-else
          @click="requestClose" 
          class="btn btn-sm btn-primary"
        >
          Done
        </button>
    </template>
  </DynamicComponent>

  <!-- Custom exit confirmation dialog -->
  <DiscardChangesConfirmModal 
    :show="showExitConfirm"
    title="Discard Import Session?"
    message="You have uploaded a file and configured mappings. Leaving now will discard this configuration."
    @cancel="showExitConfirm = false" 
    @confirm="emit('close')" 
  />

  <!-- Wizard mapping popup modal -->
  <ColumnMappingWizard
    :show="isWizardOpen"
    :csvHeaderName="wizardCsvHeaderName"
    :exampleValue="wizardExampleValue"
    :importFields="importFields"
    :activeOpType="wizardActiveOpType"
    :activeOpTypes="activeDbOpTypes"
    :delimiter="importDelimiter"
    :decimalSeparator="importDecimalSep"
    :uniqueCsvValues="wizardUniqueValues"
    :initialMapping="wizardInitialMapping"
    @close="isWizardOpen = false"
    @clear="handleWizardClear"
    @save="handleWizardSave"
  />

  <!-- Overwrite template warning popup -->
  <OverwriteTemplateConfirmModal
    :show="showOverwriteConfirm"
    :templateName="mappingTemplateName"
    @cancel="showOverwriteConfirm = false"
    @confirm="onConfirmOverwrite"
  />

  <!-- Delete template warning popup -->
  <DeleteTemplateConfirmModal
    :show="showDeleteConfirm"
    :templateName="selectedSchema ? selectedSchema.name : ''"
    @cancel="showDeleteConfirm = false"
    @confirm="handleDeleteTemplate"
  />
</template>
