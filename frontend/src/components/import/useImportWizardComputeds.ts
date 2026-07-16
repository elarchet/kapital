import { computed, type Ref } from 'vue';
import {
  groupRowsByOpType,
  validateLiveStats,
  getValidationErrors,
  isExtraGroupKey,
  baseFieldKey,
  groupIndex,
} from '../../services/import';

export function useImportWizardComputeds(params: {
  importFiles: Ref<File[]>;
  allRawRows: Ref<string[][]>;
  operationTypeColumnIdx: Ref<number | null>;
  operationTypeMappings: Ref<Record<string, string>>;
  importFields: Ref<any[]>;
  importDelimiter: Ref<string>;
  importDecimalSep: Ref<string>;
  columnConfigMap: Ref<Record<string, any>>;
  uiColumns: Ref<any[]>;
  uiRowsOrder?: Ref<string[]>;
  enrichedNames: Ref<Record<string, string>>;
  splitOpTypes?: Ref<string[]>;
}) {
  const uniqueOperationTypes = computed(() => {
    if (params.operationTypeColumnIdx.value === null) return [];
    const uniqueSet = new Set<string>();
    params.allRawRows.value.forEach(row => {
      const val = row[params.operationTypeColumnIdx.value!];
      if (val && val.trim()) uniqueSet.add(val.trim());
    });
    
    let baseOrder = Array.from(uniqueSet);
    if (params.uiRowsOrder && params.uiRowsOrder.value && params.uiRowsOrder.value.length > 0) {
      const customOrderMap = new Map();
      params.uiRowsOrder.value.forEach((v, i) => customOrderMap.set(v, i));
      baseOrder.sort((a, b) => {
        const aIndex = customOrderMap.has(a) ? customOrderMap.get(a) : Infinity;
        const bIndex = customOrderMap.has(b) ? customOrderMap.get(b) : Infinity;
        return aIndex - bIndex;
      });
    }
    return baseOrder;
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

  // Static metadata fields plus generated fields for mapped extra fee/tax groups
  // (suffixed db keys like fee_amount__2), so their values get validated too.
  const effectiveImportFields = computed(() => {
    const mappedExtraKeys = new Set<string>();
    Object.values(params.columnConfigMap.value || {}).forEach((conf: any) => {
      Object.values(conf?.typeSpecific || {}).forEach((list: any) => {
        (Array.isArray(list) ? list : []).forEach((m: any) => {
          if (m?.dbKey && isExtraGroupKey(m.dbKey)) mappedExtraKeys.add(m.dbKey);
        });
      });
    });
    if (!mappedExtraKeys.size) return params.importFields.value;
    const extra: any[] = [];
    mappedExtraKeys.forEach(key => {
      const base = params.importFields.value.find((f: any) => f.key === baseFieldKey(key));
      if (base) extra.push({ ...base, key, label: `${base.label} (${groupIndex(key)})`, required_for: undefined });
    });
    return [...params.importFields.value, ...extra];
  });

  const liveValidationStats = computed(() => {
    return validateLiveStats({
      importFields: effectiveImportFields.value,
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
      importFile: params.importFiles.value[0] ?? null,
      operationTypeColumnIdx: params.operationTypeColumnIdx.value,
      uniqueOperationTypes: uniqueOperationTypes.value,
      operationTypeMappings: params.operationTypeMappings.value,
      activeDbOpTypes: activeDbOpTypes.value,
      importFields: params.importFields.value,
      columnConfigMap: params.columnConfigMap.value,
      uiColumns: params.uiColumns.value,
      liveValidationStats: liveValidationStats.value,
      splitTypes: params.splitOpTypes?.value || []
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
