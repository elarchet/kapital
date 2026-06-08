import type { ColMapping } from './types';
import { getMappedColIdxForField } from './validation';

export function parsePreviewRows(params: {
  fileText: string;
  importDelimiter: string;
  importDecimalSep: string;
  operationTypeColumnIdx: number | null;
  operationTypeMappings: Record<string, string>;
  columnConfigMap: Record<string, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>;
  uiColumns: Array<{ id: string; colIdx: number }>;
  importFields: any[];
}) {
  if (!params.fileText || !params.importDelimiter || params.operationTypeColumnIdx === null) return [];

  const lines = params.fileText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length <= 1) return [];

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

  const previewLines = lines.slice(1, 6);
  return previewLines.map(line => {
    const cells = line.split(params.importDelimiter).map(c => c.trim().replace(/^["']|["']$/g, ''));
    const getVal = (idx: number) => (idx >= 0 && idx < cells.length ? cells[idx] : '');

    const rawAction = getVal(params.operationTypeColumnIdx!);
    const opType = params.operationTypeMappings[rawAction] || 'unknown';

    const getMappedVal = (dbKey: string) => {
      const idx = getMappedColIdxForField(dbKey, opType, params.columnConfigMap, params.uiColumns);
      return getVal(idx);
    };

    const applyTrans = (dbKey: string, rawVal: string) => {
      let num = parseFloat(rawVal.replace(params.importDecimalSep === '.' ? ',' : '.', '').replace(params.importDecimalSep, '.'));
      if (isNaN(num)) return rawVal;

      const idx = getMappedColIdxForField(dbKey, opType, params.columnConfigMap, params.uiColumns);
      if (idx !== -1) {
        const conf = getColumnConfigForField(dbKey, opType) as ColMapping | null;
        if (conf?.divisor) num /= conf.divisor;
        if (conf?.multiplier) num *= conf.multiplier;
      }
      return num.toString();
    };

    const ticker = getMappedVal('ticker');
    const isin = getMappedVal('isin');
    const name = getMappedVal('name') || ticker || isin || 'Asset';

    const rawQty = getMappedVal('quantity');
    const rawPrice = getMappedVal('unit_price');
    const rawPriceCurrency = getMappedVal('price_currency');
    const rawTotal = getMappedVal('total_amount');
    const rawCurrency = getMappedVal('currency');

    let parsedPrice = rawPrice;
    if (rawPrice) parsedPrice = applyTrans('unit_price', rawPrice);
    let parsedTotal = rawTotal;
    if (rawTotal) parsedTotal = applyTrans('total_amount', rawTotal);

    const displayCurrency = rawCurrency || 'EUR';
    const displayPriceCurrency = rawPriceCurrency || displayCurrency;

    const feesList: string[] = [];
    const feeAmtVal = getMappedVal('fee_amount');
    if (feeAmtVal && parseFloat(feeAmtVal) > 0) {
      const parsedFee = applyTrans('fee_amount', feeAmtVal);
      const rawFeeType = getMappedVal('fee_type');
      let resolvedFeeType = 'conversion';
      if (rawFeeType) {
        const idx = getMappedColIdxForField('fee_type', opType, params.columnConfigMap, params.uiColumns);
        if (idx !== -1) {
          const conf = getColumnConfigForField('fee_type', opType) as ColMapping | null;
          resolvedFeeType = conf?.enumMappings?.[rawFeeType] || 'conversion';
        }
      }
      feesList.push(`${parsedFee} ${getMappedVal('fee_currency') || displayCurrency} (${resolvedFeeType})`);
    }

    const taxAmtVal = getMappedVal('tax_amount');
    if (taxAmtVal && parseFloat(taxAmtVal) > 0) {
      const parsedTax = applyTrans('tax_amount', taxAmtVal);
      feesList.push(`${parsedTax} ${getMappedVal('tax_currency') || displayCurrency} (tax)`);
    }

    return {
      time: getMappedVal('executed_at'),
      action: rawAction,
      opType,
      ticker,
      name,
      isin,
      quantity: rawQty ? applyTrans('quantity', rawQty) : '',
      price: parsedPrice,
      priceCurrency: displayPriceCurrency,
      total: parsedTotal,
      currency: displayCurrency,
      fees: feesList.join(', ') || 'None',
      merchant: getMappedVal('merchant_name')
        ? `${getMappedVal('merchant_name')} (${getMappedVal('merchant_category')})`
        : '—'
    };
  });
}
