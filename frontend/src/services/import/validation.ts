import type { ColMapping, RowError } from './types';

export function getColumnConfigForField(
  columnConfigMap: Record<string | number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>,
  fieldKey: string,
  rawAction: string,
  opType: string
): ColMapping | null {
  // ponytail: Consolidated duplicate config resolver helper.
  let foundConf: ColMapping | null = null;
  if (!columnConfigMap) return foundConf;
  Object.entries(columnConfigMap).forEach(([_, conf]) => {
    if (!conf) return;
    if (conf.typeSpecific && conf.typeSpecific[rawAction]?.dbKey === fieldKey) {
      foundConf = conf.typeSpecific[rawAction];
    } else if (conf.typeSpecific && opType && conf.typeSpecific[opType]?.dbKey === fieldKey) {
      foundConf = conf.typeSpecific[opType];
    } else if (conf.global?.dbKey === fieldKey) {
      foundConf = conf.global;
    }
  });
  return foundConf;
}

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

  const reqMap: Record<string, string[]> = {
    trade: ['ticker', 'quantity', 'unit_price', 'trade_side'],
    dividend: ['ticker', 'unit_price'],
    stock_split: ['ticker', 'quantity'],
    fx_rate_change: ['source_currency', 'target_currency', 'exchange_rate'],
    fee: ['fee_amount'],
    tax: ['tax_amount'],
    interest: ['interest_type'],
    transfer_in: ['source_reference'],
    transfer_out: ['destination_reference'],
    expense: ['merchant_name'],
    revenue: ['merchant_name'],
  };
  return (reqMap[opType] || []).includes(fieldKey);
}

export function getMappedColIdxForField(
  dbKey: string,
  rawAction: string,
  dbOpType: string,
  columnConfigMap: Record<string | number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>,
  uiColumns?: Array<{ id: string; colIdx: number }>
): number {
  let mappedIdx = -1;
  if (!columnConfigMap) return mappedIdx;

  const resolveIdx = (idOrIdxStr: string) => {
    if (uiColumns) {
      const col = uiColumns.find(c => c.id === idOrIdxStr);
      return col ? col.colIdx : -1;
    }
    const idx = Number(idOrIdxStr);
    return isNaN(idx) ? -1 : idx;
  };

  Object.entries(columnConfigMap).forEach(([idOrIdxStr, conf]) => {
    if (!conf) return;
    if (conf.typeSpecific && conf.typeSpecific[rawAction]?.dbKey === dbKey) {
      mappedIdx = resolveIdx(idOrIdxStr);
    } else if (conf.typeSpecific && dbOpType && conf.typeSpecific[dbOpType]?.dbKey === dbKey) {
      mappedIdx = resolveIdx(idOrIdxStr);
    } else if (conf.global?.dbKey === dbKey) {
      mappedIdx = resolveIdx(idOrIdxStr);
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
  enrichedNames?: Record<string, string>;
}): Record<string, { total: number; success: number; failed: number; errors: RowError[] }> {
  const stats: Record<string, {
    total: number;
    success: number;
    failed: number;
    errors: RowError[];
  }> = {};

  if (params.operationTypeColumnIdx === null) {
    console.log('validateLiveStats: operationTypeColumnIdx is null, returning empty stats');
    return stats;
  }

  params.allRawRows.forEach(row => {
    const rawAction = row[params.operationTypeColumnIdx!];
    if (rawAction) {
      const trimmed = rawAction.trim();
      if (!stats[trimmed]) {
        stats[trimmed] = {
          total: 0,
          success: 0,
          failed: 0,
          errors: []
        };
      }
    }
  });

  const rawActionFieldMaps: Record<string, Record<string, { colIdx: number; isRequired: boolean; mappingConf: ColMapping | null }>> = {};
  const uniqueRawActions = Object.keys(stats);

  uniqueRawActions.forEach(rawAction => {
    const dbOpType = params.operationTypeMappings[rawAction] || 'unknown';
    const fieldMap: Record<string, { colIdx: number; isRequired: boolean; mappingConf: ColMapping | null }> = {};
    params.importFields.forEach(field => {
      const colIdx = field.key === 'operation_type'
        ? (params.operationTypeColumnIdx ?? -1)
        : getMappedColIdxForField(field.key, rawAction, dbOpType, params.columnConfigMap, params.uiColumns);
      const isRequired = field.is_required || isFieldRequiredForOpType(field.key, dbOpType);
      const mappingConf = getColumnConfigForField(params.columnConfigMap, field.key, rawAction, dbOpType);
      fieldMap[field.key] = { colIdx, isRequired, mappingConf };
    });
    rawActionFieldMaps[rawAction] = fieldMap;
  });

  params.allRawRows.forEach((row, rowIdx) => {
    const rawAction = row[params.operationTypeColumnIdx!];
    if (!rawAction) return;

    const trimmedRaw = rawAction.trim();
    if (!stats[trimmedRaw]) return;

    const fieldMap = rawActionFieldMaps[trimmedRaw];
    if (!fieldMap) return;

    stats[trimmedRaw].total++;

    const rowErrors: { fieldKey: string; fieldLabel: string; rawValue: string; errorMessage: string }[] = [];

    params.importFields.forEach(field => {
      const { colIdx, isRequired, mappingConf } = fieldMap[field.key];
      const isMapped = colIdx !== -1;
      const rawValue = isMapped ? row[colIdx] : '';

      if (isRequired && !isMapped) {
        rowErrors.push({
          fieldKey: field.key,
          fieldLabel: field.label,
          rawValue: '',
          errorMessage: 'Field is required but not mapped to any column.'
        });
        return;
      }

      // Check ticker resolution failures (failing the row parsing)
      if (field.key === 'name') {
        const val = rawValue ? rawValue.trim() : '';
        const enrichOption = mappingConf?.enrichAssetNames || 'when_empty';
        const isEnrichingAssetNames = enrichOption === 'always' || (enrichOption === 'when_empty' && !val);
        if (isEnrichingAssetNames) {
          const tickerCol = fieldMap['ticker']?.colIdx ?? -1;
          const ticker = tickerCol !== -1 && tickerCol < row.length ? row[tickerCol]?.trim() : '';
          if (!ticker) {
            rowErrors.push({
              fieldKey: field.key,
              fieldLabel: field.label,
              rawValue: val,
              errorMessage: 'Asset name auto-enrichment requires a mapped ticker, but ticker value is missing.'
            });
            return;
          } else if (params.enrichedNames?.[ticker]?.includes('(Not Found)')) {
            rowErrors.push({
              fieldKey: field.key,
              fieldLabel: field.label,
              rawValue: val,
              errorMessage: `Ticker '${ticker}' could not be resolved to a valid asset name.`
            });
            return;
          }
        }
      }

      if (isMapped && rawValue && rawValue.trim()) {
        const val = rawValue.trim();

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
          if (field.key === 'operation_type') {
            const mappedEnum = params.operationTypeMappings[val];
            if (!mappedEnum) {
              rowErrors.push({
                fieldKey: field.key,
                fieldLabel: field.label,
                rawValue: val,
                errorMessage: `Value "${val}" is not mapped to a database enum option.`
              });
            }
          } else {
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
      stats[trimmedRaw].failed++;
      rowErrors.forEach(err => {
        stats[trimmedRaw].errors.push({
          rowNum: rowIdx + 2, // 1-based index (row 1 is header)
          rawRow: row,
          ...err
        });
      });
    } else {
      stats[trimmedRaw].success++;
    }
  });

  console.log('validateLiveStats output keys/totals:', Object.keys(stats).map(k => `${k}: total=${stats[k].total}, success=${stats[k].success}, failed=${stats[k].failed}`));
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
    } else {
      const stats = params.liveValidationStats[val];
      if (stats && stats.failed > 0) {
        errors.push(`There are ${stats.failed} parsing failures in "${val}" transactions.`);
      }
    }
  });

  params.activeDbOpTypes.forEach(opType => {
    params.importFields.forEach(f => {
      const isRequired = f.is_required || isFieldRequiredForOpType(f.key, opType);
      if (isRequired) {
        let colIdx = f.key === 'operation_type'
          ? (params.operationTypeColumnIdx ?? -1)
          : getMappedColIdxForField(f.key, opType, opType, params.columnConfigMap, params.uiColumns);

        if (colIdx === -1 && f.key !== 'operation_type') {
          const rawActions = params.uniqueOperationTypes.filter(r => params.operationTypeMappings[r] === opType);
          for (const rawAction of rawActions) {
            colIdx = getMappedColIdxForField(f.key, rawAction, opType, params.columnConfigMap, params.uiColumns);
            if (colIdx !== -1) break;
          }
        }

        if (colIdx === -1) {
          errors.push(`Required database field "${f.label}" is not mapped for "${opType}" transactions.`);
        }
      }
    });
  });

  return errors;
}
