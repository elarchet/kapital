<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useKapitalStore } from '../store';
import DynamicComponent from '../components/DynamicComponent.vue';
import { 
  DollarSign, 
  TrendingUp, 
  Layers, 
  Grid,
  Loader,
  Plus,
  Trash2
} from '@lucide/vue';

const store = useKapitalStore();
const showCreatePosModal = ref(false);

// New Position Form fields
const posPortfolioId = ref<number | null>(null);
const posAssetType = ref('stock');
const posTicker = ref('');
const posName = ref('');
const posIsin = ref('');
const posQuantity = ref(1.0);
const posCurrency = ref('EUR');
const isSubmitting = ref(false);
const submitError = ref('');

onMounted(async () => {
  await store.fetchAllData();
  if (store.portfolios.length > 0) {
    posPortfolioId.value = store.portfolios[0].id;
  }
});

const formatCurrency = (val: number, cur: string = 'EUR') => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: cur }).format(val);
};

const handleCreatePosition = async () => {
  if (!posPortfolioId.value || !posName.value.trim() || posQuantity.value <= 0) return;
  isSubmitting.value = true;
  submitError.value = '';
  try {
    await store.createPosition({
      portfolio_id: posPortfolioId.value,
      asset_type: posAssetType.value,
      ticker: posTicker.value.trim() || undefined,
      name: posName.value.trim(),
      isin: posIsin.value.trim() || undefined,
      quantity: posQuantity.value,
      currency: posCurrency.value,
    });
    // Reset form
    posTicker.value = '';
    posName.value = '';
    posIsin.value = '';
    posQuantity.value = 1.0;
    showCreatePosModal.value = false;
  } catch (err: any) {
    submitError.value = err.message || 'Failed to add position.';
  } finally {
    isSubmitting.value = false;
  }
};

const handleDeletePosition = async (id: number) => {
  if (!confirm('Are you sure you want to delete this position?')) return;
  try {
    await store.deletePosition(id);
  } catch (err: any) {
    alert(err.message || 'Failed to delete position.');
  }
};

const getPortfolioName = (id: number) => {
  const p = store.portfolios.find(item => item.id === id);
  return p ? p.name : 'Unknown';
};
</script>

<template>
  <div class="app-container">
    <DynamicComponent componentKey="sidebar" />

    <main class="main-content">
      <!-- Page Header -->
      <header class="page-header">
        <div class="page-title-group">
          <h1>Global Dashboard</h1>
          <p>Consolidated multi-portfolio wealth report</p>
        </div>
        <button 
          @click="showCreatePosModal = true" 
          class="btn btn-primary"
          :disabled="!store.portfolios.length"
        >
          <Plus style="width: 16px; height: 16px;" />
          <span>Add Asset Position</span>
        </button>
      </header>

      <!-- Loading State -->
      <div v-if="store.loading && !store.positions.length" class="empty-state" style="flex: 1;">
        <Loader class="animate-spin w-10 h-10 text-accent" />
        <p style="margin-top: 1rem; font-weight: 500;">Aggregating asset sheets...</p>
      </div>

      <!-- Main Dashboard view -->
      <div v-else class="dashboard-content" style="margin-top: 1.5rem;">
        <!-- KPI Summary Cards -->
        <section class="metrics-grid" style="padding: 0;">
          <div class="card kpi-card">
            <div class="kpi-header">
              <span>CONSOLIDATED NET WORTH</span>
              <DollarSign style="width: 16px; height: 16px; color: var(--text-tertiary);" />
            </div>
            <div class="kpi-value">{{ formatCurrency(store.totalNetWorth) }}</div>
            <div class="kpi-trend up">
              <TrendingUp style="width: 14px; height: 14px;" />
              <span>+3.24% YTD</span>
            </div>
          </div>

          <div class="card kpi-card">
            <div class="kpi-header">
              <span>ACTIVE ASSETS</span>
              <Layers style="width: 16px; height: 16px; color: var(--text-tertiary);" />
            </div>
            <div class="kpi-value">{{ store.positions.length }}</div>
            <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.75rem;">
              Distributed across {{ store.portfolios.length }} custom portfolio strategies
            </p>
          </div>

          <div class="card kpi-card">
            <div class="kpi-header">
              <span>UNREALIZED GAINS</span>
              <TrendingUp style="width: 16px; height: 16px; color: var(--text-tertiary);" />
            </div>
            <div class="kpi-value" style="color: var(--color-success);">
              +{{ formatCurrency(store.totalNetWorth * 0.083) }}
            </div>
            <div class="kpi-trend up" style="background-color: var(--color-success-light); color: var(--color-success);">
              <span>Outperforming benchmarks</span>
            </div>
          </div>
        </section>

        <!-- Visual Asset Allocation Bar -->
        <section class="card" v-if="store.positions.length > 0">
          <h3 class="table-title" style="font-size: 1rem; margin-bottom: 0.25rem;">Consolidated Asset Allocation</h3>
          <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 1rem;">
            Breakdown based on active financial weight
          </p>

          <div class="allocation-bar-container">
            <div class="allocation-bar">
              <div 
                v-for="alloc in store.assetAllocations" 
                :key="alloc.type"
                class="allocation-segment"
                :style="{ width: alloc.percentage + '%', backgroundColor: alloc.color }"
                :title="alloc.type.toUpperCase() + ': ' + alloc.percentage.toFixed(1) + '%'"
              ></div>
            </div>

            <div class="allocation-legend">
              <div v-for="alloc in store.assetAllocations" :key="alloc.type" class="legend-item">
                <span class="legend-color" :style="{ backgroundColor: alloc.color }"></span>
                <span style="text-transform: capitalize; font-weight: 500;">
                  {{ alloc.type }}: {{ alloc.percentage.toFixed(1) }}% ({{ formatCurrency(alloc.value) }})
                </span>
              </div>
            </div>
          </div>
        </section>

        <!-- Positions Table -->
        <section class="table-container">
          <div class="table-header-block">
            <h3 class="table-title">Aggregated Positions</h3>
            <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); background-color: var(--bg-tertiary); padding: 0.25rem 0.5rem; border-radius: var(--radius-sm);">
              {{ store.positions.length }} holdings
            </span>
          </div>

          <div v-if="!store.positions.length" class="empty-state">
            <Grid class="empty-icon" />
            <h3>No asset positions found</h3>
            <p style="font-size: 0.875rem; max-width: 320px; margin-top: 0.5rem; margin-bottom: 1.5rem;">
              Get started by creating a portfolio and adding asset sheets, cash deposits, or stock tokens.
            </p>
            <button 
              @click="showCreatePosModal = true" 
              class="btn btn-sm btn-primary"
              :disabled="!store.portfolios.length"
            >
              Add First Position
            </button>
          </div>

          <div v-else class="table-wrapper">
            <table class="premium-table">
              <thead>
                <tr>
                  <th>Asset Name</th>
                  <th>Class</th>
                  <th>Ticker / ISIN</th>
                  <th>Quantity</th>
                  <th>Est. Unit Price</th>
                  <th>Current Value</th>
                  <th>Strategy Folder</th>
                  <th style="width: 50px;"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pos in store.computedPositions" :key="pos.id">
                  <td style="font-weight: 600;">{{ pos.name }}</td>
                  <td>
                    <span class="badge" :class="'badge-' + pos.asset_type">
                      {{ pos.asset_type }}
                    </span>
                  </td>
                  <td>
                    <code style="font-size: 0.8rem; background-color: var(--bg-tertiary); padding: 0.125rem 0.35rem; border-radius: 4px;">
                      {{ pos.ticker || '—' }}
                    </code>
                    <span v-if="pos.isin" style="color: var(--text-secondary); font-size: 0.75rem; margin-left: 0.5rem;">
                      {{ pos.isin }}
                    </span>
                  </td>
                  <td style="font-family: monospace; font-size: 0.875rem;">{{ pos.quantity }}</td>
                  <td style="font-family: monospace;">{{ formatCurrency(pos.estimated_price || 0, pos.currency) }}</td>
                  <td style="font-weight: 600; font-family: monospace;">
                    {{ formatCurrency(pos.estimated_value || 0, pos.currency) }}
                  </td>
                  <td>
                    <router-link 
                      :to="'/portfolio/' + pos.portfolio_id" 
                      style="color: var(--accent-color); text-decoration: none; font-weight: 500;"
                    >
                      {{ getPortfolioName(pos.portfolio_id) }}
                    </router-link>
                  </td>
                  <td>
                    <button @click="handleDeletePosition(pos.id)" class="btn-logout" title="Remove Position" style="padding: 0.25rem;">
                      <Trash2 style="width: 14px; height: 14px; color: var(--text-tertiary);" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <!-- Add Position Modal -->
      <div v-if="showCreatePosModal" class="modal-overlay">
        <div class="modal-card">
          <div class="modal-header">
            <h3 class="table-title">Add Asset Position</h3>
            <button @click="showCreatePosModal = false" style="background: none; border: none; cursor: pointer; font-size: 1.25rem;">&times;</button>
          </div>
          <div class="modal-body">
            <div v-if="submitError" class="login-error" style="margin-bottom: 1rem;">
              {{ submitError }}
            </div>
            
            <div class="form-group">
              <label for="posPortfolio">Portfolio Strategy</label>
              <select v-model="posPortfolioId" id="posPortfolio" class="form-control" required>
                <option v-for="p in store.portfolios" :key="p.id" :value="p.id">
                  {{ p.name }}
                </option>
              </select>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
              <div class="form-group">
                <label for="posAsset">Asset Class</label>
                <select v-model="posAssetType" id="posAsset" class="form-control">
                  <option value="stock">Stock</option>
                  <option value="crypto">Crypto</option>
                  <option value="etf">ETF</option>
                  <option value="bond">Bond</option>
                  <option value="cash">Cash Deposit</option>
                  <option value="commodity">Commodity</option>
                  <option value="fund">Fund</option>
                  <option value="other">Other Asset</option>
                </select>
              </div>

              <div class="form-group">
                <label for="posCurrency">Currency</label>
                <select v-model="posCurrency" id="posCurrency" class="form-control">
                  <option value="EUR">EUR (€)</option>
                  <option value="USD">USD ($)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="CHF">CHF</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label for="posName">Asset Label / Company Name</label>
              <input 
                v-model="posName" 
                type="text" 
                id="posName" 
                class="form-control" 
                placeholder="e.g. Apple Inc. or Bitcoin Cash" 
                required 
              />
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
              <div class="form-group">
                <label for="posTicker">Ticker Symbol</label>
                <input 
                  v-model="posTicker" 
                  type="text" 
                  id="posTicker" 
                  class="form-control" 
                  placeholder="e.g. AAPL or BTC" 
                />
              </div>

              <div class="form-group">
                <label for="posIsin">ISIN Number</label>
                <input 
                  v-model="posIsin" 
                  type="text" 
                  id="posIsin" 
                  class="form-control" 
                  placeholder="e.g. US0378331005" 
                />
              </div>
            </div>

            <div class="form-group">
              <label for="posQuantity">Quantity / Weight</label>
              <input 
                v-model.number="posQuantity" 
                type="number" 
                step="any"
                id="posQuantity" 
                class="form-control" 
                required 
              />
            </div>
          </div>
          <div class="modal-footer">
            <button @click="showCreatePosModal = false" class="btn btn-sm">Cancel</button>
            <button @click="handleCreatePosition" class="btn btn-sm btn-primary" :disabled="isSubmitting || !posPortfolioId || !posName.trim()">
              <span v-if="isSubmitting">Recording holding...</span>
              <span v-else>Record Holding</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

