<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { Layers, Loader, Trash2, Pencil, Upload } from '@lucide/vue';
import { api, type ImportedFileInfo } from '../../services/api';

// Composables & services
import { useImportWizard } from './useImportWizard';

// Subcomponents - nested subdirectories & globals
import Step1DelimiterMapping from './wizard/Step1DelimiterMapping.vue';
import Step2ColumnMapping from './wizard/Step2ColumnMapping.vue';
import ParsedPreviewTable from './wizard/ParsedPreviewTable.vue';

import OverwriteTemplateConfirmModal from './modals/OverwriteTemplateConfirmModal.vue';
import DeleteTemplateConfirmModal from './modals/DeleteTemplateConfirmModal.vue';
import DiscardChangesConfirmModal from './modals/DiscardChangesConfirmModal.vue';

import ImportSuccessSummary from './ImportSuccessSummary.vue';
import PreviousImportsList from './PreviousImportsList.vue';

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
  importSuccessSummary,
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

// Empty-state file selection (when the modal opens without preselected files).
const emptyStateFileInput = ref<HTMLInputElement | null>(null);
const previousImportsList = ref<InstanceType<typeof PreviousImportsList> | null>(null);

const onEmptyStateFilesSelected = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    processFiles(Array.from(target.files));
  }
};

// Re-import a stored file: fetch its original bytes and feed them through the
// same wizard flow as a fresh upload (row dedup makes this idempotent).
const loadStoredFile = async (stored: ImportedFileInfo) => {
  importError.value = '';
  try {
    const blob = await api.downloadImportedFile(stored.id);
    const file = new File([blob], stored.filename, { type: stored.content_type || 'text/csv' });
    await processFiles([file]);
  } catch (err: any) {
    importError.value = err.message || 'Failed to load the stored file.';
  } finally {
    previousImportsList.value?.clearDownloading();
  }
};

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

const preventSwipeNav = (e: WheelEvent) => {
  // Only intercept if it's primarily a horizontal swipe
  if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
    let target = e.target as HTMLElement | null;
    
    // Find nearest horizontally scrollable container
    while (target && target !== document.body && target !== document.documentElement) {
      const style = window.getComputedStyle(target);
      if ((style.overflowX === 'auto' || style.overflowX === 'scroll') && target.scrollWidth > target.clientWidth) {
        break;
      }
      target = target.parentElement;
    }
    
    if (target && target !== document.body && target !== document.documentElement) {
      const isAtLeftEdge = target.scrollLeft <= 0;
      const isAtRightEdge = target.scrollWidth - target.clientWidth <= target.scrollLeft + 1;
      
      // If we're at the edge and trying to scroll past it, aggressively prevent default
      // to kill the Chrome swipe navigation.
      if ((e.deltaX < 0 && isAtLeftEdge) || (e.deltaX > 0 && isAtRightEdge)) {
        e.preventDefault();
      }
    } else {
      // If we aren't even over a horizontal scroll container, ANY horizontal swipe is
      // just going to trigger browser navigation. Block it.
      e.preventDefault();
    }
  }
};

onMounted(() => {
  document.documentElement.style.overscrollBehaviorX = 'none';
  document.body.style.overscrollBehaviorX = 'none';
  window.addEventListener('wheel', preventSwipeNav, { passive: false });
});

onUnmounted(() => {
  document.documentElement.style.overscrollBehaviorX = '';
  document.body.style.overscrollBehaviorX = '';
  window.removeEventListener('wheel', preventSwipeNav);
});
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
      <h3 class="table-title !text-base !m-0">Import Transactions to "{{ portfolio.name }}"</h3>
    </template>

    <template #body>
        <div v-if="importError" class="login-error mb-2 shrink-0">
          {{ importError }}
        </div>

        <!-- Success State -->
        <ImportSuccessSummary
          v-if="importSuccessSummary"
          :importSuccessSummary="importSuccessSummary"
          :mappingTemplateName="mappingTemplateName"
        />

        <template v-else-if="importFiles.length">
          <div v-if="!isCustomMapping || currentStep === 1" class="flex justify-between items-center gap-3 bg-bg-tertiary py-2 px-3 rounded-sm border border-border-color mb-3">
            <div class="flex items-center gap-x-2 gap-y-0.5 min-w-0 flex-wrap">
              <Layers class="w-4 h-4 text-accent shrink-0" />
              <span v-for="f in importFiles" :key="f.name" class="flex items-baseline gap-1 min-w-0">
                <span class="text-[0.9rem] font-semibold truncate">{{ f.name }}</span>
                <span class="text-xs text-text-secondary">({{ (f.size / 1024).toFixed(1) }} KB)</span>
              </span>
              <span v-if="importFiles.length > 1" class="text-xs text-text-secondary">
                — {{ importFiles.length }} files imported as one batch; rows appearing in several files are only imported once
              </span>
            </div>
            <button @click="requestClose" class="bg-transparent border-none text-danger-color cursor-pointer text-[0.8rem] font-semibold shrink-0">Remove</button>
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

        <!-- Empty state: pick new files or re-import a stored one -->
        <template v-else>
          <div class="flex flex-col gap-4">
            <div
              class="flex flex-col items-center gap-2 border border-dashed border-border-color rounded-sm py-8 px-4 cursor-pointer hover:bg-bg-tertiary"
              data-testid="import-file-dropzone"
              @click="emptyStateFileInput?.click()"
            >
              <Upload class="w-6 h-6 text-accent" />
              <span class="text-sm font-semibold">Choose CSV file(s) to import</span>
              <span class="text-xs text-text-secondary">Several files are imported as one batch and deduplicated</span>
              <input
                type="file"
                ref="emptyStateFileInput"
                accept=".csv"
                multiple
                style="display: none;"
                @change="onEmptyStateFilesSelected"
              />
            </div>

            <PreviousImportsList ref="previousImportsList" @select="loadStoredFile" />
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
          :disabled="isImporting || !importFiles.length || (isCustomMapping && !isValidCustomMapping) || (isCustomMapping && saveMappingTemplate && !mappingTemplateName.trim())"
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
