import type { ColMapping, RowError } from './types';

export function getMappedColIdxForField(
  dbKey: string,
  opType: string,
  columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>
): number {
  let mappedIdx = -1;
  Object.entries(columnConfigMap).forEach(([idxStr, conf]) => {
    const idx = Number(idxStr);
    if (conf.typeSpecific[opType]?.dbKey === dbKey) {
      mappedIdx = idx;
    } else if (conf.global.dbKey === dbKey && !conf.typeSpecific[opType]?.dbKey) {
      mappedIdx = idx;
    }
  });
  return mappedIdx;
}

export function validateLiveStats(params: {
  importFields: any[];
  importDelimiter: string;
  importDecimalSep: string;
  columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>;
  activeDbOpTypes: string[];
  allRawRows: string[][];
  operationTypeColumnIdx: number | null;
  operationTypeMappings: Record<string, string>;
}): Record<string, { total: number; success: number; failed: number; errors: RowError[] }> {
  const stats: Record<string, {
    total: number;
    success: number;
    failed: number;
    errors: RowError[];
  }> = {};

  params.activeDbOpTypes.forEach(type => {
    stats[type] = {
      total: 0,
      success: 0,
      failed: 0,
      errors: []
    };
  });

  if (params.operationTypeColumnIdx === null) return stats;

  const getColumnConfig = (colIdx: number, opType: string) => {
    const conf = params.columnConfigMap[colIdx];
    if (!conf) return null;
    if (conf.typeSpecific[opType]?.dbKey) {
      return conf.typeSpecific[opType];
    }
    return conf.global;
  };

  params.allRawRows.forEach((row, rowIdx) => {
    const rawAction = row[params.operationTypeColumnIdx!];
    if (!rawAction) return;

    const opType = params.operationTypeMappings[rawAction];
    if (!opType || !stats[opType]) return;

    stats[opType].total++;

    const rowErrors: { fieldKey: string; fieldLabel: string; rawValue: string; errorMessage: string }[] = [];

    params.importFields.forEach(field => {
      const colIdx = getMappedColIdxForField(field.key, opType, params.columnConfigMap);
      const isMapped = colIdx !== -1;
      const rawValue = isMapped ? row[colIdx] : '';

      if (field.is_required && !isMapped) {
        rowErrors.push({
          fieldKey: field.key,
          fieldLabel: field.label,
          rawValue: '',
          errorMessage: 'Field is required but not mapped to any column.'
        });
        return;
      }

      if (isMapped && rawValue && rawValue.trim()) {
        const val = rawValue.trim();
        const mappingConf = getColumnConfig(colIdx, opType);

        if (field.type === 'numeric') {
          let cleaned = val;
          if (params.importDecimalSep !== '.') {
            cleaned = cleaned.replace(params.importDecimalSep, '.');
          }
          if (params.importDecimalSep === '.') {
            cleaned = cleaned.replace(/,/g, '');
          } else {
            cleaned = cleaned.replace(/\./g, '').replace(/\s/g, '');
          }

          const num = parseFloat(cleaned);
          if (isNaN(num)) {
            rowErrors.push({
              fieldKey: field.key,
              fieldLabel: field.label,
              rawValue: val,
              errorMessage: `"${val}" is not a valid decimal number.`
            });
          }
        } else if (field.type === 'datetime') {
          const parsedDate = new Date(val);
          if (isNaN(parsedDate.getTime())) {
            rowErrors.push({
              fieldKey: field.key,
              fieldLabel: field.label,
              rawValue: val,
              errorMessage: `"${val}" is not a valid date format.`
            });
          }
        } else if (field.type === 'enum') {
          const mappedEnum = mappingConf?.enumMappings?.[val];
          if (!mappedEnum) {
            rowErrors.push({
              fieldKey: field.key,
              fieldLabel: field.label,
              rawValue: val,
              errorMessage: `Value "${val}" is not mapped to a database enum option.`
            });
          }
        }
      } else if (field.is_required && (!rawValue || !rawValue.trim())) {
        rowErrors.push({
          fieldKey: field.key,
          fieldLabel: field.label,
          rawValue: '',
          errorMessage: 'Required field is empty.'
        });
      }
    });

    if (rowErrors.length > 0) {
      stats[opType].failed++;
      rowErrors.forEach(err => {
        stats[opType].errors.push({
          rowNum: rowIdx + 2, // 1-based index (row 1 is header)
          rawRow: row,
          ...err
        });
      });
    } else {
      stats[opType].success++;
    }
  });

  return stats;
}

export function getValidationErrors(params: {
  importFile: any;
  operationTypeColumnIdx: number | null;
  uniqueOperationTypes: string[];
  operationTypeMappings: Record<string, string>;
  activeDbOpTypes: string[];
  importFields: any[];
  columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>;
  liveValidationStats: Record<string, { failed: number }>;
}): string[] {
  const errors: string[] = [];
  if (!params.importFile) return errors;

  if (params.operationTypeColumnIdx === null) {
    errors.push('Required: operation type CSV column is not selected.');
    return errors;
  }

  params.uniqueOperationTypes.forEach(val => {
    if (!params.operationTypeMappings[val]) {
      errors.push(`Action "${val}" from your file is not mapped to any database transaction type.`);
    }
  });

  params.activeDbOpTypes.forEach(opType => {
    params.importFields.forEach(f => {
      if (f.is_required) {
        const colIdx = getMappedColIdxForField(f.key, opType, params.columnConfigMap);
        if (colIdx === -1) {
          errors.push(`Required database field "${f.label}" is not mapped for "${opType}" transactions.`);
        }
      }
    });

    const stats = params.liveValidationStats[opType];
    if (stats && stats.failed > 0) {
      errors.push(`There are ${stats.failed} parsing failures in "${opType}" transactions. Expand the Verification Panel below to inspect.`);
    }
  });

  return errors;
}
