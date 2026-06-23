<script setup lang="ts">
import { computed } from 'vue';
import { Layers, Loader, Trash2, Pencil } from '@lucide/vue';

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

const startEditingSchema = () => {
  if (selectedSchema.value) {
    isCustomMapping.value = true;
    saveMappingTemplate.value = true;
    mappingTemplateName.value = selectedSchema.value.name;
    currentStep.value = 1;
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
        <div v-if="importError" class="login-error mb-2">
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
            <div v-if="!isCustomMapping || currentStep === 1" class="flex justify-between items-center bg-bg-tertiary py-2 px-3 rounded-sm border border-border-color mb-3">
              <div class="flex items-center gap-2">
                <Layers class="w-4 h-4 text-accent" />
                <span class="text-[0.9rem] font-semibold">{{ importFile.name }}</span>
                <span class="text-xs text-text-secondary">({{ (importFile.size / 1024).toFixed(1) }} KB)</span>
              </div>
              <button @click="requestClose" class="bg-transparent border-none text-danger-color cursor-pointer text-[0.8rem] font-semibold">Remove</button>
            </div>

            <div class="flex flex-col gap-3 w-full">
              <div>
                <!-- Template select -->
                <div v-if="!isCustomMapping || currentStep === 1" class="form-group !mb-3 max-w-[450px]">
                  <label>Template Schema</label>
                  <div class="flex gap-2 items-stretch mb-1">
                    <div class="flex-1 min-w-0">
                      <DynamicComponent
                        componentKey="custom-dropdown"
                        v-model="selectedSchemaIdString"
                        :options="schemaOptions"
                        placeholder="Select schema template..."
                        label=""
                        class="mb-0"
                      />
                    </div>
                    <button
                      v-if="selectedSchema && !selectedSchema.is_public"
                      @click="startEditingSchema"
                      type="button"
                      class="btn !py-0 !px-3 shrink-0 mr-1"
                      title="Edit this template"
                    >
                      <Pencil class="w-4 h-4 text-accent" />
                    </button>
                    <button
                      v-if="selectedSchema && !selectedSchema.is_public"
                      @click="promptDeleteTemplate"
                      type="button"
                      class="btn !py-0 !px-3 shrink-0"
                      title="Delete this template"
                    >
                      <Trash2 class="w-4 h-4 text-danger-color" />
                    </button>
                  </div>
                  <p v-if="autodetectedSchemaId && selectedSchemaId === autodetectedSchemaId" class="text-xs text-success-color mt-1 font-medium">
                    ✓ Autodetected format matching this file
                  </p>
                </div>

                <!-- Custom mapping builder form -->
                <div v-if="isCustomMapping" class="border border-border-color rounded-sm p-3 mt-2 bg-bg-primary">
                  
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
          class="btn btn-sm btn-primary !bg-warning-color !border-warning-color !text-white"
          :disabled="isImporting || !mappingTemplateName.trim()"
        >
          <Loader v-if="isImporting" class="w-3.5 h-3.5 animate-spin" />
          <span v-if="isImporting">Saving template...</span>
          <span v-else>Save Incomplete Template</span>
        </button>
        <button 
          v-else-if="!importSuccessSummary"
          @click="handleImport" 
          class="btn btn-sm btn-primary" 
          :disabled="isImporting || !importFile || (isCustomMapping && !isValidCustomMapping) || (isCustomMapping && saveMappingTemplate && !mappingTemplateName.trim())"
        >
          <Loader v-if="isImporting" class="w-3.5 h-3.5 animate-spin" />
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
