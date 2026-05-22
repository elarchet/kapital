import { defineStore } from 'pinia';
import { api } from '../services/api';

export interface Portfolio {
  id: number;
  name: string;
  description?: string;
  created_at: string;
}

export interface Position {
  id: number;
  asset_type: 'cash' | 'crypto' | 'etf' | 'stock' | 'bond' | 'commodity' | 'fund' | 'other';
  ticker?: string;
  name: string;
  isin?: string;
  quantity: number;
  currency: string;
  portfolio_id: number;
  created_at: string;
  // Computed locally for beautiful rendering:
  estimated_price?: number; 
  estimated_value?: number;
}

export const useKapitalStore = defineStore('kapital', {
  state: () => ({
    portfolios: [] as Portfolio[],
    positions: [] as Position[],
    loading: false,
    error: null as string | null,
    isAuthenticated: api.isAuthenticated(),
    userEmail: api.getCurrentUserEmail(),
  }),

  getters: {
    // Aggregated net worth (mocking current prices since DB stores quantity and currency)
    // In a production fintech app, quantities would be multiplied by real-time tickers.
    // We will apply sensible mock pricing rules based on asset types for high visual premium fidelity.
    computedPositions(state): Position[] {
      return state.positions.map(pos => {
        // Safe defaults for visualization
        let estimatedPrice = 1.0;
        if (pos.asset_type === 'cash') estimatedPrice = 1.0;
        else if (pos.asset_type === 'stock') {
          // Stable mock prices based on ticker
          if (pos.ticker === 'AAPL') estimatedPrice = 175.50;
          else if (pos.ticker === 'MSFT') estimatedPrice = 420.20;
          else if (pos.ticker === 'NVDA') estimatedPrice = 875.00;
          else estimatedPrice = 120.00;
        } else if (pos.asset_type === 'crypto') {
          if (pos.ticker === 'BTC') estimatedPrice = 67200.00;
          else if (pos.ticker === 'ETH') estimatedPrice = 3500.00;
          else estimatedPrice = 1.50;
        } else if (pos.asset_type === 'etf') {
          estimatedPrice = 85.00;
        } else if (pos.asset_type === 'bond') {
          estimatedPrice = 100.00;
        } else if (pos.asset_type === 'commodity') {
          if (pos.ticker === 'GOLD') estimatedPrice = 2300.00;
          else estimatedPrice = 80.00;
        } else {
          estimatedPrice = 50.00;
        }

        const quantityNum = Number(pos.quantity);
        const estimatedValue = quantityNum * estimatedPrice;

        return {
          ...pos,
          estimated_price: estimatedPrice,
          estimated_value: estimatedValue
        };
      });
    },

    totalNetWorth(): number {
      return this.computedPositions.reduce((sum, pos) => sum + (pos.estimated_value || 0), 0);
    },

    // Allocations by asset class for beautiful distribution visualizer
    assetAllocations(): { type: string; value: number; percentage: number; color: string }[] {
      const totals: Record<string, number> = {};
      let absoluteTotal = 0;

      const colors: Record<string, string> = {
        stock: '#2563eb',       // Indigo
        crypto: '#7c3aed',      // Purple
        etf: '#0891b2',         // Cyan
        bond: '#0d9488',        // Teal
        cash: '#16a34a',        // Green
        commodity: '#d97706',   // Amber
        fund: '#db2777',        // Pink
        other: '#4b5563'        // Cool Slate
      };

      this.computedPositions.forEach(pos => {
        const val = pos.estimated_value || 0;
        totals[pos.asset_type] = (totals[pos.asset_type] || 0) + val;
        absoluteTotal += val;
      });

      if (absoluteTotal === 0) return [];

      return Object.entries(totals).map(([type, value]) => ({
        type,
        value,
        percentage: (value / absoluteTotal) * 100,
        color: colors[type] || '#64748b'
      })).sort((a, b) => b.value - a.value);
    }
  },

  actions: {
    async fetchAllData() {
      if (!this.isAuthenticated) return;
      this.loading = true;
      this.error = null;
      try {
        const [portfoliosData, positionsData] = await Promise.all([
          api.getPortfolios(),
          api.getPositions(),
        ]);
        this.portfolios = portfoliosData;
        this.positions = positionsData;
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch data';
      } finally {
        this.loading = false;
      }
    },

    async createPortfolio(name: string, description: string = '') {
      this.loading = true;
      try {
        const newPortfolio = await api.createPortfolio(name, description);
        this.portfolios.push(newPortfolio);
        return newPortfolio;
      } catch (err: any) {
        this.error = err.message || 'Failed to create portfolio';
        throw err;
      } finally {
        this.loading = false;
      }
    },

    async deletePortfolio(id: number) {
      this.loading = true;
      try {
        await api.deletePortfolio(id);
        this.portfolios = this.portfolios.filter(p => p.id !== id);
        this.positions = this.positions.filter(pos => pos.portfolio_id !== id);
      } catch (err: any) {
        this.error = err.message || 'Failed to delete portfolio';
        throw err;
      } finally {
        this.loading = false;
      }
    },

    async createPosition(data: {
      portfolio_id: number;
      asset_type: string;
      ticker?: string;
      name: string;
      isin?: string;
      quantity: number;
      currency: string;
    }) {
      this.loading = true;
      try {
        const newPos = await api.createPosition(data);
        this.positions.push(newPos);
        return newPos;
      } catch (err: any) {
        this.error = err.message || 'Failed to create position';
        throw err;
      } finally {
        this.loading = false;
      }
    },

    async deletePosition(id: number) {
      this.loading = true;
      try {
        await api.deletePosition(id);
        this.positions = this.positions.filter(p => p.id !== id);
      } catch (err: any) {
        this.error = err.message || 'Failed to delete position';
        throw err;
      } finally {
        this.loading = false;
      }
    },

    setAuthenticated(status: boolean, email?: string) {
      this.isAuthenticated = status;
      if (email) {
        this.userEmail = email;
      }
    }
  }
});
