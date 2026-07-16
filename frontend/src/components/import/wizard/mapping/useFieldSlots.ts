import { computed, type Ref } from 'vue';
import type { ColMapping, ColumnConfig, ImportField } from '../../../../services/import/types';
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
// Each typeSpecific key holds a list of mappings, so one CSV column can feed several
// DB fields. New mappings are written keyed by the DB op type; legacy templates keyed
// by raw action strings still resolve through the rawAction fallback lookups.
export function useFieldSlots(params: {
  columnConfigMap: Ref<Record<string, ColumnConfig>>;
  uiColumns: Ref<Array<{ id: string; colIdx: number; name: string; label: string }>>;
  importFields: Ref<ImportField[]>;
  operationTypeMappings: Ref<Record<string, string>>;
  selectedOpType: Ref<string>;
  // Mapping key writes go to: the opType for merged types, the raw action string
  // for split-type variants. Defaults to the opType when not provided.
  selectedKey?: Ref<string>;
}) {
  const rawActionsForSelected = computed(() =>
    Object.keys(params.operationTypeMappings.value)
      .filter(raw => params.operationTypeMappings.value[raw] === params.selectedOpType.value)
  );

  const writeKey = () => params.selectedKey?.value || params.selectedOpType.value;

  // Split variant (writeKey != opType): that raw action's mappings only.
  // Merged: opType-keyed mappings plus legacy rawAction-keyed fallbacks.
  const keysToCheck = () => writeKey() !== params.selectedOpType.value
    ? [writeKey()]
    : [params.selectedOpType.value, ...rawActionsForSelected.value];

  const findMapping = (fieldKey: string): { colId: string; keyUsed: string; mapping: ColMapping } | null => {
    for (const key of keysToCheck()) {
      for (const [colId, conf] of Object.entries(params.columnConfigMap.value)) {
        const mapping = conf?.typeSpecific?.[key]?.find(m => m.dbKey === fieldKey);
        if (mapping) return { colId, keyUsed: key, mapping };
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

  // Remove the entry for fieldKey from one column's list; keep an explicit-clear
  // sentinel when nothing else remains so the clear survives a save/reload cycle.
  const removeEntry = (conf: ColumnConfig, key: string, fieldKey: string) => {
    const list = conf?.typeSpecific?.[key];
    if (!list) return;
    const filtered = list.filter(m => m.dbKey !== fieldKey);
    conf.typeSpecific[key] = filtered.length ? filtered : [{ dbKey: '' }];
  };

  const clearField = (fieldKey: string) => {
    keysToCheck().forEach(key => {
      Object.values(params.columnConfigMap.value).forEach(conf => {
        if (conf?.typeSpecific?.[key]?.some(m => m.dbKey === fieldKey)) {
          removeEntry(conf, key, fieldKey);
        }
      });
    });
    touch();
  };

  // Drop/assign: the column swaps but the field keeps its date/enum/enrich settings.
  // Other fields already fed by the target column are untouched — one CSV column can
  // legitimately map to several DB fields.
  // A cross-column formula is intentionally dropped — it referenced other columns.
  const assignColumn = (colId: string, fieldKey: string) => {
    const key = writeKey();
    const conf = params.columnConfigMap.value[colId];
    if (!conf) return;

    const previous = findMapping(fieldKey);
    if (previous && previous.colId !== colId) {
      removeEntry(params.columnConfigMap.value[previous.colId], previous.keyUsed, fieldKey);
    }

    const preserved = previous?.mapping;
    const entry: ColMapping = {
      dbKey: fieldKey,
      divisor: preserved?.divisor,
      multiplier: preserved?.multiplier,
      enumMappings: preserved?.enumMappings,
      dateFormat: preserved?.dateFormat,
      enrichAssetNames: preserved?.enrichAssetNames,
      enrichTransactionIds: preserved?.enrichTransactionIds,
    };
    const list = (conf.typeSpecific[key] ||= []).filter(m => m.dbKey !== fieldKey && m.dbKey !== '');
    list.push(entry);
    conf.typeSpecific[key] = list;
    touch();
  };

  // Persist advanced settings coming back from the config modal.
  const updateMapping = (fieldKey: string, mapping: ColMapping) => {
    const found = findMapping(fieldKey);
    let targetColId = found?.colId ?? null;
    let targetKey = found?.keyUsed ?? writeKey();

    // A pure formula mapping may not have a column yet: anchor it on the first
    // column referenced by the formula.
    if (!targetColId && mapping.formula?.length) {
      const anchorToken = mapping.formula.find(t => 'col' in t) as { col: string } | undefined;
      const anchorCol = anchorToken
        ? params.uiColumns.value.find(c => c.name === anchorToken.col)
        : null;
      if (!anchorCol) return;
      targetColId = anchorCol.id;
      targetKey = writeKey();
    }
    if (!targetColId) return;

    const conf = params.columnConfigMap.value[targetColId];
    if (!conf) return;
    const list = (conf.typeSpecific[targetKey] ||= []).filter(m => m.dbKey !== fieldKey && m.dbKey !== '');
    list.push({ ...mapping, dbKey: fieldKey });
    conf.typeSpecific[targetKey] = list;
    touch();
  };

  return { slots, usedColIds, rawActionsForSelected, findMapping, assignColumn, clearField, updateMapping };
}
