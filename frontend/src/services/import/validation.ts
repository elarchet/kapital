import type { ColMapping, RowError } from './types';

export function parseDateTimeWithFormat(val: string, format?: string): Date | null {
  if (!val) return null;
  const cleaned = val.trim();
  if (!format || format === 'auto') {
    const d = new Date(cleaned);
    return isNaN(d.getTime()) ? null : d;
  }

  try {
    let regexStr = format
      .replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&') // escape regex chars
      .replace('%Y', '(?<year>\\d{4})')
      .replace('%m', '(?<month>\\d{1,2})')
      .replace('%d', '(?<day>\\d{1,2})')
      .replace('%H', '(?<hour>\\d{1,2})')
      .replace('%M', '(?<minute>\\d{1,2})')
      .replace('%S', '(?<second>\\d{1,2})');
    
    if (regexStr.endsWith('(?<second>\\d{1,2})')) {
      regexStr += '(?<ms>\\.\\d+)?';
    }

    const regex = new RegExp(`^${regexStr}`);
    const match = cleaned.match(regex);
    if (match && match.groups) {
      const year = parseInt(match.groups.year, 10);
      const month = parseInt(match.groups.month, 10) - 1; // 0-based
      const day = parseInt(match.groups.day, 10);
      const hour = match.groups.hour ? parseInt(match.groups.hour, 10) : 0;
      const minute = match.groups.minute ? parseInt(match.groups.minute, 10) : 0;
      const second = match.groups.second ? parseInt(match.groups.second, 10) : 0;
      
      const d = new Date(year, month, day, hour, minute, second);
      if (!isNaN(d.getTime())) {
        return d;
      }
    }
  } catch (err) {
    console.error('Error parsing date with custom format:', err);
  }

  const fallback = new Date(cleaned);
  return isNaN(fallback.getTime()) ? null : fallback;
}

export function isFieldRequiredForOpType(fieldKey: string, opType: string): boolean {
  const globalRequired = ['executed_at', 'total_amount', 'currency'];
  if (globalRequired.includes(fieldKey)) return true;
  if (!opType) return false;

  if (opType === 'trade') {
    return ['ticker', 'quantity', 'unit_price', 'trade_side'].includes(fieldKey);
  }
  if (opType === 'dividend') {
    return ['ticker', 'unit_price'].includes(fieldKey);
  }
  if (opType === 'interest') {
    return fieldKey === 'interest_type';
  }
  if (opType === 'transfer_in') {
    return fieldKey === 'source_reference';
  }
  if (opType === 'transfer_out') {
    return fieldKey === 'destination_reference';
  }
  if (opType === 'stock_split') {
    return ['ticker', 'quantity'].includes(fieldKey);
  }
  if (opType === 'fx_rate_change') {
    return ['source_currency', 'target_currency', 'exchange_rate'].includes(fieldKey);
  }
  if (opType === 'fee') {
    return ['fee_amount'].includes(fieldKey);
  }
  if (opType === 'tax') {
    return ['tax_amount'].includes(fieldKey);
  }
  if (opType === 'expense') {
    return fieldKey === 'merchant_name';
  }
  if (opType === 'revenue') {
    return fieldKey === 'merchant_name';
  }
  return false;
}

export function getMappedColIdxForField(
  dbKey: string,
  opType: string,
  columnConfigMap: Record<string | number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>,
  uiColumns?: Array<{ id: string; colIdx: number }>
): number {
  let mappedIdx = -1;
  Object.entries(columnConfigMap).forEach(([idOrIdxStr, conf]) => {
    if (conf.typeSpecific[opType]?.dbKey === dbKey || (conf.global.dbKey === dbKey && !conf.typeSpecific[opType]?.dbKey)) {
      if (uiColumns) {
        const col = uiColumns.find(c => c.id === idOrIdxStr);
        if (col) {
          mappedIdx = col.colIdx;
        }
      } else {
        const idx = Number(idOrIdxStr);
        if (!isNaN(idx)) {
          mappedIdx = idx;
        }
      }
    }
  });
  return mappedIdx;
}

export function validateLiveStats(params: {
  importFields: any[];
  importDelimiter: string;
  importDecimalSep: string;
  columnConfigMap: Record<string, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>;
  uiColumns: Array<{ id: string; colIdx: number }>;
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

  const getColumnConfigForField = (fieldKey: string, opType: string) => {
    let foundConf: ColMapping | null = null;
    Object.entries(params.columnConfigMap).forEach(([_, conf]) => {
      if (conf.typeSpecific[opType]?.dbKey === fieldKey) {
        foundConf = conf.typeSpecific[opType];
      } else if (conf.global.dbKey === fieldKey && !conf.typeSpecific[opType]?.dbKey) {
        foundConf = conf.global;
      }
    });
    return foundConf;
  };

  params.allRawRows.forEach((row, rowIdx) => {
    const rawAction = row[params.operationTypeColumnIdx!];
    if (!rawAction) return;

    const opType = params.operationTypeMappings[rawAction];
    if (!opType || !stats[opType]) return;

    stats[opType].total++;

    const rowErrors: { fieldKey: string; fieldLabel: string; rawValue: string; errorMessage: string }[] = [];

    params.importFields.forEach(field => {
      const colIdx = getMappedColIdxForField(field.key, opType, params.columnConfigMap, params.uiColumns);
      const isMapped = colIdx !== -1;
      const rawValue = isMapped ? row[colIdx] : '';

      const isRequired = field.is_required || isFieldRequiredForOpType(field.key, opType);

      if (isRequired && !isMapped) {
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
        const mappingConf = getColumnConfigForField(field.key, opType) as ColMapping | null;

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
          const parsedDate = parseDateTimeWithFormat(val, mappingConf?.dateFormat);
          if (!parsedDate) {
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
      } else if (isRequired && (!rawValue || !rawValue.trim())) {
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
  columnConfigMap: Record<string, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>;
  uiColumns: Array<{ id: string; colIdx: number }>;
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
      const isRequired = f.is_required || isFieldRequiredForOpType(f.key, opType);
      if (isRequired) {
        const colIdx = getMappedColIdxForField(f.key, opType, params.columnConfigMap, params.uiColumns);
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
