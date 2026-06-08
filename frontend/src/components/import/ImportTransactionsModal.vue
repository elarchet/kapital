<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { api } from '../../services/api';
import { Layers, Loader, Trash2 } from '@lucide/vue';
import ColumnMappingWizard from './ColumnMappingWizard.vue';
import OverwriteTemplateConfirmModal from './OverwriteTemplateConfirmModal.vue';
import DeleteTemplateConfirmModal from './DeleteTemplateConfirmModal.vue';
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
import CustomDropdown from './CustomDropdown.vue';

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
const columnConfigMap = ref<Record<string, {
  global: ColMapping;
  typeSpecific: Record<string, ColMapping>;
}>>({});

const uiColumns = ref<Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }>>([]);

// Wizard modal popup states
const isWizardOpen = ref(false);
const wizardCsvHeaderName = ref('');
const wizardExampleValue = ref('');
const wizardActiveOpType = ref('');
const wizardColId = ref<string | null>(null);
const wizardColIdx = ref<number | null>(null);
const wizardUniqueValues = ref<string[]>([]);
const wizardInitialMapping = ref<any>(null);
const wizardTargetCells = ref<Array<{ colId: string; opType: string | null }>>([]);

// Custom exit confirmation state
const showExitConfirm = ref<boolean>(false);

// Overwrite and Delete template states
const showOverwriteConfirm = ref(false);
const hasConfirmedOverwrite = ref(false);
const showDeleteConfirm = ref(false);
const isDeletingSchema = ref(false);

const selectedSchema = computed(() => {
  if (selectedSchemaId.value === null || selectedSchemaId.value === -1) return null;
  return availableSchemas.value.find(s => s.id === selectedSchemaId.value) || null;
});

const promptDeleteTemplate = () => {
  if (selectedSchema.value && !selectedSchema.value.is_public) {
    showDeleteConfirm.value = true;
  }
};

const handleDeleteTemplate = async () => {
  if (!selectedSchema.value || selectedSchema.value.is_public) return;
  isDeletingSchema.value = true;
  importError.value = '';
  try {
    await api.deleteImportFileSchema(selectedSchema.value.id);
    selectedSchemaId.value = null;
    showDeleteConfirm.value = false;
    await loadSchemas();
  } catch (err: any) {
    importError.value = err.message || 'Failed to delete template.';
  } finally {
    isDeletingSchema.value = false;
  }
};

const onConfirmOverwrite = () => {
  showOverwriteConfirm.value = false;
  hasConfirmedOverwrite.value = true;
  handleImport();
};

// Dirty state check
const isDirty = computed(() => {
  return importFile.value !== null;
});

const selectedSchemaIdString = computed({
  get() {
    return selectedSchemaId.value !== null ? String(selectedSchemaId.value) : '';
  },
  set(val: string) {
    if (val === '') {
      selectedSchemaId.value = null;
    } else {
      selectedSchemaId.value = Number(val);
    }
    onSchemaSelect();
  }
});

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
      uiColumns.value = parsed.uiColumns;
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
      uiColumns.value = parsed.headers.map((h, idx) => ({
        id: `col-${idx}`,
        colIdx: idx,
        name: h,
        label: h
      }));
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
  uiColumns.value = importFileHeaders.value.map((h, idx) => ({
    id: `col-${idx}`,
    colIdx: idx,
    name: h,
    label: h
  }));
  columnConfigMap.value = {};
  uiColumns.value.forEach(col => {
    columnConfigMap.value[col.id] = {
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

  const guesses = prepopulateFieldGuesses(headers, allRawRows.value, operationTypeColumnIdx.value);
  const newConfigMap: Record<string, any> = {};
  uiColumns.value.forEach(col => {
    newConfigMap[col.id] = guesses[col.colIdx] || { global: { dbKey: '' }, typeSpecific: {} };
  });
  columnConfigMap.value = newConfigMap;
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

const matchingRowsByRawAction = computed(() => {
  const result: Record<string, { csvRow: string[]; rowIdx: number }[]> = {};
  if (operationTypeColumnIdx.value === null) return result;

  allRawRows.value.forEach((row, idx) => {
    const rawAction = row[operationTypeColumnIdx.value!];
    if (rawAction) {
      const trimmed = rawAction.trim();
      if (!result[trimmed]) {
        result[trimmed] = [];
      }
      result[trimmed].push({ csvRow: row, rowIdx: idx });
    }
  });
  return result;
});

const matchingRowsByType = computed(() => {
  return groupRowsByOpType(allRawRows.value, operationTypeColumnIdx.value, operationTypeMappings.value);
});

const selectedExampleOffset = ref<Record<string, number>>({});

const nextExampleForType = (opType: string) => {
  const matches = matchingRowsByRawAction.value[opType] || [];
  if (matches.length <= 1) return;
  selectedExampleOffset.value[opType] = ((selectedExampleOffset.value[opType] || 0) + 1) % matches.length;
};

const prevExampleForType = (opType: string) => {
  const matches = matchingRowsByRawAction.value[opType] || [];
  if (matches.length <= 1) return;
  selectedExampleOffset.value[opType] = ((selectedExampleOffset.value[opType] || 0) - 1 + matches.length) % matches.length;
};

const exampleTransactions = computed(() => {
  if (operationTypeColumnIdx.value === null) return [];
  return getExampleTransactions(uniqueOperationTypes.value, matchingRowsByRawAction.value, selectedExampleOffset.value);
});

const liveValidationStats = computed(() => {
  return validateLiveStats({
    importFields: importFields.value,
    importDelimiter: importDelimiter.value,
    importDecimalSep: importDecimalSep.value,
    columnConfigMap: columnConfigMap.value,
    uiColumns: uiColumns.value,
    activeDbOpTypes: activeDbOpTypes.value,
    allRawRows: allRawRows.value,
    operationTypeColumnIdx: operationTypeColumnIdx.value,
    operationTypeMappings: operationTypeMappings.value
  });
});

const goToStep2 = () => {
  if (operationTypeColumnIdx.value !== null) {
    const opTypeCol = uiColumns.value.find(c => c.colIdx === operationTypeColumnIdx.value && !c.isDuplicate);
    if (opTypeCol) {
      columnConfigMap.value[opTypeCol.id] = {
        global: {
          dbKey: 'operation_type',
          enumMappings: { ...operationTypeMappings.value }
        },
        typeSpecific: {}
      };
    }
  }
  currentStep.value = 2;
};

const openWizard = (colId: string, opType: string | null, targets?: Array<{ colId: string; opType: string | null }>, rawAction?: string | null) => {
  const col = uiColumns.value.find(c => c.id === colId);
  if (!col) return;
  const colIdx = col.colIdx;

  wizardColId.value = colId;
  wizardColIdx.value = colIdx;
  wizardActiveOpType.value = opType || '';
  wizardTargetCells.value = targets && targets.length > 0 ? targets : [{ colId, opType }];

  const setup = getWizardSetup({
    colId,
    colIdx,
    opType,
    rawAction: rawAction || null,
    importFileHeaders: importFileHeaders.value,
    exampleTransactions: exampleTransactions.value,
    allRawRows: allRawRows.value,
    columnConfigMap: columnConfigMap.value,
    matchingRowsByType: matchingRowsByType.value,
    targets: wizardTargetCells.value.map(t => ({ colId: t.colId, colIdx: uiColumns.value.find(c => c.id === t.colId)?.colIdx || 0, opType: t.opType }))
  });

  if (targets && targets.length > 1) {
    wizardCsvHeaderName.value = `${setup.csvHeaderName} (+ ${targets.length - 1} other columns)`;
  } else {
    wizardCsvHeaderName.value = setup.csvHeaderName;
  }
  
  wizardExampleValue.value = setup.exampleValue;
  wizardUniqueValues.value = setup.uniqueValues;
  wizardInitialMapping.value = setup.initialMapping;

  isWizardOpen.value = true;
};

const handleWizardSave = (payload: any) => {
  if (wizardTargetCells.value.length > 0) {
    wizardTargetCells.value.forEach(target => {
      saveWizardConfig(columnConfigMap.value, target.colId, target.opType, {
        ...payload,
        scope: target.opType ? 'type' : 'global'
      });
    });
  }
  isWizardOpen.value = false;
};

const handleWizardClear = () => {
  if (wizardTargetCells.value.length > 0) {
    wizardTargetCells.value.forEach(target => {
      clearWizardConfig(columnConfigMap.value, target.colId, target.opType);
    });
  }
  isWizardOpen.value = false;
};

const handleUpdateMapping = ({ colId, opType, mapping }: { colId: string; opType: string | null; mapping: any }) => {
  if (mapping === null) {
    clearWizardConfig(columnConfigMap.value, colId, opType);
  } else {
    saveWizardConfig(columnConfigMap.value, colId, opType, {
      dbKey: mapping.dbKey,
      scope: opType ? 'type' : 'global',
      divisor: mapping.divisor,
      multiplier: mapping.multiplier,
      enumMappings: mapping.enumMappings,
      dateFormat: mapping.dateFormat
    });
  }
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
    uiColumns: uiColumns.value,
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
    uiColumns: uiColumns.value,
    importFields: importFields.value
  });
});

const buildCustomMappingPayload = () => {
  return buildCustomMappingPayloadHelper({
    operationTypeColumnIdx: operationTypeColumnIdx.value,
    importFileHeaders: importFileHeaders.value,
    columnConfigMap: columnConfigMap.value,
    uiColumns: uiColumns.value,
    operationTypeMappings: operationTypeMappings.value,
    importFields: importFields.value
  });
};

const handleDuplicateColumn = (colId: string) => {
  const baseCol = uiColumns.value.find(c => c.id === colId);
  if (!baseCol) return;
  const dupCount = uiColumns.value.filter(c => c.colIdx === baseCol.colIdx).length;
  const newId = `${colId}_dup_${dupCount}`;
  const newCol = {
    id: newId,
    colIdx: baseCol.colIdx,
    name: baseCol.name,
    label: `${baseCol.name} (Copy)`,
    isDuplicate: true
  };
  const lastIndex = uiColumns.value.map(c => c.colIdx).lastIndexOf(baseCol.colIdx);
  uiColumns.value.splice(lastIndex + 1, 0, newCol);
  columnConfigMap.value[newId] = {
    global: { dbKey: '' },
    typeSpecific: {}
  };
};

const handleDeleteColumn = (colId: string) => {
  const index = uiColumns.value.findIndex(c => c.id === colId);
  if (index !== -1 && uiColumns.value[index].isDuplicate) {
    uiColumns.value.splice(index, 1);
    delete columnConfigMap.value[colId];
  }
};

const handleUpdateOpTypeMapping = ({ rawAction, dbOpType }: { rawAction: string; dbOpType: string }) => {
  if (dbOpType === '') {
    delete operationTypeMappings.value[rawAction];
  } else {
    operationTypeMappings.value[rawAction] = dbOpType;
  }
  
  if (operationTypeColumnIdx.value !== null) {
    const opTypeCol = uiColumns.value.find(c => c.colIdx === operationTypeColumnIdx.value && !c.isDuplicate);
    if (opTypeCol) {
      columnConfigMap.value[opTypeCol.id].global = {
        dbKey: 'operation_type',
        enumMappings: { ...operationTypeMappings.value }
      };
    }
  }
};

const handleImport = async () => {
  if (!importFile.value || !props.portfolio.id) return;
  isImporting.value = true;
  importError.value = '';
  importSuccessSummary.value = null;

  try {
    let finalSchemaId = selectedSchemaId.value;

    if (isCustomMapping.value && saveMappingTemplate.value && mappingTemplateName.value.trim()) {
      // Check if a template with this name already exists
      const existingSchema = availableSchemas.value.find(
        s => s.name.trim().toLowerCase() === mappingTemplateName.value.trim().toLowerCase()
      );

      if (existingSchema) {
        if (existingSchema.is_public || existingSchema.user_id === null) {
          throw new Error(`A public template named "${existingSchema.name}" already exists. Please choose a unique name.`);
        }

        if (!hasConfirmedOverwrite.value) {
          showOverwriteConfirm.value = true;
          isImporting.value = false;
          return;
        }
      }
    }

    // Reset the confirmation flag for future runs
    const overwriteConfirmed = hasConfirmedOverwrite.value;
    hasConfirmedOverwrite.value = false;

    if (isCustomMapping.value) {
      if (!isValidCustomMapping.value) {
        if (saveMappingTemplate.value && mappingTemplateName.value.trim()) {
          const mappingConfig = buildCustomMappingPayload();
          const templateData = {
            name: mappingTemplateName.value.trim(),
            is_public: false,
            delimiter: importDelimiter.value,
            decimal_separator: importDecimalSep.value,
            mappings: JSON.stringify(mappingConfig),
            is_incomplete: true,
          };

          if (overwriteConfirmed) {
            const existingSchema = availableSchemas.value.find(
              s => s.name.trim().toLowerCase() === mappingTemplateName.value.trim().toLowerCase()
            );
            if (existingSchema) {
              await api.updateImportFileSchema(existingSchema.id, templateData);
            }
          } else {
            await api.createImportFileSchema(templateData);
          }
          
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
        const templateData = {
          name: mappingTemplateName.value.trim(),
          is_public: false,
          delimiter: importDelimiter.value,
          decimal_separator: importDecimalSep.value,
          mappings: JSON.stringify(mappingConfig),
          is_incomplete: false,
        };

        let savedSchema;
        if (overwriteConfirmed) {
          const existingSchema = availableSchemas.value.find(
            s => s.name.trim().toLowerCase() === mappingTemplateName.value.trim().toLowerCase()
          );
          if (existingSchema) {
            savedSchema = await api.updateImportFileSchema(existingSchema.id, templateData);
          } else {
            savedSchema = await api.createImportFileSchema(templateData);
          }
        } else {
          savedSchema = await api.createImportFileSchema(templateData);
        }
        finalSchemaId = savedSchema.id;
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
    <div class="modal-card flex flex-col transition-all duration-300" :class="importFile && !importSuccessSummary ? 'modal-card--wide' : 'w-full max-w-[550px]'">
      <div class="modal-header !py-3 !px-4">
        <h3 class="table-title !text-base !m-0">Import Transactions to "{{ portfolio.name }}"</h3>
        <button @click="requestClose" class="bg-transparent border-0 cursor-pointer text-[1.25rem] text-text-secondary transition-colors duration-150 ease-in-out hover:text-text-primary">&times;</button>
      </div>
      
      <div class="modal-body !p-4" style="overflow-y: auto; flex: 1;">
        <div v-if="importError" class="login-error" style="margin-bottom: 0.5rem;">
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
            <div v-if="!isCustomMapping || currentStep === 1" style="display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-tertiary); padding: 0.5rem 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); margin-bottom: 0.75rem;">
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <Layers style="width: 16px; height: 16px; color: var(--accent-color);" />
                <span style="font-weight: 600; font-size: 0.9rem;">{{ importFile.name }}</span>
                <span style="font-size: 0.75rem; color: var(--text-secondary);">({{ (importFile.size / 1024).toFixed(1) }} KB)</span>
              </div>
              <button @click="importFile = null" style="background: none; border: none; color: var(--color-danger); cursor: pointer; font-size: 0.8rem; font-weight: 600;">Remove</button>
            </div>

            <div style="display: flex; flex-direction: column; gap: 0.75rem; width: 100%;">
              <div>
                <!-- Template select -->
                <div v-if="!isCustomMapping || currentStep === 1" class="form-group !mb-3" style="max-width: 450px;">
                  <label>Template Schema</label>
                  <div style="display: flex; gap: 0.5rem; align-items: stretch; margin-bottom: 0.25rem;">
                    <div style="flex: 1; min-width: 0;">
                      <CustomDropdown
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
                    @column-change="prepopulateOpTypeGuesses"
                    @next="goToStep2"
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
      </div>

      <div class="modal-footer !py-3 !px-4">
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

