import { computed, type Ref } from 'vue';
import type { ColMapping, ColumnConfig, ImportField } from '../../../../services/import/types';
import {
  isFieldRelevantForOpType,
  isFieldRequiredForOpType,
  type LivePreviewResult,
} from '../../../../services/import';

// One pill per mapping variant: merged types get one variant (key = opType);
// split types get one variant per raw file action (key = the raw action string).
export interface MappingVariant {
  opType: string;
  key: string;
  rawAction?: string;
}

// Mapping state of one field for one selected variant.
export interface VariantSlotView {
  key: string;
  opType: string;
  rawAction?: string;
  colId: string | null;
  header: string | null;
  mapping: ColMapping | null;
}

// One live-preview line per selected variant (label only shows in multi-select).
export interface SlotPreviewEntry {
  label: string | null;
  exampleValue: string;
  preview: LivePreviewResult | null;
}

export interface FieldSlotView {
  field: ImportField;
  isRequired: boolean;
  // Unified view when every selected variant agrees on the source column;
  // null + mixed=true when they disagree (multi-select only).
  colId: string | null;
  header: string | null;
  mapping: ColMapping | null;
  mixed: boolean;
  perVariant: VariantSlotView[];
}

// Derived view over columnConfigMap (colId -> typeSpecific[opTypeOrRawAction])
// for the currently selected variants (usually one; several when the user
// Ctrl+clicks pills to map shared columns across types at once).
// Each typeSpecific key holds a list of mappings, so one CSV column can feed
// several DB fields. Writes go to every selected variant's key.
export function useFieldSlots(params: {
  columnConfigMap: Ref<Record<string, ColumnConfig>>;
  uiColumns: Ref<Array<{ id: string; colIdx: number; name: string; label: string }>>;
  importFields: Ref<ImportField[]>;
  operationTypeMappings: Ref<Record<string, string>>;
  selectedVariants: Ref<MappingVariant[]>;
}) {
  const rawsFor = (opType: string) =>
    Object.keys(params.operationTypeMappings.value)
      .filter(raw => params.operationTypeMappings.value[raw] === opType);

  // Split variant: that raw action's mappings only.
  // Merged: opType-keyed mappings plus legacy rawAction-keyed fallbacks.
  const keysToCheck = (variant: MappingVariant) => variant.rawAction
    ? [variant.key]
    : [variant.opType, ...rawsFor(variant.opType)];

  const findMappingFor = (
    variant: MappingVariant,
    fieldKey: string
  ): { colId: string; keyUsed: string; mapping: ColMapping } | null => {
    for (const key of keysToCheck(variant)) {
      for (const [colId, conf] of Object.entries(params.columnConfigMap.value)) {
        const mapping = conf?.typeSpecific?.[key]?.find(m => m.dbKey === fieldKey);
        if (mapping) return { colId, keyUsed: key, mapping };
      }
    }
    return null;
  };

  const primaryVariant = computed(() => params.selectedVariants.value[0] || null);

  // Primary-variant lookup, used by single-variant consumers (config modal, ...).
  const findMapping = (fieldKey: string) =>
    primaryVariant.value ? findMappingFor(primaryVariant.value, fieldKey) : null;

  const selectedOpTypes = computed(() =>
    [...new Set(params.selectedVariants.value.map(v => v.opType))]);

  const slots = computed<FieldSlotView[]>(() => {
    const variants = params.selectedVariants.value;
    const opTypes = selectedOpTypes.value;
    if (!variants.length) return [];
    return params.importFields.value
      // Multi-select shows only the fields shared by every selected type.
      .filter(f => f.key !== 'operation_type' && opTypes.every(t => isFieldRelevantForOpType(f, t)))
      .map(f => {
        const perVariant: VariantSlotView[] = variants.map(v => {
          const found = findMappingFor(v, f.key);
          const col = found ? params.uiColumns.value.find(c => c.id === found.colId) : null;
          return {
            key: v.key,
            opType: v.opType,
            rawAction: v.rawAction,
            colId: found?.colId ?? null,
            header: col?.name ?? null,
            mapping: found?.mapping ?? null,
          };
        });
        const first = perVariant[0];
        const mixed = perVariant.some(pv =>
          pv.colId !== first.colId
          || !!pv.mapping?.formula?.length !== !!first.mapping?.formula?.length
        );
        return {
          field: f,
          isRequired: opTypes.some(t => isFieldRequiredForOpType(f, t)),
          colId: mixed ? null : first.colId,
          header: mixed ? null : first.header,
          mapping: mixed ? null : first.mapping,
          mixed,
          perVariant,
        };
      })
      .sort((a, b) => Number(b.isRequired) - Number(a.isRequired));
  });

  const usedColIds = computed(() => {
    const set = new Set<string>();
    slots.value.forEach(s => s.perVariant.forEach(pv => { if (pv.colId) set.add(pv.colId); }));
    return set;
  });

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
    params.selectedVariants.value.forEach(variant => {
      keysToCheck(variant).forEach(key => {
        Object.values(params.columnConfigMap.value).forEach(conf => {
          if (conf?.typeSpecific?.[key]?.some(m => m.dbKey === fieldKey)) {
            removeEntry(conf, key, fieldKey);
          }
        });
      });
    });
    touch();
  };

  // Drop/assign: the column swaps but each variant's field keeps its own
  // date/enum/enrich settings. Other fields already fed by the target column are
  // untouched — one CSV column can legitimately map to several DB fields.
  // A cross-column formula is intentionally dropped — it referenced other columns.
  const assignColumn = (colId: string, fieldKey: string) => {
    const conf = params.columnConfigMap.value[colId];
    if (!conf) return;

    params.selectedVariants.value.forEach(variant => {
      const previous = findMappingFor(variant, fieldKey);
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
      const list = (conf.typeSpecific[variant.key] ||= []).filter(m => m.dbKey !== fieldKey && m.dbKey !== '');
      list.push(entry);
      conf.typeSpecific[variant.key] = list;
    });
    touch();
  };

  // Persist advanced settings coming back from the config modal — applied to
  // every selected variant, like drops.
  const updateMapping = (fieldKey: string, mapping: ColMapping) => {
    params.selectedVariants.value.forEach(variant => {
      const found = findMappingFor(variant, fieldKey);
      let targetColId = found?.colId ?? null;
      let targetKey = found?.keyUsed ?? variant.key;

      // A pure formula mapping may not have a column yet: anchor it on the first
      // column referenced by the formula.
      if (!targetColId && mapping.formula?.length) {
        const anchorToken = mapping.formula.find(t => 'col' in t) as { col: string } | undefined;
        const anchorCol = anchorToken
          ? params.uiColumns.value.find(c => c.name === anchorToken.col)
          : null;
        if (!anchorCol) return;
        targetColId = anchorCol.id;
        targetKey = variant.key;
      }
      if (!targetColId) return;

      const conf = params.columnConfigMap.value[targetColId];
      if (!conf) return;
      const list = (conf.typeSpecific[targetKey] ||= []).filter(m => m.dbKey !== fieldKey && m.dbKey !== '');
      list.push({ ...mapping, dbKey: fieldKey });
      conf.typeSpecific[targetKey] = list;
    });
    touch();
  };

  return { slots, usedColIds, findMapping, assignColumn, clearField, updateMapping };
}
