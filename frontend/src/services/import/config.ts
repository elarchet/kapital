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
  columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>;
  operationTypeMappings: Record<string, string>;
  importFields: any[];
}) {
  const transformations: Record<string, any> = {};
  const enum_mappings: Record<string, Record<string, string[]>> = {};
  const date_formats: Record<string, any> = {};

  const dbKeyToCol = new Map<string, { global?: string; typeSpecific?: Record<string, string> }>();

  params.importFields.forEach(f => {
    if (f.key !== 'operation_type') {
      dbKeyToCol.set(f.key, {});
    }
  });

  Object.entries(params.columnConfigMap).forEach(([colIdxStr, conf]) => {
    const colIdx = Number(colIdxStr);
    const headerName = params.importFileHeaders[colIdx];

    if (conf.global.dbKey) {
      const entry = dbKeyToCol.get(conf.global.dbKey) || {};
      entry.global = headerName;
      dbKeyToCol.set(conf.global.dbKey, entry);

      if (conf.global.divisor || conf.global.multiplier) {
        transformations[conf.global.dbKey] = {
          divisor: conf.global.divisor,
          multiplier: conf.global.multiplier
        };
      }

      if (conf.global.dateFormat && conf.global.dateFormat !== 'auto') {
        date_formats[conf.global.dbKey] = conf.global.dateFormat;
      }

      if (conf.global.enumMappings) {
        const dbKey = conf.global.dbKey;
        if (!enum_mappings[dbKey]) enum_mappings[dbKey] = {};
        Object.entries(conf.global.enumMappings).forEach(([rawVal, targetVal]) => {
          if (targetVal) {
            if (!enum_mappings[dbKey][targetVal]) enum_mappings[dbKey][targetVal] = [];
            enum_mappings[dbKey][targetVal].push(rawVal);
          }
        });
      }
    }

    Object.entries(conf.typeSpecific).forEach(([opType, specificConf]) => {
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
          if (!date_formats[specificConf.dbKey]) {
            date_formats[specificConf.dbKey] = {};
          }
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
      }
    });
  });

  const finalColumns: Record<string, any> = {};
  if (params.operationTypeColumnIdx !== null) {
    finalColumns['operation_type'] = params.importFileHeaders[params.operationTypeColumnIdx];
  }

  dbKeyToCol.forEach((entry, dbKey) => {
    if (entry.typeSpecific && Object.keys(entry.typeSpecific).length > 0) {
      const typeMap: Record<string, string> = { ...entry.typeSpecific };
      if (entry.global) {
        typeMap['global'] = entry.global;
      }
      finalColumns[dbKey] = typeMap;
    } else if (entry.global) {
      finalColumns[dbKey] = entry.global;
    }
  });

  const type_mappings: Record<string, string[]> = {};
  const opField = params.importFields.find(f => f.key === 'operation_type');
  if (opField && opField.enum_values) {
    opField.enum_values.forEach((v: string) => {
      type_mappings[v] = [];
    });
  }

  Object.entries(params.operationTypeMappings).forEach(([rawVal, targetVal]) => {
    if (targetVal) {
      if (!type_mappings[targetVal]) type_mappings[targetVal] = [];
      type_mappings[targetVal].push(rawVal);
    }
  });

  return {
    columns: finalColumns,
    type_mappings,
    enum_mappings,
    transformations,
    date_formats
  };
}

export function parseSchemaMappings(
  mappingsJson: string,
  importFileHeaders: string[]
): {
  operationTypeColumnIdx: number | null;
  operationTypeMappings: Record<string, string>;
  columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>;
} {
  let operationTypeColumnIdx: number | null = null;
  const operationTypeMappings: Record<string, string> = {};
  const columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }> = {};

  importFileHeaders.forEach((_, idx) => {
    columnConfigMap[idx] = {
      global: { dbKey: '' },
      typeSpecific: {}
    };
  });

  try {
    const mappings = JSON.parse(mappingsJson);
    const cols = mappings.columns || {};
    const dateFormats = mappings.date_formats || {};

    // 1. Parse operation type column
    const opTypeHeader = cols.operation_type;
    if (opTypeHeader) {
      const idx = importFileHeaders.indexOf(opTypeHeader);
      if (idx >= 0) {
        operationTypeColumnIdx = idx;
      }
    }

    // 2. Parse operation type value mappings
    const op_mappings = mappings.enum_mappings?.operation_type || mappings.type_mappings || {};
    Object.entries(op_mappings).forEach(([targetEnum, rawVals]: [string, any]) => {
      if (Array.isArray(rawVals)) {
        rawVals.forEach(val => {
          operationTypeMappings[val] = targetEnum;
        });
      }
    });

    // 3. Parse other columns mappings
    Object.entries(cols).forEach(([dbKey, val]) => {
      if (dbKey === 'operation_type') return;

      if (typeof val === 'string') {
        const idx = importFileHeaders.indexOf(val);
        if (idx >= 0) {
          let globalDateFormat = 'auto';
          const dfVal = dateFormats[dbKey];
          if (dfVal) {
            if (typeof dfVal === 'string') {
              globalDateFormat = dfVal;
            } else if (typeof dfVal === 'object') {
              globalDateFormat = dfVal.global || 'auto';
            }
          }

          columnConfigMap[idx].global = {
            dbKey,
            divisor: mappings.transformations?.[dbKey]?.divisor,
            multiplier: mappings.transformations?.[dbKey]?.multiplier,
            enumMappings: getEnumMappingsForField(dbKey, mappings),
            dateFormat: globalDateFormat
          };
        }
      } else if (val && typeof val === 'object') {
        const valObj = val as Record<string, string>;
        Object.entries(valObj).forEach(([opType, headerName]) => {
          const idx = importFileHeaders.indexOf(headerName);
          if (idx >= 0) {
            let specDateFormat = 'auto';
            const dfVal = dateFormats[dbKey];
            if (dfVal) {
              if (typeof dfVal === 'string') {
                specDateFormat = dfVal;
              } else if (typeof dfVal === 'object') {
                specDateFormat = dfVal[opType] || dfVal.global || 'auto';
              }
            }

            const mapEntry = {
              dbKey,
              divisor: mappings.transformations?.[dbKey]?.[opType]?.divisor || mappings.transformations?.[dbKey]?.divisor,
              multiplier: mappings.transformations?.[dbKey]?.[opType]?.multiplier || mappings.transformations?.[dbKey]?.multiplier,
              enumMappings: getEnumMappingsForField(dbKey, mappings),
              dateFormat: specDateFormat
            };

            if (opType === 'global') {
              columnConfigMap[idx].global = mapEntry;
            } else {
              columnConfigMap[idx].typeSpecific[opType] = mapEntry;
            }
          }
        });
      }
    });
  } catch (err) {
    console.error('Failed to parse schema mappings:', err);
  }

  return {
    operationTypeColumnIdx,
    operationTypeMappings,
    columnConfigMap
  };
}
