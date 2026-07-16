import type { ColMapping, ColumnConfig, FormulaToken, OpTypeSettings } from './types';

export function getEnumMappingsForField(dbKey: string, mappings: any): Record<string, string> {
  const result: Record<string, string> = {};
  const enum_mappings = mappings.enum_mappings?.[dbKey] || {};
  Object.entries(enum_mappings).forEach(([targetEnum, rawVals]: [string, any]) => {
    if (Array.isArray(rawVals)) {
      rawVals.forEach(val => {
        result[val] = targetEnum;
      });
    }
  });
  return result;
}

export function buildCustomMappingPayload(params: {
  operationTypeColumnIdx: number | null;
  importFileHeaders: string[];
  columnConfigMap: Record<string, ColumnConfig>;
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean; width?: number }>;
  operationTypeMappings: Record<string, string>;
  importFields: any[];
  uiRowsOrder?: string[];
  institutionKey?: string;
  opTypeSettings?: Record<string, OpTypeSettings>;
  splitOpTypes?: string[];
}) {
  const transformations: Record<string, any> = {};
  const enum_mappings: Record<string, Record<string, string[]>> = {};
  const date_formats: Record<string, any> = {};
  const formulas: Record<string, Record<string, FormulaToken[]>> = {};

  const dbKeyToCol = new Map<string, { typeSpecific?: Record<string, string> }>();
  params.importFields.forEach(f => { dbKeyToCol.set(f.key, {}); });

  // Collect explicitly-cleared type-specific entries (dbKey = '') so they survive a
  // save/reload cycle and the per-row clear is not lost.
  // Key = CSV header name, value = rawAction opTypes that were explicitly cleared.
  const cleared_type_specifics: Record<string, string[]> = {};
  const enrich_asset_names: Record<string, string> = {};
  const enrich_transaction_ids: Record<string, string> = {};

  Object.entries(params.columnConfigMap).forEach(([colId, conf]) => {
    const col = params.uiColumns.find(c => c.id === colId);
    if (!col) return;
    const headerName = params.importFileHeaders[col.colIdx];

    Object.entries(conf.typeSpecific).forEach(([opType, mappingList]) => {
      (mappingList || []).forEach(specificConf => {
      if (specificConf.dbKey === 'name' && specificConf.enrichAssetNames) {
        enrich_asset_names[opType] = specificConf.enrichAssetNames;
      }
      if (specificConf.dbKey === 'transaction_id' && specificConf.enrichTransactionIds) {
        enrich_transaction_ids[opType] = specificConf.enrichTransactionIds;
      }

      if (specificConf.dbKey) {
        const entry = dbKeyToCol.get(specificConf.dbKey) || {};
        if (!entry.typeSpecific) entry.typeSpecific = {};
        entry.typeSpecific[opType] = headerName;
        dbKeyToCol.set(specificConf.dbKey, entry);

        if (specificConf.divisor || specificConf.multiplier) {
          if (!transformations[specificConf.dbKey]) transformations[specificConf.dbKey] = {};
          transformations[specificConf.dbKey][opType] = {
            divisor: specificConf.divisor,
            multiplier: specificConf.multiplier
          };
        }

        if (specificConf.formula?.length) {
          if (!formulas[specificConf.dbKey]) formulas[specificConf.dbKey] = {};
          formulas[specificConf.dbKey][opType] = specificConf.formula;
        }

        if (specificConf.dateFormat && specificConf.dateFormat !== 'auto') {
          if (!date_formats[specificConf.dbKey]) date_formats[specificConf.dbKey] = {};
          date_formats[specificConf.dbKey][opType] = specificConf.dateFormat;
        }

        if (specificConf.enumMappings) {
          const dbKey = specificConf.dbKey;
          if (!enum_mappings[dbKey]) enum_mappings[dbKey] = {};
          Object.entries(specificConf.enumMappings).forEach(([rawVal, targetVal]) => {
            if (targetVal) {
              if (!enum_mappings[dbKey][targetVal]) enum_mappings[dbKey][targetVal] = [];
              enum_mappings[dbKey][targetVal].push(rawVal);
            }
          });
        }
      } else {
        // dbKey is empty → explicitly cleared row; persist so the parser can restore it.
        if (!cleared_type_specifics[headerName]) cleared_type_specifics[headerName] = [];
        if (!cleared_type_specifics[headerName].includes(opType)) {
          cleared_type_specifics[headerName].push(opType);
        }
      }
      });
    });
  });

  const finalColumns: Record<string, any> = {};
  dbKeyToCol.forEach((entry, dbKey) => {
    if (entry.typeSpecific && Object.keys(entry.typeSpecific).length > 0) {
      finalColumns[dbKey] = { ...entry.typeSpecific };
    }
  });

  const type_mappings: Record<string, string[]> = {};
  const opField = params.importFields.find(f => f.key === 'operation_type');
  if (opField?.enum_values) {
    opField.enum_values.forEach((v: string) => { type_mappings[v] = []; });
  }
  Object.entries(params.operationTypeMappings).forEach(([rawVal, targetVal]) => {
    if (targetVal) {
      if (!type_mappings[targetVal]) type_mappings[targetVal] = [];
      type_mappings[targetVal].push(rawVal);
    }
  });

  // Per-op-type settings win over the legacy per-mapping enrich option: auto IDs
  // must be configurable even when no transaction_id column exists (Fortuneo).
  const hash_columns: Record<string, string[]> = {};
  Object.entries(params.opTypeSettings || {}).forEach(([opType, settings]) => {
    if (settings?.autoTransactionId) {
      enrich_transaction_ids[opType] = settings.autoTransactionId;
    }
    if (settings?.hashColumns?.length) {
      hash_columns[opType] = settings.hashColumns;
    }
  });

  return {
    operation_type_column: params.operationTypeColumnIdx !== null
      ? params.importFileHeaders[params.operationTypeColumnIdx]
      : null,
    institution_key: params.institutionKey || 'custom',
    columns: finalColumns,
    type_mappings,
    enum_mappings,
    transformations,
    date_formats,
    formulas,
    enrich_asset_names,
    enrich_transaction_ids,
    ...(Object.keys(hash_columns).length > 0 ? { hash_columns } : {}),
    // Ignored by the backend (rawAction-keyed columns already win over opType keys);
    // persisted so the wizard restores the split/merged choice per DB type.
    ...(params.splitOpTypes?.length ? { split_types: params.splitOpTypes } : {}),
    ui_columns: params.uiColumns,
    ui_rows_order: params.uiRowsOrder || [],
    ...(Object.keys(cleared_type_specifics).length > 0 ? { cleared_type_specifics } : {})
  };
}

export function parseSchemaMappings(
  mappingsJson: string,
  importFileHeaders: string[]
): {
  operationTypeColumnIdx: number | null;
  operationTypeMappings: Record<string, string>;
  columnConfigMap: Record<string, ColumnConfig>;
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean; width?: number }>;
  uiRowsOrder?: string[];
  opTypeSettings: Record<string, OpTypeSettings>;
  splitTypes: string[];
} {
  let operationTypeColumnIdx: number | null = null;
  const operationTypeMappings: Record<string, string> = {};
  const columnConfigMap: Record<string, ColumnConfig> = {};
  const uiColumns: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean; width?: number }> = [];
  let uiRowsOrder: string[] = [];
  const opTypeSettings: Record<string, OpTypeSettings> = {};
  let splitTypes: string[] = [];

  let mappings: any = {};
  try {
    mappings = JSON.parse(mappingsJson);
  } catch (e) { }

  if (Array.isArray(mappings.split_types)) {
    splitTypes = mappings.split_types.filter((t: any) => typeof t === 'string');
  }

  if (mappings.ui_columns && Array.isArray(mappings.ui_columns) && mappings.ui_columns.length > 0) {
    // Legacy templates carried duplicate "(Copy)" columns because one column could
    // only feed one field; mappings now stack per column, so fold duplicates away.
    uiColumns.push(...mappings.ui_columns.filter((c: any) => !c.isDuplicate));
    uiColumns.forEach(c => {
      columnConfigMap[c.id] = { typeSpecific: {} };
    });
  } else {
    importFileHeaders.forEach((h, idx) => {
      const colId = `col-${idx}`;
      uiColumns.push({ id: colId, colIdx: idx, name: h, label: h, width: 180 });
      columnConfigMap[colId] = { typeSpecific: {} };
    });
  }

  if (mappings.ui_rows_order && Array.isArray(mappings.ui_rows_order)) {
    uiRowsOrder = mappings.ui_rows_order;
  }

  const getColIdForMapping = (idx: number): string | null =>
    uiColumns.find(col => col.colIdx === idx && columnConfigMap[col.id])?.id ?? null;

  const pushMapping = (colId: string, key: string, mapping: ColMapping) => {
    const list = (columnConfigMap[colId].typeSpecific[key] ||= []);
    const existingIdx = list.findIndex(m => m.dbKey === mapping.dbKey);
    if (existingIdx >= 0) list[existingIdx] = mapping;
    else list.push(mapping);
  };

  try {
    const cols = mappings.columns || {};
    const dateFormats = mappings.date_formats || {};

    // 1. Operation type column
    const opTypeHeader = mappings.operation_type_column || cols.operation_type;
    if (opTypeHeader) {
      const idx = importFileHeaders.indexOf(opTypeHeader);
      if (idx >= 0) operationTypeColumnIdx = idx;
    }

    // 2. Operation type value mappings
    const op_mappings = mappings.enum_mappings?.operation_type || mappings.type_mappings || {};
    Object.entries(op_mappings).forEach(([targetEnum, rawVals]: [string, any]) => {
      if (Array.isArray(rawVals)) {
        rawVals.forEach(val => { operationTypeMappings[val.trim()] = targetEnum; });
      }
    });

    // 3. Column mappings — only object format (per-opType) is supported.
    //    String-value (global) format is not supported; it was a legacy concept.
    Object.entries(cols).forEach(([dbKey, val]) => {
      if (dbKey === 'operation_type') return;
      if (!val || typeof val !== 'object') return;

      const valObj = val as Record<string, string>;
      Object.entries(valObj).forEach(([opType, headerName]) => {
        const idx = importFileHeaders.indexOf(headerName);
        if (idx < 0) return;
        const colId = getColIdForMapping(idx);
        if (!colId) return;
        const dfVal = dateFormats[dbKey];
        const specDateFormat = !dfVal
          ? 'auto'
          : typeof dfVal === 'string' ? dfVal : (dfVal[opType] || 'auto');

        const formulaVal = mappings.formulas?.[dbKey];
        const formulaTokens = Array.isArray(formulaVal) ? formulaVal : formulaVal?.[opType];

        const specConf: ColMapping = {
          dbKey,
          divisor: mappings.transformations?.[dbKey]?.[opType]?.divisor || mappings.transformations?.[dbKey]?.divisor,
          multiplier: mappings.transformations?.[dbKey]?.[opType]?.multiplier || mappings.transformations?.[dbKey]?.multiplier,
          enumMappings: getEnumMappingsForField(dbKey, mappings),
          dateFormat: specDateFormat,
          ...(Array.isArray(formulaTokens) && formulaTokens.length > 0 ? { formula: formulaTokens } : {})
        };

        if (dbKey === 'name') {
          specConf.enrichAssetNames = mappings.enrich_asset_names?.[opType] || 'when_empty';
        }
        if (dbKey === 'transaction_id') {
          specConf.enrichTransactionIds = mappings.enrich_transaction_ids?.[opType] || 'when_empty';
        }

        pushMapping(colId, opType, specConf);
      });
    });

    // 4. Restore explicitly-cleared rows so cleared cells don't appear mapped on reload.
    const clearedTypeSpecifics: Record<string, string[]> = mappings.cleared_type_specifics || {};
    Object.entries(clearedTypeSpecifics).forEach(([headerName, opTypes]) => {
      const idx = importFileHeaders.indexOf(headerName);
      if (idx < 0) return;
      (opTypes as string[]).forEach(opType => {
        const colId = getColIdForMapping(idx);
        if (!colId) return;
        const list = columnConfigMap[colId].typeSpecific[opType];
        if (!list || !list.some(m => m.dbKey)) {
          columnConfigMap[colId].typeSpecific[opType] = [{ dbKey: '' }];
        }
      });
    });
    // 5. Per-op-type settings: auto transaction IDs + hash column subsets.
    const enrichTxIds = mappings.enrich_transaction_ids;
    if (enrichTxIds && typeof enrichTxIds === 'object') {
      Object.entries(enrichTxIds).forEach(([opType, mode]) => {
        if (!opTypeSettings[opType]) opTypeSettings[opType] = {};
        opTypeSettings[opType].autoTransactionId = mode as OpTypeSettings['autoTransactionId'];
      });
    }
    const hashColumns = mappings.hash_columns;
    if (hashColumns && typeof hashColumns === 'object' && !Array.isArray(hashColumns)) {
      Object.entries(hashColumns).forEach(([opType, cols]) => {
        if (!Array.isArray(cols)) return;
        if (!opTypeSettings[opType]) opTypeSettings[opType] = {};
        opTypeSettings[opType].hashColumns = cols as string[];
      });
    }
  } catch (err) {
    console.error('Failed to parse schema mappings:', err);
  }

  return { operationTypeColumnIdx, operationTypeMappings, columnConfigMap, uiColumns, uiRowsOrder, opTypeSettings, splitTypes };
}
