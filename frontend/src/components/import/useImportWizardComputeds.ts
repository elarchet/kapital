import { computed, type Ref } from 'vue';
import {
  groupRowsByOpType,
  validateLiveStats,
  getValidationErrors,
} from '../../services/import';

export function useImportWizardComputeds(params: {
  importFile: Ref<File | null>;
  allRawRows: Ref<string[][]>;
  operationTypeColumnIdx: Ref<number | null>;
  operationTypeMappings: Ref<Record<string, string>>;
  importFields: Ref<any[]>;
  importDelimiter: Ref<string>;
  importDecimalSep: Ref<string>;
  columnConfigMap: Ref<Record<string, any>>;
  uiColumns: Ref<any[]>;
  enrichedNames: Ref<Record<string, string>>;
}) {
  const uniqueOperationTypes = computed(() => {
    if (params.operationTypeColumnIdx.value === null) return [];
    const uniqueSet = new Set<string>();
    params.allRawRows.value.forEach(row => {
      const val = row[params.operationTypeColumnIdx.value!];
      if (val && val.trim()) uniqueSet.add(val.trim());
    });
    return Array.from(uniqueSet);
  });

  const activeDbOpTypes = computed(() => {
    const types = new Set<string>();
    Object.values(params.operationTypeMappings.value).forEach(v => {
      if (v) types.add(v);
    });
    return Array.from(types);
  });

  const matchingRowsByRawAction = computed(() => {
    const result: Record<string, { csvRow: string[]; rowIdx: number }[]> = {};
    if (params.operationTypeColumnIdx.value === null) return result;
    params.allRawRows.value.forEach((row, idx) => {
      const rawAction = row[params.operationTypeColumnIdx.value!];
      if (rawAction) {
        const trimmed = rawAction.trim();
        if (!result[trimmed]) result[trimmed] = [];
        result[trimmed].push({ csvRow: row, rowIdx: idx });
      }
    });
    return result;
  });

  const matchingRowsByType = computed(() => {
    return groupRowsByOpType(params.allRawRows.value, params.operationTypeColumnIdx.value, params.operationTypeMappings.value);
  });

  const liveValidationStats = computed(() => {
    return validateLiveStats({
      importFields: params.importFields.value,
      importDelimiter: params.importDelimiter.value,
      importDecimalSep: params.importDecimalSep.value,
      columnConfigMap: params.columnConfigMap.value,
      uiColumns: params.uiColumns.value,
      activeDbOpTypes: activeDbOpTypes.value,
      allRawRows: params.allRawRows.value,
      operationTypeColumnIdx: params.operationTypeColumnIdx.value,
      operationTypeMappings: params.operationTypeMappings.value,
      enrichedNames: params.enrichedNames.value
    });
  });

  const validationErrors = computed(() => {
    return getValidationErrors({
      importFile: params.importFile.value,
      operationTypeColumnIdx: params.operationTypeColumnIdx.value,
      uniqueOperationTypes: uniqueOperationTypes.value,
      operationTypeMappings: params.operationTypeMappings.value,
      activeDbOpTypes: activeDbOpTypes.value,
      importFields: params.importFields.value,
      columnConfigMap: params.columnConfigMap.value,
      uiColumns: params.uiColumns.value,
      liveValidationStats: liveValidationStats.value
    });
  });

  const isValidCustomMapping = computed(() => validationErrors.value.length === 0);

  return {
    uniqueOperationTypes,
    activeDbOpTypes,
    matchingRowsByRawAction,
    matchingRowsByType,
    liveValidationStats,
    validationErrors,
    isValidCustomMapping
  };
}
