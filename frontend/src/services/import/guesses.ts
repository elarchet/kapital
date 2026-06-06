import type { ColMapping } from './types';

export function prepopulateFieldGuesses(
  headers: string[],
  allRawRows: string[][],
  opIdx: number | null
): Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }> {
  const columnConfigMap: Record<number, { global: ColMapping; typeSpecific: Record<string, ColMapping> }> = {};
  headers.forEach((_, idx) => {
    columnConfigMap[idx] = {
      global: { dbKey: '' },
      typeSpecific: {}
    };
  });

  const findMatchIdx = (keys: string[]) => {
    return headers.findIndex(h => keys.some(k => h.toLowerCase().includes(k.toLowerCase())));
  };

  const matches: Record<string, string[]> = {
    ticker: ['ticker', 'symbol'],
    isin: ['isin'],
    name: ['name', 'description', 'company'],
    quantity: ['shares', 'qty', 'quantity', 'number of shares', 'no. of shares'],
    unit_price: ['price', 'unit price', 'price / share'],
    price_currency: ['price currency', 'price_currency'],
    total_amount: ['total', 'amount'],
    currency: ['currency'],
    executed_at: ['time', 'date', 'timestamp'],
    transaction_id: ['id', 'transaction id', 'reference'],
    fee_amount: ['fee', 'conversion fee'],
    fee_currency: ['fee currency'],
    fee_type: ['fee type'],
    tax_amount: ['tax', 'withholding tax'],
    tax_currency: ['tax currency'],
    merchant_name: ['merchant', 'merchant name'],
    merchant_category: ['category', 'merchant category'],
    interest_type: ['interest type', 'interest_type'],
    trade_side: ['side', 'trade side', 'direction', 'buy/sell'],
    order_type: ['order type', 'order_type'],
    order_status: ['order status', 'status'],
    limit_price: ['limit price', 'limit_price'],
    stop_price: ['stop price', 'stop_price'],
    execution_price: ['execution price', 'fill price', 'avg price'],
    order_placed_at: ['order date', 'placed at', 'order_placed_at'],
    filled_at: ['fill date', 'filled at', 'filled_at'],
    expense_category: ['expense category', 'expense_category'],
    revenue_category: ['revenue category', 'revenue_category', 'income type'],
    payment_method: ['payment method', 'payment_method', 'payment type']
  };

  Object.entries(matches).forEach(([dbKey, keys]) => {
    const idx = findMatchIdx(keys);
    if (idx >= 0 && idx !== opIdx) {
      columnConfigMap[idx].global = { dbKey };
    }
  });

  // Auto detect GBX currency for scaling divisor = 100
  const currencyIdx = headers.findIndex(h => h.toLowerCase().includes('currency'));
  if (currencyIdx >= 0) {
    const hasGBX = allRawRows.slice(0, 100).some(row => row[currencyIdx]?.toUpperCase() === 'GBX');
    if (hasGBX) {
      const priceIdx = findMatchIdx(['price', 'unit price', 'price / share']);
      if (priceIdx >= 0 && columnConfigMap[priceIdx]) {
        columnConfigMap[priceIdx].global.divisor = 100;
      }
      const totalIdx = findMatchIdx(['total', 'amount']);
      if (totalIdx >= 0 && columnConfigMap[totalIdx]) {
        columnConfigMap[totalIdx].global.divisor = 100;
      }
    }
  }

  return columnConfigMap;
}

export function prepopulateOpTypeGuesses(uniqueOperationTypes: string[]): Record<string, string> {
  const operationTypeMappings: Record<string, string> = {};
  uniqueOperationTypes.forEach(val => {
    const lower = val.toLowerCase();
    if (lower.includes('buy')) operationTypeMappings[val] = 'trade';
    else if (lower.includes('sell')) operationTypeMappings[val] = 'trade';
    else if (lower.includes('dividend')) operationTypeMappings[val] = 'dividend';
    else if (lower.includes('interest')) operationTypeMappings[val] = 'interest';
    else if (lower.includes('deposit')) operationTypeMappings[val] = 'transfer_in';
    else if (lower.includes('withdraw')) operationTypeMappings[val] = 'transfer_out';
    else if (lower.includes('debit') || lower.includes('expense')) operationTypeMappings[val] = 'expense';
    else if (lower.includes('credit') || lower.includes('revenue')) operationTypeMappings[val] = 'revenue';
    else if (lower.includes('conversion') || lower.includes('fx')) operationTypeMappings[val] = 'fx_rate_change';
    else if (lower.includes('split')) operationTypeMappings[val] = 'stock_split';
    else if (lower.includes('fee')) operationTypeMappings[val] = 'fee';
    else if (lower.includes('tax')) operationTypeMappings[val] = 'tax';
  });
  return operationTypeMappings;
}
