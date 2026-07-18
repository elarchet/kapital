<script setup lang="ts">
import { computed, ref } from 'vue';
import { Loader, Trash2, Pencil } from '@lucide/vue';
import { api } from '../../services/api';
import type { MappingVariant } from './wizard/mapping/useFieldSlots';

// Composables & services
import { useImportWizard } from './useImportWizard';
import { useSwipeNavGuard } from './useSwipeNavGuard';

// Subcomponents - nested subdirectories & globals
import Step1DelimiterMapping from './wizard/Step1DelimiterMapping.vue';
import Step2ColumnMapping from './wizard/Step2ColumnMapping.vue';
import ParsedPreviewTable from './wizard/ParsedPreviewTable.vue';

import OverwriteTemplateConfirmModal from './modals/OverwriteTemplateConfirmModal.vue';
import DeleteTemplateConfirmModal from './modals/DeleteTemplateConfirmModal.vue';
import DiscardChangesConfirmModal from './modals/DiscardChangesConfirmModal.vue';

import ImportFileSelector, { type SelectedImportFile } from './ImportFileSelector.vue';
import ImportBatchFilesBar from './ImportBatchFilesBar.vue';

import DynamicComponent from '../DynamicComponent.vue';

const props = defineProps<{
  portfolio: {
    id: number;
    name: string;
  };
  initialFiles?: File[] | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'success'): void;
}>();

const {
  importFiles,
  importFileHeaders,
  availableSchemas,
  selectedSchemaId,
  autodetectedSchemaId,
  isCustomMapping,
  isImporting,
  importError,
  mappingTemplateName,
  saveMappingTemplate,
  importDelimiter,
  importDecimalSep,
  institutionKey,
  importFields,
  currentStep,
  operationTypeColumnIdx,
  operationTypeMappings,
  splitOpTypes,
  toggleSplitType,
  columnConfigMap,
  uiColumns,
  opTypeSettings,
  allRawRows,
  rawRowSources,
  showExitConfirm,
  showOverwriteConfirm,
  showDeleteConfirm,
  selectedSchema,
  selectedSchemaIdString,
  panelWidth,
  handleUpdateOpTypeMapping,
  handleImport,
  handleDeleteTemplate,
  requestClose,
  validationErrors,
  isValidCustomMapping,
  parsedPreviewRows,
  enrichedNames,
  uniqueOperationTypes,
  activeDbOpTypes,
  matchingRowsByType,
  matchingRowsByRawAction,
  liveValidationStats,
  hasConfirmedOverwrite,
  handleColumnChange,
  touchColumnConfig,
  updateOpTypeSettings,
  updateFeeTaxGroupCount,
  feeTaxGroupCounts,
  processFiles,
} = useImportWizard(props, emit);

// The tick-based file selector is the single entry point for composing the
// batch: it shows on open (nothing loaded yet) and again on "Add / change files".
const showFileSelection = ref(false);
const isLoadingSelection = ref(false);

const onConfirmSelection = async (selection: SelectedImportFile[]) => {
  isLoadingSelection.value = true;
  importError.value = '';
  try {
    // Session uploads carry their bytes; history entries are downloaded.
    const files: File[] = [];
    for (const sel of selection) {
      if (sel.localFile) {
        files.push(sel.localFile);
      } else if (sel.stored) {
        const blob = await api.downloadImportedFile(sel.stored.id);
        files.push(new File([blob], sel.filename, { type: sel.stored.content_type || 'text/csv' }));
      }
    }
    if (!files.length) return;
    // Everything in the selection was already stored (at upload time), so the
    // batch build never re-uploads. Growing the batch appends and preserves
    // the mapping work; shrinking or replacing it rebuilds from scratch.
    const currentNames = importFiles.value.map(f => f.name);
    const keptWholeBatch = currentNames.length > 0 && currentNames.every(n => files.some(f => f.name === n));
    if (keptWholeBatch) {
      await processFiles(files.filter(f => !currentNames.includes(f.name)), { append: true, alreadyStored: true });
    } else {
      await processFiles(files, { alreadyStored: true });
    }
    showFileSelection.value = false;
  } catch (err: any) {
    importError.value = err.message || 'Failed to load the selected files.';
  } finally {
    isLoadingSelection.value = false;
  }
};

// Variant(s) currently being mapped in Step 2, mirrored into the drawer header
// so they stay visible while the mapping board scrolls.
const mappingSelection = ref<MappingVariant[]>([]);

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

useSwipeNavGuard();
</script>

<template>
  <DynamicComponent
    componentKey="right-panel-drawer"
    :show="true"
    :initialWidth="panelWidth"
    :minWidth="500"
    :bodyClass="currentStep === 2 ? '!p-2 overscroll-x-none' : 'overscroll-x-none'"
    @close="requestClose"
  >
    <template #header>
      <div class="flex items-center gap-2 min-w-0">
        <h3 class="table-title !text-base !m-0 shrink-0">Import Transactions to "{{ portfolio.name }}"</h3>
        <!-- The otherwise-empty header space shows what is being mapped, so it
             stays visible while the Step 2 board scrolls. -->
        <template v-if="isCustomMapping && currentStep === 2 && mappingSelection.length">
          <span class="text-sm text-text-tertiary shrink-0">— mapping</span>
          <div class="flex items-center gap-1.5 min-w-0 overflow-x-auto">
            <span
              v-for="variant in mappingSelection"
              :key="variant.key"
              class="flex items-center gap-1 shrink-0"
              data-testid="header-mapping-variant"
            >
              <span class="badge" :class="`badge-${variant.opType}`">{{ variant.opType }}</span>
              <span
                v-if="variant.rawAction"
                class="text-[0.68rem] font-mono text-text-secondary max-w-[140px] truncate"
                :title="variant.rawAction"
              >{{ variant.rawAction }}</span>
            </span>
          </div>
        </template>
      </div>
    </template>

    <template #body>
        <div v-if="importError" class="login-error mb-2 shrink-0">
          {{ importError }}
        </div>

        <template v-if="importFiles.length && !showFileSelection">
          <ImportBatchFilesBar
            v-if="!isCustomMapping || currentStep === 1"
            :files="importFiles"
            @change-files="showFileSelection = true"
            @remove="requestClose"
          />

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
              <div v-if="isCustomMapping" class="border border-border-color rounded-sm mt-2 bg-bg-primary" :class="currentStep === 2 ? 'p-2' : 'p-3'">
                
                <!-- STEP 1: Delimiter & OpType mapping -->
                <Step1DelimiterMapping
                  v-if="currentStep === 1"
                  v-model:delimiter="importDelimiter"
                  v-model:decimalSeparator="importDecimalSep"
                  v-model:operationTypeColumnIdx="operationTypeColumnIdx"
                  v-model:operationTypeMappings="operationTypeMappings"
                  v-model:institutionKey="institutionKey"
                  :importFileHeaders="importFileHeaders"
                  :uniqueOperationTypes="uniqueOperationTypes"
                  :importFields="importFields"
                  :activeDbOpTypes="activeDbOpTypes"
                  :allRawRows="allRawRows"
                  :rawRowSources="rawRowSources"
                  :splitOpTypes="splitOpTypes"
                  @column-change="handleColumnChange"
                  @update-optype-mapping="handleUpdateOpTypeMapping"
                  @toggle-split="({ opType, enabled }) => toggleSplitType(opType, enabled)"
                  @next="currentStep = 2"
                />

                <!-- STEP 2: Drag-and-drop column mapping per transaction type -->
                <Step2ColumnMapping
                  v-else-if="currentStep === 2"
                  v-model:saveMappingTemplate="saveMappingTemplate"
                  v-model:mappingTemplateName="mappingTemplateName"
                  :uiColumns="uiColumns"
                  :columnConfigMap="columnConfigMap"
                  :operationTypeMappings="operationTypeMappings"
                  :uniqueOperationTypes="uniqueOperationTypes"
                  :activeDbOpTypes="activeDbOpTypes"
                  :importFields="importFields"
                  :allRawRows="allRawRows"
                  :operationTypeColumnIdx="operationTypeColumnIdx"
                  :matchingRowsByType="matchingRowsByType"
                  :matchingRowsByRawAction="matchingRowsByRawAction"
                  :splitOpTypes="splitOpTypes"
                  :feeTaxGroupCounts="feeTaxGroupCounts"
                  :opTypeSettings="opTypeSettings"
                  :importDecimalSep="importDecimalSep"
                  :liveValidationStats="liveValidationStats"
                  :validationErrors="validationErrors"
                  :enrichedNames="enrichedNames"
                  @back="currentStep = 1"
                  @update-optype-settings="updateOpTypeSettings"
                  @update-group-count="updateFeeTaxGroupCount"
                  @touch-config="touchColumnConfig"
                  @selection-change="(variants: MappingVariant[]) => mappingSelection = variants"
                />
              </div>
            </div>

            <!-- REAL-TIME PARSED DATA PREVIEW (Only shown when not actively designing custom mappings) -->
            <ParsedPreviewTable
              v-if="!isCustomMapping"
              :parsedPreviewRows="parsedPreviewRows"
            />
          </div>
        </template>

        <!-- File selection: upload new files and/or tick previously loaded ones,
             then continue with the ticked set as the batch. Shown on open and
             again whenever the user changes the files of a loaded batch. -->
        <template v-else>
          <ImportFileSelector
            :preselectedNames="importFiles.map(f => f.name)"
            :sessionFiles="importFiles"
            :busy="isLoadingSelection"
            :showBack="importFiles.length > 0"
            @back="showFileSelection = false"
            @confirm="onConfirmSelection"
          />
        </template>
    </template>

    <template #footer>
        <button @click="requestClose" class="btn btn-sm">Cancel</button>
        <button
          v-if="isCustomMapping && saveMappingTemplate && !isValidCustomMapping"
          @click="handleImport"
          class="btn btn-sm btn-primary !bg-warning-color !border-warning-color !text-white"
          :disabled="isImporting || showFileSelection || !mappingTemplateName.trim()"
        >
          <Loader v-if="isImporting" class="w-3.5 h-3.5 animate-spin" />
          <span v-if="isImporting">Saving template...</span>
          <span v-else>Save Incomplete Template</span>
        </button>
        <button
          v-else
          @click="handleImport"
          class="btn btn-sm btn-primary"
          :disabled="isImporting || showFileSelection || !importFiles.length || (isCustomMapping && !isValidCustomMapping) || (isCustomMapping && saveMappingTemplate && !mappingTemplateName.trim())"
        >
          <Loader v-if="isImporting" class="w-3.5 h-3.5 animate-spin" />
          <span v-if="isImporting">Importing data...</span>
          <span v-else-if="isCustomMapping && saveMappingTemplate">Save Template & Import</span>
          <span v-else>Import Transactions</span>
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
