<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useKapitalStore } from '../store';
import Sidebar from '../components/Sidebar.vue';
import { 
  DollarSign, 
  TrendingUp, 
  Layers, 
  Grid,
  Loader,
  Trash2,
  Plus,
  ArrowLeft
} from '@lucide/vue';

const route = useRoute();
const router = useRouter();
const store = useKapitalStore();

const showCreatePosModal = ref(false);

// New Position Form fields
const posAssetType = ref('stock');
const posTicker = ref('');
const posName = ref('');
const posIsin = ref('');
const posQuantity = ref(1.0);
const posCurrency = ref('EUR');
const isSubmitting = ref(false);
const submitError = ref('');

const portfolioId = computed(() => Number(route.params.id));

const portfolio = computed(() => {
  return store.portfolios.find(p => p.id === portfolioId.value);
});

const portfolioPositions = computed(() => {
  return store.computedPositions.filter(pos => pos.portfolio_id === portfolioId.value);
});

const portfolioValue = computed(() => {
  return portfolioPositions.value.reduce((sum, pos) => sum + (pos.estimated_value || 0), 0);
});

// Allocations by asset class strictly for this portfolio
const portfolioAllocations = computed(() => {
  const totals: Record<string, number> = {};
  let absoluteTotal = 0;

  const colors: Record<string, string> = {
    stock: '#2563eb',
    crypto: '#7c3aed',
    etf: '#0891b2',
    bond: '#0d9488',
    cash: '#16a34a',
    commodity: '#d97706',
    fund: '#db2777',
    other: '#4b5563'
  };

  portfolioPositions.value.forEach(pos => {
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
});

onMounted(async () => {
  await store.fetchAllData();
});

watch(() => route.params.id, () => {
  // Clear modal and error states when changing portfolios
  showCreatePosModal.value = false;
  submitError.value = '';
});

const formatCurrency = (val: number, cur: string = 'EUR') => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: cur }).format(val);
};

const handleCreatePosition = async () => {
  if (!portfolioId.value || !posName.value.trim() || posQuantity.value <= 0) return;
  isSubmitting.value = true;
  submitError.value = '';
  try {
    await store.createPosition({
      portfolio_id: portfolioId.value,
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

const handleDeletePortfolio = async () => {
  if (!portfolio.value) return;
  if (!confirm(`Are you sure you want to delete the portfolio "${portfolio.value.name}"?\nAll associated positions will also be removed.`)) return;
  try {
    await store.deletePortfolio(portfolioId.value);
    router.push('/');
  } catch (err: any) {
    alert(err.message || 'Failed to delete portfolio.');
  }
};
</script>

<template>
  <div class="app-container">
    <Sidebar />

    <main class="main-content">
      <!-- Loading state if portfolios list is not populated yet -->
      <div v-if="store.loading && !store.portfolios.length" class="empty-state" style="flex: 1;">
        <Loader style="animation: spin 1.5s linear infinite; width: 40px; height: 40px; color: var(--accent-color);" />
        <p style="margin-top: 1rem; font-weight: 500;">Aggregating portfolios...</p>
      </div>

      <!-- Strategy not found fallback -->
      <div v-else-if="!portfolio" class="empty-state" style="flex: 1; padding-top: 6rem;">
        <Grid class="empty-icon" style="color: var(--color-danger);" />
        <h3>Strategy Folder Not Found</h3>
        <p style="font-size: 0.875rem; max-width: 340px; margin-top: 0.5rem; margin-bottom: 1.5rem;">
          The requested portfolio folder has either been removed or you do not have sufficient authorization levels to view it.
        </p>
        <router-link to="/" class="btn btn-sm btn-primary">
          <ArrowLeft style="width: 14px; height: 14px;" />
          <span>Back to Global View</span>
        </router-link>
      </div>

      <!-- Active Portfolio view -->
      <template v-else>
        <!-- Page Header -->
        <header class="page-header">
          <div class="page-title-group">
            <h1 style="display: flex; align-items: center; gap: 0.5rem;">
              <router-link to="/" style="color: var(--text-tertiary); display: flex; align-items: center;" title="Back to Global Dashboard">
                <ArrowLeft style="width: 20px; height: 20px;" />
              </router-link>
              <span>{{ portfolio.name }}</span>
            </h1>
            <p>{{ portfolio.description || 'Custom asset strategy plan' }}</p>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button @click="handleDeletePortfolio" class="btn btn-danger" title="Delete Portfolio">
              <Trash2 style="width: 16px; height: 16px;" />
              <span>Delete Strategy</span>
            </button>
            <button @click="showCreatePosModal = true" class="btn btn-primary">
              <Plus style="width: 16px; height: 16px;" />
              <span>Add Position</span>
            </button>
          </div>
        </header>

        <div class="dashboard-content" style="margin-top: 1.5rem;">
          <!-- Metric Cards specific to this portfolio -->
          <section class="metrics-grid" style="padding: 0;">
            <div class="card kpi-card">
              <div class="kpi-header">
                <span>PORTFOLIO VALUATION</span>
                <DollarSign style="width: 16px; height: 16px; color: var(--text-tertiary);" />
              </div>
              <div class="kpi-value">{{ formatCurrency(portfolioValue) }}</div>
              <div class="kpi-trend up">
                <TrendingUp style="width: 14px; height: 14px;" />
                <span>+4.12% YTD</span>
              </div>
            </div>

            <div class="card kpi-card">
              <div class="kpi-header">
                <span>ASSETS ENROLLED</span>
                <Layers style="width: 16px; height: 16px; color: var(--text-tertiary);" />
              </div>
              <div class="kpi-value">{{ portfolioPositions.length }}</div>
              <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.75rem;">
                Distinct holdings registered in this folder
              </p>
            </div>

            <div class="card kpi-card">
              <div class="kpi-header">
                <span>PORTFOLIO YIELD (EST.)</span>
                <TrendingUp style="width: 16px; height: 16px; color: var(--text-tertiary);" />
              </div>
              <div class="kpi-value" style="color: var(--color-success);">
                +{{ formatCurrency(portfolioValue * 0.091) }}
              </div>
              <div class="kpi-trend up" style="background-color: var(--color-success-light); color: var(--color-success);">
                <span>Exceeding target allocations</span>
              </div>
            </div>
          </section>

          <!-- Visual Portfolio Allocation Bar -->
          <section class="card" v-if="portfolioPositions.length > 0">
            <h3 class="table-title" style="font-size: 1rem; margin-bottom: 0.25rem;">Strategy Asset Allocation</h3>
            <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 1rem;">
              Local distribution of asset weight inside {{ portfolio.name }}
            </p>

            <div class="allocation-bar-container">
              <div class="allocation-bar">
                <div 
                  v-for="alloc in portfolioAllocations" 
                  :key="alloc.type"
                  class="allocation-segment"
                  :style="{ width: alloc.percentage + '%', backgroundColor: alloc.color }"
                  :title="alloc.type.toUpperCase() + ': ' + alloc.percentage.toFixed(1) + '%'"
                ></div>
              </div>

              <div class="allocation-legend">
                <div v-for="alloc in portfolioAllocations" :key="alloc.type" class="legend-item">
                  <span class="legend-color" :style="{ backgroundColor: alloc.color }"></span>
                  <span style="text-transform: capitalize; font-weight: 500;">
                    {{ alloc.type }}: {{ alloc.percentage.toFixed(1) }}% ({{ formatCurrency(alloc.value) }})
                  </span>
                </div>
              </div>
            </div>
          </section>

          <!-- Local Filtered Positions Table -->
          <section class="table-container">
            <div class="table-header-block">
              <h3 class="table-title">Strategy Holdings</h3>
              <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); background-color: var(--bg-tertiary); padding: 0.25rem 0.5rem; border-radius: var(--radius-sm);">
                {{ portfolioPositions.length }} items
              </span>
            </div>

            <div v-if="!portfolioPositions.length" class="empty-state">
              <Grid class="empty-icon" />
              <h3>This strategy folder is empty</h3>
              <p style="font-size: 0.875rem; max-width: 320px; margin-top: 0.5rem; margin-bottom: 1.5rem;">
                No financial sheet registered here. Record stock stocks, cash, or crypto tokens using the button below.
              </p>
              <button @click="showCreatePosModal = true" class="btn btn-sm btn-primary">
                Add Strategy Holding
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
                    <th style="width: 50px;"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="pos in portfolioPositions" :key="pos.id">
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

        <!-- Add Position Modal (Current Portfolio Pre-Selected) -->
        <div v-if="showCreatePosModal" class="modal-overlay">
          <div class="modal-card">
            <div class="modal-header">
              <h3 class="table-title">Add Asset to "{{ portfolio.name }}"</h3>
              <button @click="showCreatePosModal = false" style="background: none; border: none; cursor: pointer; font-size: 1.25rem;">&times;</button>
            </div>
            <div class="modal-body">
              <div v-if="submitError" class="login-error" style="margin-bottom: 1rem;">
                {{ submitError }}
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
              <button @click="handleCreatePosition" class="btn btn-sm btn-primary" :disabled="isSubmitting || !posName.trim()">
                <span v-if="isSubmitting">Recording holding...</span>
                <span v-else>Record Holding</span>
              </button>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
