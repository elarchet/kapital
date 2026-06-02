import type { ColMapping } from './types';

export function groupRowsByOpType(
  allRawRows: string[][],
  operationTypeColumnIdx: number | null,
  operationTypeMappings: Record<string, string>
): Record<string, { csvRow: string[]; rowIdx: number }[]> {
  const result: Record<string, { csvRow: string[]; rowIdx: number }[]> = {};
  if (operationTypeColumnIdx === null) return result;

  allRawRows.forEach((row, idx) => {
    const rawAction = row[operationTypeColumnIdx];
    if (rawAction) {
      const opType = operationTypeMappings[rawAction];
      if (opType) {
        if (!result[opType]) {
          result[opType] = [];
        }
        result[opType].push({ csvRow: row, rowIdx: idx });
      }
    }
  });
  return result;
}

export function getExampleTransactions(
  activeDbOpTypes: string[],
  matchingRowsByType: Record<string, { csvRow: string[]; rowIdx: number }[]>,
  selectedExampleOffset: Record<string, number>
) {
  return activeDbOpTypes.map(type => {
    const matches = matchingRowsByType[type] || [];
    if (matches.length === 0) {
      return { opType: type, csvRow: [], rowIdx: -1, totalMatches: 0, currentOffset: 0 };
    }

    let offset = selectedExampleOffset[type] || 0;
    if (offset >= matches.length) {
      offset = 0;
    }
    const match = matches[offset];
    return {
      opType: type,
      csvRow: match.csvRow,
      rowIdx: match.rowIdx,
      totalMatches: matches.length,
      currentOffset: offset
    };
  }).filter(e => e.rowIdx !== -1);
}

export function getWizardSetup(params: {
  colIdx: number;
  opType: string | null;
  importFileHeaders: string[];
  exampleTransactions: any[];
  allRawRows: string[][];
  columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>;
}) {
  const csvHeaderName = params.importFileHeaders[params.colIdx];

  let exampleValue = '';
  if (params.opType) {
    const example = params.exampleTransactions.find(e => e.opType === params.opType);
    if (example && example.csvRow) {
      exampleValue = example.csvRow[params.colIdx] || '';
    }
  } else {
    if (params.allRawRows.length > 0) {
      exampleValue = params.allRawRows[0][params.colIdx] || '';
    }
  }

  const uniqueSet = new Set<string>();
  params.allRawRows.forEach(row => {
    const v = row[params.colIdx];
    if (v && v.trim()) {
      uniqueSet.add(v.trim());
    }
  });
  const uniqueValues = Array.from(uniqueSet);

  const conf = params.columnConfigMap[params.colIdx];
  let initialMapping: any = null;
  if (params.opType) {
    const specific = conf.typeSpecific[params.opType];
    if (specific?.dbKey) {
      initialMapping = {
        dbKey: specific.dbKey,
        scope: 'type',
        divisor: specific.divisor,
        multiplier: specific.multiplier,
        enumMappings: specific.enumMappings,
        dateFormat: specific.dateFormat
      };
    } else {
      initialMapping = {
        dbKey: conf.global.dbKey,
        scope: 'global',
        divisor: conf.global.divisor,
        multiplier: conf.global.multiplier,
        enumMappings: conf.global.enumMappings,
        dateFormat: conf.global.dateFormat
      };
    }
  } else {
    initialMapping = {
      dbKey: conf.global.dbKey,
      scope: 'global',
      divisor: conf.global.divisor,
      multiplier: conf.global.multiplier,
      enumMappings: conf.global.enumMappings,
      dateFormat: conf.global.dateFormat
    };
  }

  return {
    csvHeaderName,
    exampleValue,
    uniqueValues,
    initialMapping
  };
}

export function saveWizardConfig(
  columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>,
  colIdx: number,
  opType: string | null,
  payload: {
    dbKey: string;
    scope: 'global' | 'type';
    divisor?: number;
    multiplier?: number;
    enumMappings?: Record<string, string>;
    dateFormat?: string;
  }
) {
  const conf = columnConfigMap[colIdx];
  if (!conf) return;

  const mapEntry = {
    dbKey: payload.dbKey,
    divisor: payload.divisor,
    multiplier: payload.multiplier,
    enumMappings: payload.enumMappings,
    dateFormat: payload.dateFormat
  };

  // Always save to typeSpecific when opType is provided; fall back to global only when explicitly absent
  if (opType) {
    if (payload.dbKey) {
      conf.typeSpecific[opType] = mapEntry;
    } else {
      // "Ignore column" — remove any existing type-specific mapping
      delete conf.typeSpecific[opType];
    }
  } else {
    conf.global = mapEntry;
  }
}

export function clearWizardConfig(
  columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>,
  colIdx: number,
  opType: string | null
) {
  const conf = columnConfigMap[colIdx];
  if (!conf) return;

  if (opType) {
    delete conf.typeSpecific[opType];
  } else {
    conf.global = { dbKey: '' };
  }
}
