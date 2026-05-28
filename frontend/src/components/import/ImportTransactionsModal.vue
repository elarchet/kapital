<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { api } from '../../services/api';
import { Layers, Loader } from '@lucide/vue';
import ColumnMappingWizard from './ColumnMappingWizard.vue';
import DiscardChangesConfirmModal from './DiscardChangesConfirmModal.vue';
import ImportSuccessSummary from './ImportSuccessSummary.vue';
import CSVUploadZone from './CSVUploadZone.vue';
import Step1DelimiterMapping from './Step1DelimiterMapping.vue';
import ParsedPreviewTable from './ParsedPreviewTable.vue';
import {
  prepopulateFieldGuesses,
  prepopulateOpTypeGuesses as prepopulateOpTypeGuessesHelper,
  buildCustomMappingPayload as buildCustomMappingPayloadHelper,
  validateLiveStats,
  parsePreviewRows,
  getValidationErrors,
  parseSchemaMappings,
  parseCsvText,
  groupRowsByOpType,
  getExampleTransactions,
  getWizardSetup,
  saveWizardConfig,
  clearWizardConfig
} from '../../services/import';
import Step2ColumnMapping from './Step2ColumnMapping.vue';

const props = defineProps<{
  portfolio: {
    id: number;
    name: string;
  };
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'success'): void;
}>();

// UI States
const importFile = ref<File | null>(null);
const fileText = ref('');
const importFileHeaders = ref<string[]>([]);
const availableSchemas = ref<any[]>([]);
const selectedSchemaId = ref<number | null>(null);
const autodetectedSchemaId = ref<number | null>(null);
const isCustomMapping = ref(false);

const isImporting = ref(false);
const importError = ref('');
const importSuccessSummary = ref<{ positions_created: number; operations_imported: number; operations_skipped: number; is_template_only?: boolean } | null>(null);

// Mappings configuration
const mappingTemplateName = ref('');
const saveMappingTemplate = ref(false);
const importDelimiter = ref(',');
const importDecimalSep = ref('.');

// Dynamic metadata & row parsing state
const importFields = ref<any[]>([]);
const allRawRows = ref<string[][]>([]);

// Wizard step: 1 = Delimiter & OpType mapping, 2 = Columns Mapping & Verification
const currentStep = ref(1);

// Step 1: Operation type column and value mapping
const operationTypeColumnIdx = ref<number | null>(null);
const operationTypeMappings = ref<Record<string, string>>({}); // raw CSV action -> DB opType

// Step 2: Column configs: colIdx -> { global: ColMapping, typeSpecific: Record<string, ColMapping> }
interface ColMapping {
  dbKey: string;
  divisor?: number;
  multiplier?: number;
  enumMappings?: Record<string, string>;
}
const columnConfigMap = ref<Record<number, {
  global: ColMapping;
  typeSpecific: Record<string, ColMapping>;
}>>({});

// Wizard modal popup states
const isWizardOpen = ref(false);
const wizardCsvHeaderName = ref('');
const wizardExampleValue = ref('');
const wizardActiveOpType = ref('');
const wizardColIdx = ref<number | null>(null);
const wizardUniqueValues = ref<string[]>([]);
const wizardInitialMapping = ref<any>(null);

// Custom exit confirmation state
const showExitConfirm = ref<boolean>(false);

// Dirty state check
const isDirty = computed(() => {
  return importFile.value !== null;
});

const requestClose = () => {
  if (isDirty.value && !importSuccessSummary.value) {
    showExitConfirm.value = true;
  } else {
    emit('close');
  }
};

const loadSchemas = async () => {
  try {
    availableSchemas.value = await api.getImportFileSchemas();
  } catch (err: any) {
    console.error('Failed to load schemas:', err);
  }
};

const isSchemaIncomplete = (schema: any) => {
  return schema ? !!schema.is_incomplete : false;
};

const onSchemaSelect = () => {
  if (selectedSchemaId.value === -1) {
    isCustomMapping.value = true;
    selectedSchemaId.value = null;
    initializeConfigs();
    prepopulateGuesses(importFileHeaders.value);
  } else {
    const schema = availableSchemas.value.find(s => s.id === selectedSchemaId.value);
    if (schema) {
      const isIncomplete = isSchemaIncomplete(schema);
      if (isIncomplete) {
        isCustomMapping.value = true;
        saveMappingTemplate.value = true;
        mappingTemplateName.value = schema.name;
      } else {
        isCustomMapping.value = false;
      }
      importDelimiter.value = schema.delimiter;
      importDecimalSep.value = schema.decimal_separator;
      
      const parsed = parseSchemaMappings(schema.mappings, importFileHeaders.value);
      operationTypeColumnIdx.value = parsed.operationTypeColumnIdx;
      operationTypeMappings.value = parsed.operationTypeMappings;
      columnConfigMap.value = parsed.columnConfigMap;
    }
  }
};

const processFile = async (file: File) => {
  importFile.value = file;
  importError.value = '';
  importSuccessSummary.value = null;

  const reader = new FileReader();
  reader.onload = async (e) => {
    const text = e.target?.result as string;
    fileText.value = text;
    
    const parsed = parseCsvText(text);
    if (parsed.headers.length > 0) {
      importDelimiter.value = parsed.delimiter;
      importFileHeaders.value = parsed.headers;
      allRawRows.value = parsed.rawRows;
      currentStep.value = 1;

      // Auto-detect schema
      try {
        const detectRes = await api.detectImportFileSchema(parsed.headers);
        if (detectRes.schema_id) {
          autodetectedSchemaId.value = detectRes.schema_id;
          selectedSchemaId.value = detectRes.schema_id;
          isCustomMapping.value = false;
          onSchemaSelect();
        } else {
          autodetectedSchemaId.value = null;
          selectedSchemaId.value = null;
          isCustomMapping.value = true;
          prepopulateGuesses(parsed.headers);
        }
      } catch (err: any) {
        console.error('Failed to autodetect schema:', err);
        isCustomMapping.value = true;
        prepopulateGuesses(parsed.headers);
      }
    }
  };
  reader.readAsText(file);
};

const initializeConfigs = () => {
  columnConfigMap.value = {};
  importFileHeaders.value.forEach((_, idx) => {
    columnConfigMap.value[idx] = {
      global: { dbKey: '' },
      typeSpecific: {}
    };
  });
  operationTypeMappings.value = {};
  operationTypeColumnIdx.value = null;
  currentStep.value = 1;
};

const prepopulateGuesses = (headers: string[]) => {
  initializeConfigs();

  const opIdx = headers.findIndex(h => ['action', 'type', 'transaction type'].some(k => h.toLowerCase().includes(k.toLowerCase())));
  if (opIdx >= 0) {
    operationTypeColumnIdx.value = opIdx;
    prepopulateOpTypeGuesses();
  }

  columnConfigMap.value = prepopulateFieldGuesses(headers, allRawRows.value, operationTypeColumnIdx.value);
};

const uniqueOperationTypes = computed(() => {
  if (operationTypeColumnIdx.value === null) return [];
  const uniqueSet = new Set<string>();
  allRawRows.value.forEach(row => {
    const val = row[operationTypeColumnIdx.value!];
    if (val && val.trim()) {
      uniqueSet.add(val.trim());
    }
  });
  return Array.from(uniqueSet);
});

const prepopulateOpTypeGuesses = () => {
  operationTypeMappings.value = prepopulateOpTypeGuessesHelper(uniqueOperationTypes.value);
};

const activeDbOpTypes = computed(() => {
  const types = new Set<string>();
  Object.values(operationTypeMappings.value).forEach(v => {
    if (v) types.add(v);
  });
  return Array.from(types);
});

const matchingRowsByType = computed(() => {
  return groupRowsByOpType(allRawRows.value, operationTypeColumnIdx.value, operationTypeMappings.value);
});

const selectedExampleOffset = ref<Record<string, number>>({});

const nextExampleForType = (opType: string) => {
  const matches = matchingRowsByType.value[opType] || [];
  if (matches.length <= 1) return;
  selectedExampleOffset.value[opType] = ((selectedExampleOffset.value[opType] || 0) + 1) % matches.length;
};

const prevExampleForType = (opType: string) => {
  const matches = matchingRowsByType.value[opType] || [];
  if (matches.length <= 1) return;
  selectedExampleOffset.value[opType] = ((selectedExampleOffset.value[opType] || 0) - 1 + matches.length) % matches.length;
};

const exampleTransactions = computed(() => {
  if (operationTypeColumnIdx.value === null) return [];
  return getExampleTransactions(activeDbOpTypes.value, matchingRowsByType.value, selectedExampleOffset.value);
});

const liveValidationStats = computed(() => {
  return validateLiveStats({
    importFields: importFields.value,
    importDelimiter: importDelimiter.value,
    importDecimalSep: importDecimalSep.value,
    columnConfigMap: columnConfigMap.value,
    activeDbOpTypes: activeDbOpTypes.value,
    allRawRows: allRawRows.value,
    operationTypeColumnIdx: operationTypeColumnIdx.value,
    operationTypeMappings: operationTypeMappings.value
  });
});

const goToStep2 = () => {
  if (operationTypeColumnIdx.value !== null) {
    columnConfigMap.value[operationTypeColumnIdx.value].global = {
      dbKey: 'operation_type',
      enumMappings: { ...operationTypeMappings.value }
    };
  }
  currentStep.value = 2;
};

const openWizard = (colIdx: number, opType: string | null) => {
  if (colIdx === operationTypeColumnIdx.value) return; // Already configured in Step 1
  wizardColIdx.value = colIdx;
  wizardActiveOpType.value = opType || '';

  const setup = getWizardSetup({
    colIdx,
    opType,
    importFileHeaders: importFileHeaders.value,
    exampleTransactions: exampleTransactions.value,
    allRawRows: allRawRows.value,
    columnConfigMap: columnConfigMap.value
  });

  wizardCsvHeaderName.value = setup.csvHeaderName;
  wizardExampleValue.value = setup.exampleValue;
  wizardUniqueValues.value = setup.uniqueValues;
  wizardInitialMapping.value = setup.initialMapping;

  isWizardOpen.value = true;
};

const handleWizardSave = (payload: any) => {
  if (wizardColIdx.value !== null) {
    saveWizardConfig(columnConfigMap.value, wizardColIdx.value, wizardActiveOpType.value || null, payload);
  }
  isWizardOpen.value = false;
};

const handleWizardClear = () => {
  if (wizardColIdx.value !== null) {
    clearWizardConfig(columnConfigMap.value, wizardColIdx.value, wizardActiveOpType.value || null);
  }
  isWizardOpen.value = false;
};

const validationErrors = computed(() => {
  return getValidationErrors({
    importFile: importFile.value,
    operationTypeColumnIdx: operationTypeColumnIdx.value,
    uniqueOperationTypes: uniqueOperationTypes.value,
    operationTypeMappings: operationTypeMappings.value,
    activeDbOpTypes: activeDbOpTypes.value,
    importFields: importFields.value,
    columnConfigMap: columnConfigMap.value,
    liveValidationStats: liveValidationStats.value
  });
});

const isValidCustomMapping = computed(() => validationErrors.value.length === 0);

// Client-side parser for displaying mapped data in real-time
const parsedPreviewRows = computed(() => {
  return parsePreviewRows({
    fileText: fileText.value,
    importDelimiter: importDelimiter.value,
    importDecimalSep: importDecimalSep.value,
    operationTypeColumnIdx: operationTypeColumnIdx.value,
    operationTypeMappings: operationTypeMappings.value,
    columnConfigMap: columnConfigMap.value,
    importFields: importFields.value
  });
});

const buildCustomMappingPayload = () => {
  return buildCustomMappingPayloadHelper({
    operationTypeColumnIdx: operationTypeColumnIdx.value,
    importFileHeaders: importFileHeaders.value,
    columnConfigMap: columnConfigMap.value,
    operationTypeMappings: operationTypeMappings.value,
    importFields: importFields.value
  });
};;

const handleImport = async () => {
  if (!importFile.value || !props.portfolio.id) return;
  isImporting.value = true;
  importError.value = '';
  importSuccessSummary.value = null;

  try {
    let finalSchemaId = selectedSchemaId.value;

    if (isCustomMapping.value) {
      if (!isValidCustomMapping.value) {
        if (saveMappingTemplate.value && mappingTemplateName.value.trim()) {
          const mappingConfig = buildCustomMappingPayload();

          await api.createImportFileSchema({
            name: mappingTemplateName.value.trim(),
            is_public: false,
            delimiter: importDelimiter.value,
            decimal_separator: importDecimalSep.value,
            mappings: JSON.stringify(mappingConfig),
            is_incomplete: true,
          });
          
          importSuccessSummary.value = {
            positions_created: 0,
            operations_imported: 0,
            operations_skipped: 0,
            is_template_only: true,
          };
          loadSchemas();
          emit('success');
          return;
        } else {
          throw new Error('Please fix the validation errors before importing.');
        }
      }
      const mappingConfig = buildCustomMappingPayload();

      if (saveMappingTemplate.value && mappingTemplateName.value.trim()) {
        const newSchema = await api.createImportFileSchema({
          name: mappingTemplateName.value.trim(),
          is_public: false,
          delimiter: importDelimiter.value,
          decimal_separator: importDecimalSep.value,
          mappings: JSON.stringify(mappingConfig),
          is_incomplete: false,
        });
        finalSchemaId = newSchema.id;
      } else {
        const res = await api.importPositions(
          props.portfolio.id,
          importFile.value,
          null,
          {
            mappings: mappingConfig,
            delimiter: importDelimiter.value,
            decimal_separator: importDecimalSep.value,
          }
        );
        importSuccessSummary.value = res;
        emit('success');
        return;
      }
    }

    if (finalSchemaId) {
      const res = await api.importPositions(props.portfolio.id, importFile.value, finalSchemaId, null);
      importSuccessSummary.value = res;
      emit('success');
    }
  } catch (err: any) {
    importError.value = err.message || 'Import failed.';
  } finally {
    isImporting.value = false;
  }
};

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && !isWizardOpen.value) {
    if (showExitConfirm.value) {
      showExitConfirm.value = false;
    } else {
      requestClose();
    }
  }
};

onMounted(async () => {
  try {
    const meta = await api.getImportMetadata();
    importFields.value = meta.fields || [];
  } catch (err) {
    console.error('Failed to load import metadata:', err);
  }
  loadSchemas();
  window.addEventListener('keydown', handleKeyDown);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown);
});
</script>

<template>
  <div class="modal-overlay" @click.self="requestClose">
    <div class="modal-card wide-modal">
      <div class="modal-header">
        <h3 class="table-title">Import Transactions to "{{ portfolio.name }}"</h3>
        <button @click="requestClose" class="modal-close-btn">&times;</button>
      </div>
      
      <div class="modal-body" style="overflow-y: auto; flex: 1;">
        <div v-if="importError" class="login-error" style="margin-bottom: 1rem;">
          {{ importError }}
        </div>

        <!-- Success State -->
        <ImportSuccessSummary
          v-if="importSuccessSummary"
          :importSuccessSummary="importSuccessSummary"
          :mappingTemplateName="mappingTemplateName"
        />

        <template v-else>
          <!-- File upload area -->
          <CSVUploadZone
            v-if="!importFile"
            @file-selected="processFile"
          />

          <div v-else>
            <div style="display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-tertiary); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); margin-bottom: 1.25rem;">
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <Layers style="width: 16px; height: 16px; color: var(--accent-color);" />
                <span style="font-weight: 600; font-size: 0.9rem;">{{ importFile.name }}</span>
                <span style="font-size: 0.75rem; color: var(--text-secondary);">({{ (importFile.size / 1024).toFixed(1) }} KB)</span>
              </div>
              <button @click="importFile = null" style="background: none; border: none; color: var(--color-danger); cursor: pointer; font-size: 0.8rem; font-weight: 600;">Remove</button>
            </div>

            <div style="display: flex; flex-direction: column; gap: 1.5rem; width: 100%;">
              <div>
                <!-- Template select -->
                <div class="form-group" style="max-width: 400px;">
                  <label for="templateSelect">Template Schema</label>
                  <select v-model="selectedSchemaId" id="templateSelect" @change="onSchemaSelect" class="form-control">
                    <option v-for="schema in availableSchemas" :key="schema.id" :value="schema.id">
                      {{ schema.name }} {{ schema.is_public ? '(Public)' : '(Saved)' }} {{ isSchemaIncomplete(schema) ? '[Incomplete]' : '' }}
                    </option>
                    <option :value="-1">Custom Mapping Template...</option>
                  </select>
                  <p v-if="autodetectedSchemaId && selectedSchemaId === autodetectedSchemaId" style="font-size: 0.75rem; color: var(--color-success); margin-top: 0.25rem; font-weight: 500;">
                    ✓ Autodetected format matching this file
                  </p>
                </div>

                <!-- Custom mapping builder form -->
                <div v-if="isCustomMapping" style="border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1.5rem; margin-top: 1rem; background-color: var(--bg-primary);">
                  
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
                    @column-change="prepopulateOpTypeGuesses"
                    @next="goToStep2"
                  />

                  <!-- STEP 2: Columns mapping & live stats verification -->
                  <Step2ColumnMapping
                    v-else-if="currentStep === 2"
                    v-model:saveMappingTemplate="saveMappingTemplate"
                    v-model:mappingTemplateName="mappingTemplateName"
                    :importFileHeaders="importFileHeaders"
                    :operationTypeColumnIdx="operationTypeColumnIdx"
                    :columnConfigMap="columnConfigMap"
                    :activeDbOpTypes="activeDbOpTypes"
                    :importFields="importFields"
                    :exampleTransactions="exampleTransactions"
                    :liveValidationStats="liveValidationStats"
                    :validationErrors="validationErrors"
                    @back="currentStep = 1"
                    @open-wizard="({ colIdx, opType }) => openWizard(colIdx, opType)"
                    @prev-example="prevExampleForType"
                    @next-example="nextExampleForType"
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
      </div>

      <div class="modal-footer">
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
      </div>
    </div>
  </div>

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
    :delimiter="importDelimiter"
    :decimalSeparator="importDecimalSep"
    :uniqueCsvValues="wizardUniqueValues"
    :initialMapping="wizardInitialMapping"
    @close="isWizardOpen = false"
    @clear="handleWizardClear"
    @save="handleWizardSave"
  />
</template>

<style scoped>
.modal-close-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.25rem;
  color: var(--text-secondary);
  transition: color var(--transition-fast);
}
.modal-close-btn:hover {
  color: var(--text-primary);
}

.wide-modal {
  max-width: 1400px !important;
  width: 95vw !important;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
