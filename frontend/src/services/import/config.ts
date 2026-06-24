import type { ColMapping } from './types';

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
  columnConfigMap: Record<string, { typeSpecific: Record<string, ColMapping> }>;
  uiColumns: Array<{ id: string; colIdx: number }>;
  operationTypeMappings: Record<string, string>;
  importFields: any[];
}) {
  const transformations: Record<string, any> = {};
  const enum_mappings: Record<string, Record<string, string[]>> = {};
  const date_formats: Record<string, any> = {};

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

    Object.entries(conf.typeSpecific).forEach(([opType, specificConf]) => {
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

  return {
    operation_type_column: params.operationTypeColumnIdx !== null
      ? params.importFileHeaders[params.operationTypeColumnIdx]
      : null,
    columns: finalColumns,
    type_mappings,
    enum_mappings,
    transformations,
    date_formats,
    enrich_asset_names,
    enrich_transaction_ids,
    ...(Object.keys(cleared_type_specifics).length > 0 ? { cleared_type_specifics } : {})
  };
}

export function parseSchemaMappings(
  mappingsJson: string,
  importFileHeaders: string[]
): {
  operationTypeColumnIdx: number | null;
  operationTypeMappings: Record<string, string>;
  columnConfigMap: Record<string, { typeSpecific: Record<string, ColMapping> }>;
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }>;
} {
  let operationTypeColumnIdx: number | null = null;
  const operationTypeMappings: Record<string, string> = {};
  const columnConfigMap: Record<string, { typeSpecific: Record<string, ColMapping> }> = {};
  const uiColumns: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }> = [];

  importFileHeaders.forEach((h, idx) => {
    const colId = `col-${idx}`;
    uiColumns.push({ id: colId, colIdx: idx, name: h, label: h });
    columnConfigMap[colId] = { typeSpecific: {} };
  });

  // Find or create a UI column for the given CSV index that has a free typeSpecific
  // slot for `opType`, creating a duplicate column only when there's a real conflict.
  const getOrCreateColIdForMapping = (idx: number, dbKey: string, opType: string): string => {
    for (const col of uiColumns) {
      if (col.colIdx !== idx) continue;
      const conf = columnConfigMap[col.id];
      if (!conf) continue;
      const existing = conf.typeSpecific[opType];
      // Reuse if the slot is free or already set to this same dbKey.
      if (!existing || existing.dbKey === dbKey) return col.id;
    }
    // No suitable slot found — create a duplicate UI column.
    const headerName = importFileHeaders[idx];
    const dupCount = uiColumns.filter(c => c.colIdx === idx).length;
    const newId = `col-${idx}_dup_${dupCount}`;
    uiColumns.push({ id: newId, colIdx: idx, name: headerName, label: `${headerName} (Copy)`, isDuplicate: true });
    columnConfigMap[newId] = { typeSpecific: {} };
    return newId;
  };

  try {
    const mappings = JSON.parse(mappingsJson);
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
        const colId = getOrCreateColIdForMapping(idx, dbKey, opType);
        const dfVal = dateFormats[dbKey];
        const specDateFormat = !dfVal
          ? 'auto'
          : typeof dfVal === 'string' ? dfVal : (dfVal[opType] || 'auto');

        const specConf: ColMapping = {
          dbKey,
          divisor: mappings.transformations?.[dbKey]?.[opType]?.divisor || mappings.transformations?.[dbKey]?.divisor,
          multiplier: mappings.transformations?.[dbKey]?.[opType]?.multiplier || mappings.transformations?.[dbKey]?.multiplier,
          enumMappings: getEnumMappingsForField(dbKey, mappings),
          dateFormat: specDateFormat
        };

        if (dbKey === 'name') {
          specConf.enrichAssetNames = mappings.enrich_asset_names?.[opType] || 'when_empty';
        }
        if (dbKey === 'transaction_id') {
          specConf.enrichTransactionIds = mappings.enrich_transaction_ids?.[opType] || 'when_empty';
        }

        columnConfigMap[colId].typeSpecific[opType] = specConf;
      });
    });

    // 4. Restore explicitly-cleared rows so cleared cells don't appear mapped on reload.
    const clearedTypeSpecifics: Record<string, string[]> = mappings.cleared_type_specifics || {};
    Object.entries(clearedTypeSpecifics).forEach(([headerName, opTypes]) => {
      const idx = importFileHeaders.indexOf(headerName);
      if (idx < 0) return;
      (opTypes as string[]).forEach(opType => {
        for (const col of uiColumns) {
          if (col.colIdx !== idx) continue;
          const conf = columnConfigMap[col.id];
          if (!conf) continue;
          const existing = conf.typeSpecific[opType];
          if (!existing || !existing.dbKey) {
            conf.typeSpecific[opType] = { dbKey: '' };
            break;
          }
        }
      });
    });
  } catch (err) {
    console.error('Failed to parse schema mappings:', err);
  }

  return { operationTypeColumnIdx, operationTypeMappings, columnConfigMap, uiColumns };
}
