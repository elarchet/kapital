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
