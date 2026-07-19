/**
 * Portfolio valuation, transactions & split API client.
 *
 * All monetary figures arrive as strings (backend Decimal serialization);
 * the frontend never computes financials — it only parses for display.
 */

import { request } from './api';

export type RangeKey = '1m' | '3m' | '6m' | '1y' | 'ytd' | 'all';
export type PriceStatus = 'ok' | 'stale' | 'cost_fallback' | 'fixed';
export type AllocationMethod = 'quantity' | 'percentage' | 'amount';

export interface ValuationPoint {
  date: string;
  market_value: string;
  net_invested: string;
}

export interface PositionValuation {
  position_id: number;
  /** Every constituent position of this asset row (aggregated by ticker/isin/cash currency). */
  position_ids: number[];
  name: string | null;
  ticker: string | null;
  isin: string | null;
  asset_type: string;
  currency: string;
  quantity: string;
  price: string | null;
  price_date: string | null;
  price_status: PriceStatus;
  fx_approximate: boolean;
  market_value: string;
  total_invested: string;
  gain: string;
  gain_pct: string | null;
}

export interface AssetTypeSlice {
  asset_type: string;
  market_value: string;
  percentage: string;
}

export interface CurrentTotals {
  market_value: string;
  net_invested: string;
  gain: string;
  gain_pct: string | null;
}

export interface PortfolioValuation {
  portfolio_id: number | string;
  as_of: string;
  currency: string;
  currency_mixed: boolean;
  current: CurrentTotals;
  series: ValuationPoint[];
  positions: PositionValuation[];
  allocation: AssetTypeSlice[];
}

export interface TransactionFee {
  id: number;
  amount: string;
  currency: string;
  fee_type: string;
}

export interface RawTransaction {
  id: number;
  operation_type: string;
  trade_side: string | null;
  quantity: string | null;
  unit_price: string | null;
  total_amount: string;
  currency: string;
  executed_at: string;
  ticker: string | null;
  isin: string | null;
  name: string | null;
  notes: string | null;
  fees: TransactionFee[];
}

export interface Allocation {
  id: number;
  raw_transaction_id: number;
  position_id: number;
  method: AllocationMethod;
  value: string;
  quantity: string;
  amount: string;
  currency: string;
  is_default: boolean;
  notes: string | null;
  created_at: string;
}

export interface AllocationLineInput {
  position_id?: number;
  portfolio_id?: number;
  method: AllocationMethod;
  value: string;
  notes?: string | null;
}

export const portfolioApi = {
  async getPortfolioValuation(
    portfolioId: number | 'unassigned',
    range: RangeKey = '1y'
  ): Promise<PortfolioValuation> {
    return request<PortfolioValuation>(`/api/v1/portfolios/${portfolioId}/valuation?range=${range}`);
  },

  async getPositionTransactions(positionIds: number[]): Promise<RawTransaction[]> {
    const filters = positionIds.map(id => `position_id=${id}`).join('&');
    return request<RawTransaction[]>(`/api/v1/transactions/?${filters}&limit=1000`);
  },

  async getTransactionAllocations(transactionId: number): Promise<Allocation[]> {
    return request<Allocation[]>(`/api/v1/transactions/${transactionId}/allocations`);
  },

  async splitTransaction(transactionId: number, lines: AllocationLineInput[]): Promise<Allocation[]> {
    return request<Allocation[]>(`/api/v1/transactions/${transactionId}/allocations`, {
      method: 'POST',
      body: JSON.stringify({ lines }),
    });
  },

  async recombineTransaction(transactionId: number, positionId: number): Promise<Allocation[]> {
    return request<Allocation[]>(`/api/v1/transactions/${transactionId}/allocations/recombine`, {
      method: 'POST',
      body: JSON.stringify({ position_id: positionId }),
    });
  },
};
