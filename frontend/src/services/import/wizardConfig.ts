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
      const opType = operationTypeMappings[rawAction.trim()];
      if (opType) {
        if (!result[opType]) result[opType] = [];
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
    if (offset >= matches.length) offset = 0;
    const match = matches[offset];
    return { opType: rawAction, csvRow: match.csvRow, rowIdx: match.rowIdx, totalMatches: matches.length, currentOffset: offset };
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
  columnConfigMap: Record<string, { typeSpecific: Record<string, ColMapping> }>;
  matchingRowsByType?: Record<string, { csvRow: string[]; rowIdx: number }[]>;
  matchingRowsByRawAction?: Record<string, { csvRow: string[]; rowIdx: number }[]>;
  targets?: Array<{ colId: string; colIdx: number; opType: string | null }>;
}) {
  const csvHeaderName = params.importFileHeaders[params.colIdx];

  let exampleValue = '';
  if (params.rawAction) {
    const example = params.exampleTransactions.find(e => e.opType === params.rawAction);
    if (example?.csvRow) exampleValue = example.csvRow[params.colIdx] || '';
  } else if (params.allRawRows.length > 0) {
    exampleValue = params.allRawRows[0][params.colIdx] || '';
  }

  const uniqueSet = new Set<string>();
  const allTargetsHaveOpType = params.targets?.every(t => t.opType !== null) ?? false;
  const hasTypeContext = params.rawAction || params.opType || allTargetsHaveOpType;

  if (!hasTypeContext || (!params.matchingRowsByType && !params.matchingRowsByRawAction)) {
    params.allRawRows.forEach(row => {
      const v = row[params.colIdx];
      if (v?.trim()) uniqueSet.add(v.trim());
    });
  } else {
    const opTypesToCollect = new Set<string>();
    if (params.targets && params.targets.length > 0) {
      params.targets.forEach(t => { if (t.opType) opTypesToCollect.add(t.opType); });
    } else if (params.rawAction) {
      opTypesToCollect.add(params.rawAction);
    } else if (params.opType) {
      opTypesToCollect.add(params.opType);
    }

    opTypesToCollect.forEach(key => {
      const matches = (params.matchingRowsByRawAction?.[key]) || (params.matchingRowsByType?.[key]);
      if (matches) {
        matches.forEach(item => {
          const v = item.csvRow[params.colIdx];
          if (v?.trim()) uniqueSet.add(v.trim());
        });
      }
    });

    if (uniqueSet.size === 0) {
      params.allRawRows.forEach(row => {
        const v = row[params.colIdx];
        if (v?.trim()) uniqueSet.add(v.trim());
      });
    }
  }

  const conf = params.columnConfigMap[params.colId];
  let initialMapping: any = null;
  if (conf) {
    const specific = (params.opType ? conf.typeSpecific[params.opType] : null) ||
                     (params.rawAction ? conf.typeSpecific[params.rawAction] : null);
    if (specific?.dbKey) {
      initialMapping = {
        dbKey: specific.dbKey,
        scope: 'type',
        divisor: specific.divisor,
        multiplier: specific.multiplier,
        enumMappings: specific.enumMappings,
        dateFormat: specific.dateFormat,
        enrichAssetNames: specific.enrichAssetNames,
        enrichTransactionIds: specific.enrichTransactionIds
      };
    }
  }

  return { csvHeaderName, exampleValue, uniqueValues: Array.from(uniqueSet), initialMapping };
}

export function saveWizardConfig(
  columnConfigMap: Record<string, { typeSpecific: Record<string, ColMapping> }>,
  colId: string,
  opType: string | null,
  payload: {
    dbKey: string;
    scope: 'type';
    divisor?: number;
    multiplier?: number;
    enumMappings?: Record<string, string>;
    dateFormat?: string;
    enrichAssetNames?: 'never' | 'when_empty' | 'always';
    enrichTransactionIds?: 'never' | 'when_empty' | 'always';
  }
) {
  if (!opType) return; // opType is always required — no global slot exists anymore
  const conf = columnConfigMap[colId];
  if (!conf) return;
  conf.typeSpecific[opType] = {
    dbKey: payload.dbKey,
    divisor: payload.divisor,
    multiplier: payload.multiplier,
    enumMappings: payload.enumMappings,
    dateFormat: payload.dateFormat,
    enrichAssetNames: payload.enrichAssetNames,
    enrichTransactionIds: payload.enrichTransactionIds
  };
}

export function clearWizardConfig(
  columnConfigMap: Record<string, { typeSpecific: Record<string, ColMapping> }>,
  colId: string,
  opType: string | null
) {
  if (!opType) return; // opType is always required — no global slot exists anymore
  const conf = columnConfigMap[colId];
  if (!conf) return;
  conf.typeSpecific[opType] = { dbKey: '' };
}
