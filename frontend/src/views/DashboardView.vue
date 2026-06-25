<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useKapitalStore } from '../store';
import DynamicComponent from '../components/DynamicComponent.vue';
import PortfolioAllocationBar from '../components/portfolio/PortfolioAllocationBar.vue';
import ConsolidatedHoldingsTable from '../components/portfolio/ConsolidatedHoldingsTable.vue';
import PortfolioKpisGrid from '../components/portfolio/PortfolioKpisGrid.vue';
import { useConfirmModal } from '../composables/useConfirmModal';
import { 
  Loader,
  Plus
} from '@lucide/vue';

const store = useKapitalStore();
const showCreatePosModal = ref(false);
const { popupState, triggerPopup, handlePopupConfirm, handlePopupCancel } = useConfirmModal();

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
    triggerPopup({
      title: 'Error Creating Position',
      message: err.message || 'An unexpected failure occurred while trying to record the position.',
      confirmText: 'OK',
      variant: 'danger',
      hideCancel: true,
    });
  } finally {
    isSubmitting.value = false;
  }
};

const positionToDelete = ref<number | null>(null);

const handleDeletePosition = (id: number) => {
  positionToDelete.value = id;
  triggerPopup({
    title: 'Delete Position?',
    message: 'Are you sure you want to permanently delete this asset position from your strategy folder?',
    confirmText: 'Delete Position',
    cancelText: 'Cancel',
    variant: 'danger',
    onConfirm: async () => {
      if (positionToDelete.value === null) return;
      try {
        await store.deletePosition(positionToDelete.value);
      } catch (err: any) {
        triggerPopup({
          title: 'Error Deleting Position',
          message: err.message || 'An unexpected failure occurred while trying to delete the position.',
          confirmText: 'OK',
          variant: 'danger',
          hideCancel: true,
        });
      } finally {
        positionToDelete.value = null;
      }
    }
  });
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
      <div v-else class="dashboard-content mt-6">
        <!-- KPI Summary Cards -->
        <PortfolioKpisGrid 
          :value="store.totalNetWorth"
          :positions-count="store.positions.length"
          :is-consolidated="true"
          :yield-multiplier="0.083"
        />

        <!-- Visual Asset Allocation Bar -->
        <PortfolioAllocationBar 
          :allocations="store.assetAllocations"
          title="Consolidated Asset Allocation"
          description="Breakdown based on active financial weight"
        />

        <!-- Positions Table -->
        <ConsolidatedHoldingsTable 
          :positions="store.computedPositions"
          :portfolios="store.portfolios"
          @delete-position="handleDeletePosition"
          @open-add-modal="showCreatePosModal = true"
        />
      </div>

      <div v-if="showCreatePosModal" class="modal-overlay">
        <div class="modal-card">
          <div class="modal-header">
            <h3 class="table-title">Add Asset Position</h3>
            <button @click="showCreatePosModal = false" class="bg-transparent border-0 cursor-pointer text-xl">&times;</button>
          </div>
          <div class="modal-body">
            <div v-if="submitError" class="login-error mb-4">
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

            <div class="grid grid-cols-2 gap-4">
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

            <div class="grid grid-cols-2 gap-4">
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

      <!-- Unified Premium Modal / Alert Popup -->
      <DynamicComponent
        componentKey="base-confirm-modal"
        :show="popupState.show"
        :title="popupState.title"
        :message="popupState.message"
        :confirmText="popupState.confirmText"
        :cancelText="popupState.cancelText"
        :variant="popupState.variant"
        :hideCancel="popupState.hideCancel"
        @confirm="handlePopupConfirm"
        @cancel="handlePopupCancel"
      />
    </main>
  </div>
</template>

