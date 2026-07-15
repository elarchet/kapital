import { computed, type Ref } from 'vue';
import type { ColMapping, ImportField } from '../../../../services/import/types';
import {
  isFieldRelevantForOpType,
  isFieldRequiredForOpType,
} from '../../../../services/import';

export interface FieldSlotView {
  field: ImportField;
  isRequired: boolean;
  colId: string | null;
  header: string | null;
  mapping: ColMapping | null;
}

// Derived per-op-type view over columnConfigMap (colId -> typeSpecific[opTypeOrRawAction]).
// New mappings are written keyed by the DB op type; legacy templates keyed by raw
// action strings still resolve through the rawAction fallback lookups.
export function useFieldSlots(params: {
  columnConfigMap: Ref<Record<string, { typeSpecific: Record<string, ColMapping> }>>;
  uiColumns: Ref<Array<{ id: string; colIdx: number; name: string; label: string }>>;
  importFields: Ref<ImportField[]>;
  operationTypeMappings: Ref<Record<string, string>>;
  selectedOpType: Ref<string>;
}) {
  const rawActionsForSelected = computed(() =>
    Object.keys(params.operationTypeMappings.value)
      .filter(raw => params.operationTypeMappings.value[raw] === params.selectedOpType.value)
  );

  const keysToCheck = () => [params.selectedOpType.value, ...rawActionsForSelected.value];

  const findMapping = (fieldKey: string): { colId: string; keyUsed: string; mapping: ColMapping } | null => {
    for (const key of keysToCheck()) {
      for (const [colId, conf] of Object.entries(params.columnConfigMap.value)) {
        const mapping = conf?.typeSpecific?.[key];
        if (mapping?.dbKey === fieldKey) return { colId, keyUsed: key, mapping };
      }
    }
    return null;
  };

  const slots = computed<FieldSlotView[]>(() => {
    const opType = params.selectedOpType.value;
    return params.importFields.value
      .filter(f => f.key !== 'operation_type' && isFieldRelevantForOpType(f, opType))
      .map(f => {
        const found = findMapping(f.key);
        const col = found ? params.uiColumns.value.find(c => c.id === found.colId) : null;
        return {
          field: f,
          isRequired: isFieldRequiredForOpType(f, opType),
          colId: found?.colId ?? null,
          header: col?.name ?? null,
          mapping: found?.mapping ?? null,
        };
      })
      .sort((a, b) => Number(b.isRequired) - Number(a.isRequired));
  });

  const usedColIds = computed(() => new Set(slots.value.map(s => s.colId).filter(Boolean) as string[]));

  const touch = () => {
    params.columnConfigMap.value = { ...params.columnConfigMap.value };
  };

  const clearField = (fieldKey: string) => {
    keysToCheck().forEach(key => {
      Object.values(params.columnConfigMap.value).forEach(conf => {
        if (conf?.typeSpecific?.[key]?.dbKey === fieldKey) {
          conf.typeSpecific[key] = { dbKey: '' };
        }
      });
    });
    touch();
  };

  // Drop/assign: the column swaps but the field keeps its date/enum/enrich settings.
  // A cross-column formula is intentionally dropped — it referenced other columns.
  const assignColumn = (colId: string, fieldKey: string) => {
    const opType = params.selectedOpType.value;
    const conf = params.columnConfigMap.value[colId];
    if (!conf) return;

    const previous = findMapping(fieldKey);
    if (previous && previous.colId !== colId) {
      params.columnConfigMap.value[previous.colId].typeSpecific[previous.keyUsed] = { dbKey: '' };
    }

    const preserved = previous?.mapping;
    conf.typeSpecific[opType] = {
      dbKey: fieldKey,
      divisor: preserved?.divisor,
      multiplier: preserved?.multiplier,
      enumMappings: preserved?.enumMappings,
      dateFormat: preserved?.dateFormat,
      enrichAssetNames: preserved?.enrichAssetNames,
      enrichTransactionIds: preserved?.enrichTransactionIds,
    };
    touch();
  };

  // Persist advanced settings coming back from the config modal.
  const updateMapping = (fieldKey: string, mapping: ColMapping) => {
    const found = findMapping(fieldKey);
    let targetColId = found?.colId ?? null;
    let targetKey = found?.keyUsed ?? params.selectedOpType.value;

    // A pure formula mapping may not have a column yet: anchor it on the first
    // column referenced by the formula.
    if (!targetColId && mapping.formula?.length) {
      const anchorToken = mapping.formula.find(t => 'col' in t) as { col: string } | undefined;
      const anchorCol = anchorToken
        ? params.uiColumns.value.find(c => c.name === anchorToken.col)
        : null;
      if (!anchorCol) return;
      targetColId = anchorCol.id;
      targetKey = params.selectedOpType.value;
    }
    if (!targetColId) return;

    const conf = params.columnConfigMap.value[targetColId];
    if (!conf) return;
    conf.typeSpecific[targetKey] = { ...mapping, dbKey: fieldKey };
    touch();
  };

  return { slots, usedColIds, rawActionsForSelected, findMapping, assignColumn, clearField, updateMapping };
}
