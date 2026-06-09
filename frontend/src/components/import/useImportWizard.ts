import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { api } from '../../services/api';
import { useSchemaManagement } from './useSchemaManagement';
import { useWizardMapping } from './useWizardMapping';
import {
  buildCustomMappingPayload as buildCustomMappingPayloadHelper,
  validateLiveStats,
  parsePreviewRows,
  getValidationErrors,
  parseSchemaMappings,
  parseCsvText,
  groupRowsByOpType
} from '../../services/import';

interface Portfolio {
  id: number;
  name: string;
}

export function useImportWizard(props: { portfolio: Portfolio; initialFile?: File | null }, emit: any) {
  // Leverage sub-composables
  const schemaMgmt = useSchemaManagement();

  // UI States
  const importFile = ref<File | null>(null);
  const fileText = ref('');
  const importFileHeaders = ref<string[]>([]);
  const isCustomMapping = ref(false);
  const isImporting = ref(false);
  const importError = ref('');
  const importSuccessSummary = ref<any>(null);

  // Mappings configuration
  const mappingTemplateName = ref('');
  const saveMappingTemplate = ref(false);
  const importDelimiter = ref(',');
  const importDecimalSep = ref('.');

  // Dynamic metadata & row parsing state
  const importFields = ref<any[]>([]);
  const allRawRows = ref<string[][]>([]);
  const currentStep = ref(1);

  // Step 1: Operation type column and value mapping
  const operationTypeColumnIdx = ref<number | null>(null);
  const operationTypeMappings = ref<Record<string, string>>({});

  // Step 2: Column configs
  const columnConfigMap = ref<Record<string, any>>({});
  const uiColumns = ref<Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }>>([]);

  // Confirmations
  const showExitConfirm = ref(false);
  const showOverwriteConfirm = ref(false);
  const hasConfirmedOverwrite = ref(false);

  const isDirty = computed(() => importFile.value !== null);

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
        operationTypeMappings.value = parsed.operationTypeMappings;
        columnConfigMap.value = parsed.columnConfigMap;
        uiColumns.value = parsed.uiColumns;
      }
    }
  };

  const initializeConfigs = () => {
    uiColumns.value = importFileHeaders.value.map((h, idx) => ({ id: `col-${idx}`, colIdx: idx, name: h, label: h }));
    columnConfigMap.value = {};
    uiColumns.value.forEach(col => {
      columnConfigMap.value[col.id] = { global: { dbKey: '' }, typeSpecific: {} };
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
      columnConfigMap.value[col.id] = { global: { dbKey: '' }, typeSpecific: {} };
    });
  };

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

  // Wizard Mapping sub-composable
  const wizardMapping = useWizardMapping(
    uiColumns,
    columnConfigMap,
    importFileHeaders,
    matchingRowsByType,
    matchingRowsByRawAction,
    allRawRows,
    operationTypeMappings
  );

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
        uiColumns.value = parsed.headers.map((h, idx) => ({ id: `col-${idx}`, colIdx: idx, name: h, label: h }));
        allRawRows.value = parsed.rawRows;
        currentStep.value = 1;

        try {
          const detectRes = await api.detectImportFileSchema(parsed.headers);
          if (detectRes.schema_id) {
            schemaMgmt.autodetectedSchemaId.value = detectRes.schema_id;
            schemaMgmt.selectedSchemaId.value = detectRes.schema_id;
            isCustomMapping.value = false;
            onSchemaSelect();
          } else {
            schemaMgmt.autodetectedSchemaId.value = null;
            schemaMgmt.selectedSchemaId.value = null;
            isCustomMapping.value = true;
            initializeConfigs();
          }
        } catch (err: any) {
          console.error('Failed to autodetect schema:', err);
          isCustomMapping.value = true;
          initializeConfigs();
        }
      }
    };
    reader.readAsText(file);
  };

  const handleImport = async () => {
    if (!importFile.value || !props.portfolio.id) return;
    isImporting.value = true;
    importError.value = '';
    importSuccessSummary.value = null;

    try {
      let finalSchemaId = schemaMgmt.selectedSchemaId.value;

      if (isCustomMapping.value && saveMappingTemplate.value && mappingTemplateName.value.trim()) {
        const existingSchema = schemaMgmt.availableSchemas.value.find(
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
              const existingSchema = schemaMgmt.availableSchemas.value.find(
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
            schemaMgmt.loadSchemas();
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
            const existingSchema = schemaMgmt.availableSchemas.value.find(
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

  const handleDeleteTemplateWrapper = async () => {
    const res = await schemaMgmt.handleDeleteTemplate();
    if (res && !res.success) {
      importError.value = res.error || 'Failed to delete template.';
    }
  };

  const requestClose = () => {
    if (isDirty.value && !importSuccessSummary.value) {
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
    selectedSchemaIdString: selectedSchemaIdString,
    showDeleteConfirm: schemaMgmt.showDeleteConfirm,
    isDeletingSchema: schemaMgmt.isDeletingSchema,
    handleDeleteTemplate: handleDeleteTemplateWrapper,

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
    isImporting,
    importError,
    importSuccessSummary,
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
    showOverwriteConfirm,
    hasConfirmedOverwrite,
    isDirty,
    panelWidth,
    onSchemaSelect,
    processFile,
    handleImport,
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
