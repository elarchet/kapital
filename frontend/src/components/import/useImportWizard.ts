import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { api } from '../../services/api';
import { useSchemaManagement } from './useSchemaManagement';
import { useWizardMapping } from './useWizardMapping';
import { useImportExecutor } from './useImportExecutor';
import { useImportPreview } from './useImportPreview';
import { useImportWizardComputeds } from './useImportWizardComputeds';
import { useImportFileLoading } from './useImportFileLoading';
import {
  buildCustomMappingPayload as buildCustomMappingPayloadHelper,
  parseSchemaMappings,
  DEFAULT_INSTITUTION_KEY
} from '../../services/import';
import type { OpTypeSettings } from '../../services/import/types';

interface Portfolio {
  id: number;
  name: string;
}

export function useImportWizard(props: { portfolio: Portfolio; initialFiles?: File[] | null }, emit: any) {
  // Shared state refs. Several files import as one batch: rows are merged
  // client-side for the wizard, and the backend dedups across files.
  const importFiles = ref<File[]>([]);
  const importFileHeaders = ref<string[]>([]);
  const allRawRows = ref<string[][]>([]);
  // Parallel to allRawRows: source file name of each row (for the raw-rows preview).
  const rawRowSources = ref<string[]>([]);

  const isCustomMapping = ref(false);
  const mappingTemplateName = ref('');
  const saveMappingTemplate = ref(false);
  const importDelimiter = ref(',');
  const importDecimalSep = ref('.');
  const institutionKey = ref(DEFAULT_INSTITUTION_KEY);

  const importFields = ref<any[]>([]);
  const currentStep = ref(1);

  const operationTypeColumnIdx = ref<number | null>(null);
  const operationTypeMappings = ref<Record<string, string>>({});
  // DB op types whose raw actions are mapped separately (one variant per raw value).
  const splitOpTypes = ref<string[]>([]);
  // Session-side fee/tax group counts per mapping-variant key (>= 1). Groups with
  // mapped columns are re-derived from columnConfigMap; this only keeps still-empty
  // groups alive across step navigation.
  const feeTaxGroupCounts = ref<Record<string, { fee: number; tax: number }>>({});

  const columnConfigMap = ref<Record<string, any>>({});
  const uiColumns = ref<Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean; width?: number }>>([]);
  const uiRowsOrder = ref<string[]>([]);
  const opTypeSettings = ref<Record<string, OpTypeSettings>>({});

  const showExitConfirm = ref(false);
  const isDirty = computed(() => importFiles.value.length > 0);



  const handleColumnChange = () => {
    operationTypeMappings.value = {};
    splitOpTypes.value = [];
    feeTaxGroupCounts.value = {};
    uiColumns.value = importFileHeaders.value.map((h, idx) => ({ id: `col-${idx}`, colIdx: idx, name: h, label: h, width: 180 }));
    uiRowsOrder.value = [];
    columnConfigMap.value = {};
    opTypeSettings.value = {};
    uiColumns.value.forEach(col => {
      columnConfigMap.value[col.id] = { typeSpecific: {} };
    });
  };

  const onSchemaSelect = () => {
    if (schemaMgmt.selectedSchemaId.value === -1) {
      isCustomMapping.value = true;
      schemaMgmt.selectedSchemaId.value = null;
      handleColumnChange();
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
        institutionKey.value = schema.institution_key || 'custom';

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
        uiRowsOrder.value = parsed.uiRowsOrder || [];
        opTypeSettings.value = parsed.opTypeSettings || {};
        splitOpTypes.value = parsed.splitTypes || [];
        // Groups with mapped columns are re-derived from columnConfigMap.
        feeTaxGroupCounts.value = {};
      } else {
        isCustomMapping.value = true;
        handleColumnChange();
      }
    }
  };

  // Previews & Enrichment Pipeline
  const enrichedNames = ref<Record<string, string>>({});

  // Computeds
  const {
    uniqueOperationTypes,
    activeDbOpTypes,
    matchingRowsByRawAction,
    matchingRowsByType,
    liveValidationStats,
    validationErrors,
    isValidCustomMapping
  } = useImportWizardComputeds({
    importFiles,
    allRawRows,
    operationTypeColumnIdx,
    operationTypeMappings,
    importFields,
    importDelimiter,
    importDecimalSep,
    columnConfigMap,
    uiColumns,
    uiRowsOrder,
    enrichedNames,
    splitOpTypes
  });

  const buildCustomMappingPayload = () => {
    return buildCustomMappingPayloadHelper({
      operationTypeColumnIdx: operationTypeColumnIdx.value,
      importFileHeaders: importFileHeaders.value,
      columnConfigMap: columnConfigMap.value,
      uiColumns: uiColumns.value,
      operationTypeMappings: operationTypeMappings.value,
      importFields: importFields.value,
      uiRowsOrder: uiRowsOrder.value,
      institutionKey: institutionKey.value,
      opTypeSettings: opTypeSettings.value,
      splitOpTypes: splitOpTypes.value
    });
  };

  // Sub-composables orchestration
  const schemaMgmt = useSchemaManagement();

  const wizardMapping = useWizardMapping(
    matchingRowsByRawAction,
    operationTypeMappings,
    uniqueOperationTypes,
    columnConfigMap,
    splitOpTypes
  );

  const { parsedPreviewRows } = useImportPreview({
    allRawRows,
    importDecimalSep,
    operationTypeColumnIdx,
    operationTypeMappings,
    columnConfigMap,
    uiColumns,
    importFields,
    exampleTransactions: computed(() => wizardMapping.exampleTransactions.value),
    enrichedNames
  });

  const executor = useImportExecutor({
    portfolio: props.portfolio,
    importFiles,
    selectedSchemaId: schemaMgmt.selectedSchemaId,
    availableSchemas: schemaMgmt.availableSchemas,
    loadSchemas: schemaMgmt.loadSchemas,
    isCustomMapping,
    saveMappingTemplate,
    mappingTemplateName,
    isValidCustomMapping,
    importDelimiter,
    importDecimalSep,
    institutionKey,
    buildCustomMappingPayload,
    initializeConfigs: handleColumnChange,
    schemaDeleteTemplate: schemaMgmt.handleDeleteTemplate,
    emit,
  });

  const { processFiles } = useImportFileLoading({
    importFiles,
    importFileHeaders,
    allRawRows,
    rawRowSources,
    uiColumns,
    columnConfigMap,
    importDelimiter,
    currentStep,
    isCustomMapping,
    importError: executor.importError,
    autodetectedSchemaId: schemaMgmt.autodetectedSchemaId,
    selectedSchemaId: schemaMgmt.selectedSchemaId,
    initializeConfigs: handleColumnChange,
  });

  // Watchers & Life Cycle
  const requestClose = () => {
    if (isDirty.value) {
      showExitConfirm.value = true;
    } else {
      emit('close');
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
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

  watch(() => props.initialFiles, (newFiles) => {
    if (newFiles?.length) processFiles(newFiles);
  }, { immediate: true });

  const panelWidth = ref(550);
  watch(
    () => importFiles.value.length,
    (count) => {
      panelWidth.value = count ? Math.min(1400, window.innerWidth * 0.85) : 550;
    },
    { immediate: true }
  );

  watch(() => schemaMgmt.selectedSchemaId.value, () => {
    onSchemaSelect();
  });

  return {
    // Composable delegates
    availableSchemas: schemaMgmt.availableSchemas,
    selectedSchemaId: schemaMgmt.selectedSchemaId,
    autodetectedSchemaId: schemaMgmt.autodetectedSchemaId,
    selectedSchema: schemaMgmt.selectedSchema,
    selectedSchemaIdString: schemaMgmt.selectedSchemaIdString,
    showDeleteConfirm: schemaMgmt.showDeleteConfirm,
    isDeletingSchema: schemaMgmt.isDeletingSchema,
    handleDeleteTemplate: executor.handleDeleteTemplateWrapper,

    exampleTransactions: wizardMapping.exampleTransactions,
    nextExampleForType: wizardMapping.nextExampleForType,
    prevExampleForType: wizardMapping.prevExampleForType,
    handleUpdateOpTypeMapping: wizardMapping.handleUpdateOpTypeMapping,
    toggleSplitType: wizardMapping.toggleSplitType,

    // Re-assign to refresh identity after nested mutations from the mapping board.
    touchColumnConfig: () => {
      columnConfigMap.value = { ...columnConfigMap.value };
    },
    updateOpTypeSettings: (payload: { opType: string; settings: OpTypeSettings }) => {
      opTypeSettings.value = { ...opTypeSettings.value, [payload.opType]: payload.settings };
    },
    updateFeeTaxGroupCount: (payload: { key: string; kind: 'fee' | 'tax'; count: number }) => {
      const current = feeTaxGroupCounts.value[payload.key] || { fee: 1, tax: 1 };
      feeTaxGroupCounts.value = {
        ...feeTaxGroupCounts.value,
        [payload.key]: { ...current, [payload.kind]: Math.max(1, payload.count) },
      };
    },

    // Local states & computed
    importFiles,
    importFileHeaders,
    isCustomMapping,
    isImporting: executor.isImporting,
    importError: executor.importError,
    mappingTemplateName,
    saveMappingTemplate,
    importDelimiter,
    importDecimalSep,
    institutionKey,
    importFields,
    allRawRows,
    rawRowSources,
    currentStep,
    operationTypeColumnIdx,
    operationTypeMappings,
    splitOpTypes,
    feeTaxGroupCounts,
    columnConfigMap,
    uiColumns,
    opTypeSettings,
    showExitConfirm,
    showOverwriteConfirm: executor.showOverwriteConfirm,
    hasConfirmedOverwrite: executor.hasConfirmedOverwrite,
    isDirty,
    panelWidth,
    onSchemaSelect,
    processFiles,
    handleImport: executor.handleImport,
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
    handleColumnChange,
  };
}
