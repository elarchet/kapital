import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { api } from '../../services/api';
import { useSchemaManagement } from './useSchemaManagement';
import { useWizardMapping } from './useWizardMapping';
import { useImportFileProcessor } from './useImportFileProcessor';
import { useImportExecutor } from './useImportExecutor';
import {
  buildCustomMappingPayload as buildCustomMappingPayloadHelper,
  validateLiveStats,
  parsePreviewRows,
  getValidationErrors,
  parseSchemaMappings,
  groupRowsByOpType
} from '../../services/import';

interface Portfolio {
  id: number;
  name: string;
}

export function useImportWizard(props: { portfolio: Portfolio; initialFile?: File | null }, emit: any) {
  // Shared state refs
  const importFile = ref<File | null>(null);
  const fileText = ref('');
  const importFileHeaders = ref<string[]>([]);
  const allRawRows = ref<string[][]>([]);
  
  const isCustomMapping = ref(false);
  const mappingTemplateName = ref('');
  const saveMappingTemplate = ref(false);
  const importDelimiter = ref(',');
  const importDecimalSep = ref('.');

  const importFields = ref<any[]>([]);
  const currentStep = ref(1);

  const operationTypeColumnIdx = ref<number | null>(null);
  const operationTypeMappings = ref<Record<string, string>>({});

  const columnConfigMap = ref<Record<string, any>>({});
  const uiColumns = ref<Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }>>([]);

  const showExitConfirm = ref(false);
  const isDirty = computed(() => importFile.value !== null);

  // Configuration helpers
  const initializeConfigs = () => {
    uiColumns.value = importFileHeaders.value.map((h, idx) => ({ id: `col-${idx}`, colIdx: idx, name: h, label: h }));
    columnConfigMap.value = {};
    uiColumns.value.forEach(col => {
      columnConfigMap.value[col.id] = { typeSpecific: {} };
    });
    operationTypeMappings.value = {};
    operationTypeColumnIdx.value = null;
    currentStep.value = 1;
  };

  const handleColumnChange = () => {
    operationTypeMappings.value = {};
    uiColumns.value = importFileHeaders.value.map((h, idx) => ({ id: `col-${idx}`, colIdx: idx, name: h, label: h }));
    columnConfigMap.value = {};
    uiColumns.value.forEach(col => {
      columnConfigMap.value[col.id] = { typeSpecific: {} };
    });
  };

  const onSchemaSelect = () => {
    if (schemaMgmt.selectedSchemaId.value === -1) {
      isCustomMapping.value = true;
      schemaMgmt.selectedSchemaId.value = null;
      initializeConfigs();
    } else {
      const schema = schemaMgmt.availableSchemas.value.find(s => s.id === schemaMgmt.selectedSchemaId.value);
      if (schema) {
        isCustomMapping.value = schemaMgmt.isSchemaIncomplete(schema);
        if (isCustomMapping.value) {
          saveMappingTemplate.value = true;
          mappingTemplateName.value = schema.name;
        }
        importDelimiter.value = schema.delimiter;
        importDecimalSep.value = schema.decimal_separator;
        
        const parsed = parseSchemaMappings(schema.mappings, importFileHeaders.value);
        operationTypeColumnIdx.value = parsed.operationTypeColumnIdx;
        
        const normalizedMappings: Record<string, string> = {};
        if (parsed.operationTypeColumnIdx !== null) {
          const uniqueSet = new Set<string>();
          allRawRows.value.forEach(row => {
            const val = row[parsed.operationTypeColumnIdx!];
            if (val && val.trim()) uniqueSet.add(val.trim());
          });
          const fileUniqueOps = Array.from(uniqueSet);

          Object.entries(parsed.operationTypeMappings).forEach(([rawAction, dbOpType]) => {
            const matchedKey = fileUniqueOps.find(
              k => k.toLowerCase() === rawAction.trim().toLowerCase()
            );
            if (matchedKey) {
              normalizedMappings[matchedKey] = dbOpType;
            } else {
              normalizedMappings[rawAction.trim()] = dbOpType;
            }
          });
        } else {
          Object.entries(parsed.operationTypeMappings).forEach(([rawAction, dbOpType]) => {
            normalizedMappings[rawAction.trim()] = dbOpType;
          });
        }

        operationTypeMappings.value = normalizedMappings;
        columnConfigMap.value = parsed.columnConfigMap;
        uiColumns.value = parsed.uiColumns;
      } else {
        isCustomMapping.value = true;
        initializeConfigs();
      }
    }
  };

  // Computeds
  const uniqueOperationTypes = computed(() => {
    if (operationTypeColumnIdx.value === null) return [];
    const uniqueSet = new Set<string>();
    allRawRows.value.forEach(row => {
      const val = row[operationTypeColumnIdx.value!];
      if (val && val.trim()) uniqueSet.add(val.trim());
    });
    return Array.from(uniqueSet);
  });

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
        if (!result[trimmed]) result[trimmed] = [];
        result[trimmed].push({ csvRow: row, rowIdx: idx });
      }
    });
    return result;
  });

  const matchingRowsByType = computed(() => {
    return groupRowsByOpType(allRawRows.value, operationTypeColumnIdx.value, operationTypeMappings.value);
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

  // Sub-composables orchestration
  const schemaMgmt = useSchemaManagement();

  const wizardMapping = useWizardMapping(
    uiColumns,
    columnConfigMap,
    importFileHeaders,
    matchingRowsByType,
    matchingRowsByRawAction,
    allRawRows,
    operationTypeMappings
  );

  const executor = useImportExecutor({
    portfolio: props.portfolio,
    importFile,
    selectedSchemaId: schemaMgmt.selectedSchemaId,
    availableSchemas: schemaMgmt.availableSchemas,
    loadSchemas: schemaMgmt.loadSchemas,
    isCustomMapping,
    saveMappingTemplate,
    mappingTemplateName,
    isValidCustomMapping,
    importDelimiter,
    importDecimalSep,
    buildCustomMappingPayload,
    initializeConfigs,
    schemaDeleteTemplate: schemaMgmt.handleDeleteTemplate,
    emit,
  });

  const { processFile } = useImportFileProcessor({
    importFile,
    fileText,
    importFileHeaders,
    allRawRows,
    importDelimiter,
    uiColumns,
    currentStep,
    autodetectedSchemaId: schemaMgmt.autodetectedSchemaId,
    selectedSchemaId: schemaMgmt.selectedSchemaId,
    isCustomMapping,
    importError: executor.importError,
    importSuccessSummary: executor.importSuccessSummary,
    onSchemaSelect,
    initializeConfigs,
  });

  // Watchers & Life Cycle
  const requestClose = () => {
    if (isDirty.value && !executor.importSuccessSummary.value) {
      showExitConfirm.value = true;
    } else {
      emit('close');
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && !wizardMapping.isWizardOpen.value) {
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
    await schemaMgmt.loadSchemas();
    window.addEventListener('keydown', handleKeyDown);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', handleKeyDown);
  });

  watch(() => props.initialFile, (newFile) => {
    if (newFile) processFile(newFile);
  }, { immediate: true });

  const panelWidth = ref(550);
  watch(
    () => importFile.value,
    (newVal) => {
      panelWidth.value = newVal ? Math.min(1400, window.innerWidth * 0.85) : 550;
    },
    { immediate: true }
  );

  const selectedSchemaIdString = computed({
    get() {
      return schemaMgmt.selectedSchemaId.value !== null ? String(schemaMgmt.selectedSchemaId.value) : '';
    },
    set(val: string) {
      if (val === '') {
        schemaMgmt.selectedSchemaId.value = null;
      } else {
        schemaMgmt.selectedSchemaId.value = Number(val);
      }
      onSchemaSelect();
    }
  });

  return {
    // Composable delegates
    availableSchemas: schemaMgmt.availableSchemas,
    selectedSchemaId: schemaMgmt.selectedSchemaId,
    autodetectedSchemaId: schemaMgmt.autodetectedSchemaId,
    selectedSchema: schemaMgmt.selectedSchema,
    selectedSchemaIdString,
    showDeleteConfirm: schemaMgmt.showDeleteConfirm,
    isDeletingSchema: schemaMgmt.isDeletingSchema,
    handleDeleteTemplate: executor.handleDeleteTemplateWrapper,

    isWizardOpen: wizardMapping.isWizardOpen,
    wizardCsvHeaderName: wizardMapping.wizardCsvHeaderName,
    wizardExampleValue: wizardMapping.wizardExampleValue,
    wizardActiveOpType: wizardMapping.wizardActiveOpType,
    wizardColId: wizardMapping.wizardColId,
    wizardColIdx: wizardMapping.wizardColIdx,
    wizardUniqueValues: wizardMapping.wizardUniqueValues,
    wizardInitialMapping: wizardMapping.wizardInitialMapping,
    wizardTargetCells: wizardMapping.wizardTargetCells,
    exampleTransactions: wizardMapping.exampleTransactions,
    nextExampleForType: wizardMapping.nextExampleForType,
    prevExampleForType: wizardMapping.prevExampleForType,
    openWizard: wizardMapping.openWizard,
    handleWizardSave: wizardMapping.handleWizardSave,
    handleWizardClear: wizardMapping.handleWizardClear,
    handleUpdateMapping: wizardMapping.handleUpdateMapping,
    handleDuplicateColumn: wizardMapping.handleDuplicateColumn,
    handleDeleteColumn: wizardMapping.handleDeleteColumn,
    handleUpdateOpTypeMapping: wizardMapping.handleUpdateOpTypeMapping,

    // Local states & computed
    importFile,
    fileText,
    importFileHeaders,
    isCustomMapping,
    isImporting: executor.isImporting,
    importError: executor.importError,
    importSuccessSummary: executor.importSuccessSummary,
    mappingTemplateName,
    saveMappingTemplate,
    importDelimiter,
    importDecimalSep,
    importFields,
    allRawRows,
    currentStep,
    operationTypeColumnIdx,
    operationTypeMappings,
    columnConfigMap,
    uiColumns,
    showExitConfirm,
    showOverwriteConfirm: executor.showOverwriteConfirm,
    hasConfirmedOverwrite: executor.hasConfirmedOverwrite,
    isDirty,
    panelWidth,
    onSchemaSelect,
    processFile,
    handleImport: executor.handleImport,
    requestClose,
    validationErrors,
    isValidCustomMapping,
    parsedPreviewRows,
    uniqueOperationTypes,
    activeDbOpTypes,
    liveValidationStats,
    handleColumnChange,
  };
}
