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
  uniqueOperationTypes: string[],
  matchingRowsByRawAction: Record<string, { csvRow: string[]; rowIdx: number }[]>,
  selectedExampleOffset: Record<string, number>
) {
  return uniqueOperationTypes.map(rawAction => {
    const matches = matchingRowsByRawAction[rawAction] || [];
    if (matches.length === 0) {
      return { opType: rawAction, csvRow: [], rowIdx: -1, totalMatches: 0, currentOffset: 0 };
    }

    let offset = selectedExampleOffset[rawAction] || 0;
    if (offset >= matches.length) {
      offset = 0;
    }
    const match = matches[offset];
    return {
      opType: rawAction,
      csvRow: match.csvRow,
      rowIdx: match.rowIdx,
      totalMatches: matches.length,
      currentOffset: offset
    };
  }).filter(e => e.rowIdx !== -1);
}

export function getWizardSetup(params: {
  colId: string;
  colIdx: number;
  opType: string | null;
  rawAction: string | null;
  importFileHeaders: string[];
  exampleTransactions: any[];
  allRawRows: string[][];
  columnConfigMap: Record<string, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>;
  matchingRowsByType?: Record<string, { csvRow: string[]; rowIdx: number }[]>;
  targets?: Array<{ colId: string; colIdx: number; opType: string | null }>;
}) {
  const csvHeaderName = params.importFileHeaders[params.colIdx];

  let exampleValue = '';
  if (params.rawAction) {
    const example = params.exampleTransactions.find(e => e.opType === params.rawAction);
    if (example && example.csvRow) {
      exampleValue = example.csvRow[params.colIdx] || '';
    }
  } else {
    if (params.allRawRows.length > 0) {
      exampleValue = params.allRawRows[0][params.colIdx] || '';
    }
  }

  const uniqueSet = new Set<string>();
  const hasGlobalTarget = params.targets?.some(t => t.opType === null);
  const isGlobal = hasGlobalTarget || (!params.opType && (!params.targets || params.targets.length === 0));

  if (isGlobal || !params.matchingRowsByType) {
    params.allRawRows.forEach(row => {
      const v = row[params.colIdx];
      if (v && v.trim()) {
        uniqueSet.add(v.trim());
      }
    });
  } else {
    const opTypesToCollect = new Set<string>();
    if (params.targets && params.targets.length > 0) {
      params.targets.forEach(t => {
        if (t.opType) opTypesToCollect.add(t.opType);
      });
    } else if (params.opType) {
      opTypesToCollect.add(params.opType);
    }

    opTypesToCollect.forEach(opType => {
      const matches = params.matchingRowsByType![opType];
      if (matches) {
        matches.forEach(item => {
          const v = item.csvRow[params.colIdx];
          if (v && v.trim()) {
            uniqueSet.add(v.trim());
          }
        });
      }
    });
  }
  const uniqueValues = Array.from(uniqueSet);

  const conf = params.columnConfigMap[params.colId];
  let initialMapping: any = null;
  if (conf) {
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
  }

  return {
    csvHeaderName,
    exampleValue,
    uniqueValues,
    initialMapping
  };
}

export function saveWizardConfig(
  columnConfigMap: Record<string, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>,
  colId: string,
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
  const conf = columnConfigMap[colId];
  if (!conf) return;

  const mapEntry = {
    dbKey: payload.dbKey,
    divisor: payload.divisor,
    multiplier: payload.multiplier,
    enumMappings: payload.enumMappings,
    dateFormat: payload.dateFormat
  };

  if (opType) {
    if (payload.dbKey) {
      conf.typeSpecific[opType] = mapEntry;
    } else {
      delete conf.typeSpecific[opType];
    }
  } else {
    conf.global = mapEntry;
  }
}

export function clearWizardConfig(
  columnConfigMap: Record<string, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>,
  colId: string,
  opType: string | null
) {
  const conf = columnConfigMap[colId];
  if (!conf) return;

  if (opType) {
    delete conf.typeSpecific[opType];
  } else {
    conf.global = { dbKey: '' };
  }
}
