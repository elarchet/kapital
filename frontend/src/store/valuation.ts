import { defineStore } from 'pinia';
import {
  portfolioApi,
  type Allocation,
  type AllocationLineInput,
  type PortfolioValuation,
  type RangeKey,
  type RawTransaction,
} from '../services/portfolioApi';

/** Stable cache key for an asset row spanning one or more positions. */
export const assetKey = (positionIds: number[]) => [...positionIds].sort((a, b) => a - b).join('-');

/**
 * Valuation state for the portfolio page. All figures come computed from the
 * backend valuation endpoint — nothing financial is derived client-side.
 */
export const useValuationStore = defineStore('valuation', {
  state: () => ({
    valuation: null as PortfolioValuation | null,
    range: '1y' as RangeKey,
    loading: false,
    error: null as string | null,
    transactionsByAsset: {} as Record<string, RawTransaction[]>,
    allocationsByTransaction: {} as Record<number, Allocation[]>,
    transactionsLoading: false,
  }),

  actions: {
    async fetchValuation(portfolioId: number | 'unassigned', range?: RangeKey) {
      if (range) this.range = range;
      this.loading = true;
      this.error = null;
      try {
        this.valuation = await portfolioApi.getPortfolioValuation(portfolioId, this.range);
      } catch (err: any) {
        this.error = err.message || 'Failed to load portfolio valuation';
        this.valuation = null;
      } finally {
        this.loading = false;
      }
    },

    async fetchAssetTransactions(positionIds: number[], force = false) {
      const key = assetKey(positionIds);
      if (!force && this.transactionsByAsset[key]) return;
      this.transactionsLoading = true;
      try {
        const transactions = await portfolioApi.getPositionTransactions(positionIds);
        this.transactionsByAsset = { ...this.transactionsByAsset, [key]: transactions };
        // Allocation counts drive the "split" badges — fetch them alongside.
        const allocations = await Promise.all(
          transactions.map(t => portfolioApi.getTransactionAllocations(t.id))
        );
        const merged = { ...this.allocationsByTransaction };
        transactions.forEach((t, i) => {
          merged[t.id] = allocations[i];
        });
        this.allocationsByTransaction = merged;
      } catch (err: any) {
        this.error = err.message || 'Failed to load transactions';
      } finally {
        this.transactionsLoading = false;
      }
    },

    async applySplit(
      transactionId: number,
      lines: AllocationLineInput[],
      refresh: { portfolioId: number | 'unassigned'; positionIds: number[] }
    ) {
      const allocations = await portfolioApi.splitTransaction(transactionId, lines);
      this.allocationsByTransaction = { ...this.allocationsByTransaction, [transactionId]: allocations };
      await Promise.all([
        this.fetchValuation(refresh.portfolioId),
        this.fetchAssetTransactions(refresh.positionIds, true),
      ]);
      return allocations;
    },

    async recombine(
      transactionId: number,
      positionId: number,
      refresh: { portfolioId: number | 'unassigned'; positionIds: number[] }
    ) {
      const allocations = await portfolioApi.recombineTransaction(transactionId, positionId);
      this.allocationsByTransaction = { ...this.allocationsByTransaction, [transactionId]: allocations };
      await Promise.all([
        this.fetchValuation(refresh.portfolioId),
        this.fetchAssetTransactions(refresh.positionIds, true),
      ]);
      return allocations;
    },

    clearDrilldownCache() {
      this.transactionsByAsset = {};
      this.allocationsByTransaction = {};
    },
  },
});
