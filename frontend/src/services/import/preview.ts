import type { ColMapping } from './types';
import { getMappedColIdxForField } from './validation';

export function parsePreviewRows(params: {
  fileText: string;
  importDelimiter: string;
  importDecimalSep: string;
  operationTypeColumnIdx: number | null;
  operationTypeMappings: Record<string, string>;
  columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }>;
  importFields: any[];
}) {
  if (!params.fileText || !params.importDelimiter || params.operationTypeColumnIdx === null) return [];

  const lines = params.fileText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length <= 1) return [];

  const getColumnConfig = (colIdx: number, opType: string) => {
    const conf = params.columnConfigMap[colIdx];
    if (!conf) return null;
    if (conf.typeSpecific[opType]?.dbKey) {
      return conf.typeSpecific[opType];
    }
    return conf.global;
  };

  const previewLines = lines.slice(1, 6);
  return previewLines.map(line => {
    const cells = line.split(params.importDelimiter).map(c => c.trim().replace(/^["']|["']$/g, ''));
    const getVal = (idx: number) => (idx >= 0 && idx < cells.length ? cells[idx] : '');

    const rawAction = getVal(params.operationTypeColumnIdx!);
    const opType = params.operationTypeMappings[rawAction] || 'unknown';

    const getMappedVal = (dbKey: string) => {
      const idx = getMappedColIdxForField(dbKey, opType, params.columnConfigMap);
      return getVal(idx);
    };

    const applyTrans = (dbKey: string, rawVal: string) => {
      let num = parseFloat(rawVal.replace(params.importDecimalSep === '.' ? ',' : '.', '').replace(params.importDecimalSep, '.'));
      if (isNaN(num)) return rawVal;

      const idx = getMappedColIdxForField(dbKey, opType, params.columnConfigMap);
      if (idx !== -1) {
        const conf = getColumnConfig(idx, opType);
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
        const idx = getMappedColIdxForField('fee_type', opType, params.columnConfigMap);
        if (idx !== -1) {
          const conf = getColumnConfig(idx, opType);
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
