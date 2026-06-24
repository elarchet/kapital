import { computed, watch, type Ref } from 'vue';
import { api } from '../../services/api';
import { parsePreviewRows } from '../../services/import';

export function useImportPreview(params: {
  fileText: Ref<string>;
  importDelimiter: Ref<string>;
  importDecimalSep: Ref<string>;
  operationTypeColumnIdx: Ref<number | null>;
  operationTypeMappings: Ref<Record<string, string>>;
  columnConfigMap: Ref<Record<string, any>>;
  uiColumns: Ref<any[]>;
  importFields: Ref<any[]>;
  exampleTransactions: Ref<any[]>;
  enrichedNames: Ref<Record<string, string>>;
}) {
  const enrichedNames = params.enrichedNames;

  const parsedPreviewRows = computed(() => {
    const rawPreview = parsePreviewRows({
      fileText: params.fileText.value,
      importDelimiter: params.importDelimiter.value,
      importDecimalSep: params.importDecimalSep.value,
      operationTypeColumnIdx: params.operationTypeColumnIdx.value,
      operationTypeMappings: params.operationTypeMappings.value,
      columnConfigMap: params.columnConfigMap.value,
      uiColumns: params.uiColumns.value,
      importFields: params.importFields.value
    });

    return rawPreview.map(row => {
      let enrichOption: 'never' | 'when_empty' | 'always' = 'when_empty';
      for (const conf of Object.values(params.columnConfigMap.value) as any[]) {
        if (conf?.typeSpecific?.[row.opType]?.dbKey === 'name') {
          enrichOption = conf.typeSpecific[row.opType].enrichAssetNames || 'when_empty';
        }
      }

      const shouldEnrich =
        (enrichOption === 'always') ||
        (enrichOption === 'when_empty' && !row.nameWasSet);

      const enrichedName = (shouldEnrich && row.ticker) ? enrichedNames.value[row.ticker] : undefined;
      return {
        ...row,
        name: (enrichedName && enrichedName !== 'loading...') ? enrichedName : row.name,
        isEnriched: !!enrichedName && enrichedName !== 'loading...' && (enrichOption === 'always' || !row.nameWasSet)
      };
    });
  });

  watch([parsedPreviewRows, params.exampleTransactions, params.columnConfigMap], async ([newRows, examples, colConfig]) => {
    if (!newRows) return;
    
    const tickersToResolve = new Set<string>();

    // 1. Check preview rows
    for (const row of newRows) {
      let enrichOption: 'never' | 'when_empty' | 'always' = 'when_empty';
      for (const conf of Object.values(colConfig) as any[]) {
        if (conf?.typeSpecific?.[row.opType]?.dbKey === 'name') {
          enrichOption = conf.typeSpecific[row.opType].enrichAssetNames || 'when_empty';
        }
      }

      if (enrichOption === 'never') continue;

      const shouldEnrich =
        (enrichOption === 'always') ||
        (enrichOption === 'when_empty' && !row.nameWasSet);

      if (shouldEnrich && row.ticker) {
        tickersToResolve.add(row.ticker);
      }
    }

    // 2. Check example transactions
    for (const example of examples || []) {
      let tickerColIdx = -1;
      let nameColIdx = -1;
      params.uiColumns.value.forEach((col: any) => {
        const conf = colConfig[col.id];
        if (conf?.typeSpecific?.[example.opType]?.dbKey === 'ticker') {
          tickerColIdx = col.colIdx;
        }
        if (conf?.typeSpecific?.[example.opType]?.dbKey === 'name') {
          nameColIdx = col.colIdx;
        }
      });

      const ticker = (tickerColIdx !== -1 && tickerColIdx < example.csvRow.length) ? example.csvRow[tickerColIdx]?.trim() : '';
      const rawName = (nameColIdx !== -1 && nameColIdx < example.csvRow.length) ? example.csvRow[nameColIdx]?.trim() : '';
      const nameWasSet = !!(rawName && rawName.trim());

      let enrichOption: 'never' | 'when_empty' | 'always' = 'when_empty';
      for (const conf of Object.values(colConfig) as any[]) {
        if (conf?.typeSpecific?.[example.opType]?.dbKey === 'name') {
          enrichOption = conf.typeSpecific[example.opType].enrichAssetNames || 'when_empty';
        }
      }

      if (enrichOption === 'never') continue;

      const shouldEnrich =
        (enrichOption === 'always') ||
        (enrichOption === 'when_empty' && !nameWasSet);

      if (shouldEnrich && ticker) {
        tickersToResolve.add(ticker);
      }
    }

    // 3. Fetch tickers
    for (const ticker of tickersToResolve) {
      if (!enrichedNames.value[ticker]) {
        enrichedNames.value[ticker] = 'loading...';
        try {
          const profile = await api.getTickerProfile(ticker);
          if (profile && profile.name) {
            enrichedNames.value[ticker] = profile.name;
          } else {
            enrichedNames.value[ticker] = `${ticker} (Not Found)`;
          }
        } catch (e) {
          console.error(`Failed to fetch ticker profile for ${ticker}:`, e);
          enrichedNames.value[ticker] = `${ticker} (Not Found)`;
        }
      }
    }
  }, { immediate: true });

  return {
    parsedPreviewRows,
    enrichedNames
  };
}
