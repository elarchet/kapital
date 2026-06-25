import { defineStore } from 'pinia';
import { api } from '../services/api';
import { SIDEBAR_CONFIG } from '../config/sidebar';

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
    sidebarWidth: Number(localStorage.getItem('sidebarWidth')) || SIDEBAR_CONFIG.DEFAULT_WIDTH,
    sidebarCollapsed: localStorage.getItem('sidebarCollapsed') === 'true',
  }),

  getters: {
    // Aggregated net worth (mocking current prices since DB stores quantity and currency)
    // In a production fintech app, quantities would be multiplied by real-time tickers.
    // We will apply sensible mock pricing rules based on asset types for high visual premium fidelity.
    computedPositions(state): Position[] {
      return state.positions.map(pos => {
        // Temporary mock price (in production, use real-time tickers)
        const estimatedPrice = pos.asset_type === 'cash' ? 1.0 : 100.0;
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
    },

    hasUnassignedPositions(state): boolean {
      const activeIds = new Set(state.portfolios.map(p => p.id));
      return state.positions.some(pos => !activeIds.has(pos.portfolio_id));
    }
  },

  actions: {
    setSidebarWidth(width: number) {
      const clampedWidth = Math.max(SIDEBAR_CONFIG.MIN_WIDTH, Math.min(SIDEBAR_CONFIG.MAX_WIDTH, width));
      this.sidebarWidth = clampedWidth;
      localStorage.setItem('sidebarWidth', String(clampedWidth));
    },
    setSidebarCollapsed(collapsed: boolean) {
      this.sidebarCollapsed = collapsed;
      localStorage.setItem('sidebarCollapsed', String(collapsed));
    },
    toggleSidebar() {
      this.setSidebarCollapsed(!this.sidebarCollapsed);
    },
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
        // Do not filter out positions, they remain in state and become unassigned holdings
      } catch (err: any) {
        this.error = err.message || 'Failed to delete portfolio';
        throw err;
      } finally {
        this.loading = false;
      }
    },

    async movePosition(id: number, portfolioId: number) {
      this.loading = true;
      try {
        await api.updatePosition(id, { portfolio_id: portfolioId });
        const index = this.positions.findIndex(p => p.id === id);
        if (index !== -1) {
          this.positions[index] = { ...this.positions[index], portfolio_id: portfolioId };
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to move position';
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
