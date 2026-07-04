<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useKapitalStore } from '../store';
import DynamicComponent from '../components/DynamicComponent.vue';
import ImportTransactionsModal from '../components/import/ImportTransactionsModal.vue';
import StrategyHoldingsTable from '../components/portfolio/StrategyHoldingsTable.vue';
import PortfolioAllocationBar from '../components/portfolio/PortfolioAllocationBar.vue';
import PortfolioKpisGrid from '../components/portfolio/PortfolioKpisGrid.vue';
import { useConfirmModal } from '../composables/useConfirmModal';
import { Loader, ArrowLeft } from '@lucide/vue';

const route = useRoute();
const router = useRouter();
const store = useKapitalStore();

const showCreatePosModal = ref(false);
const showImportModal = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const initialImportFile = ref<File | null>(null);

// Rename title states
const isEditingTitle = ref(false);
const editingTitleName = ref('');
const titleInput = ref<HTMLInputElement | null>(null);

const triggerImportFile = () => {
  if (fileInput.value) {
    fileInput.value.value = '';
    fileInput.value.click();
  }
};

const onFileSelected = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    initialImportFile.value = target.files[0];
    showImportModal.value = true;
  }
};

const portfolioId = computed(() => {
  const params = route.params as Record<string, string>;
  const idParam = params.id;
  if (idParam === 'unassigned') return 'unassigned';
  return Number(idParam);
});

const portfolio = computed(() => {
  if (portfolioId.value === 'unassigned') {
    return {
      id: 'unassigned' as any,
      name: 'Unassigned Holdings',
      description: 'Default pool for positions from deleted strategy folders',
      created_at: new Date().toISOString(),
    };
  }
  return store.portfolios.find(p => p.id === portfolioId.value);
});

const portfolioPositions = computed(() => {
  if (portfolioId.value === 'unassigned') {
    const activeIds = new Set(store.portfolios.map(p => p.id));
    return store.computedPositions.filter(pos => !activeIds.has(pos.portfolio_id));
  }
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

watch(() => (route.params as Record<string, string>).id, () => {
  // Clear modal states when changing portfolios
  showCreatePosModal.value = false;
  showImportModal.value = false;
  isEditingTitle.value = false;
});

const { popupState, triggerPopup, handlePopupConfirm, handlePopupCancel } = useConfirmModal();

const handleManualSuccess = async () => {
  showCreatePosModal.value = false;
  await store.fetchAllData();
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

const handleDeletePortfolio = () => {
  if (!portfolio.value) return;
  triggerPopup({
    title: 'Delete Strategy?',
    message: `Are you sure you want to delete the strategy folder '${portfolio.value.name}'? All associated positions will also be permanently removed.`,
    confirmText: 'Delete Strategy',
    cancelText: 'Cancel',
    variant: 'danger',
    onConfirm: confirmDeletePortfolio,
  });
};

const confirmDeletePortfolio = async () => {
  if (!portfolio.value || portfolioId.value === 'unassigned') return;
  try {
    await store.deletePortfolio(portfolioId.value);
    router.push('/');
  } catch (err: any) {
    triggerPopup({
      title: 'Error Deleting Strategy',
      message: err.message || 'Failed to remove the strategy portfolio folder.',
      confirmText: 'OK',
      variant: 'danger',
      hideCancel: true,
    });
  }
};

const handleMovePosition = async (posId: number, targetPortfolioId: number) => {
  if (!targetPortfolioId) return;
  try {
    await store.movePosition(posId, targetPortfolioId);
  } catch (err: any) {
    triggerPopup({
      title: 'Error Moving Position',
      message: err.message || 'Failed to move position to the selected strategy.',
      confirmText: 'OK',
      variant: 'danger',
      hideCancel: true,
    });
  }
};

const startRenameTitle = () => {
  if (portfolioId.value === 'unassigned') return;
  isEditingTitle.value = true;
  editingTitleName.value = portfolio.value?.name || '';
  nextTick(() => {
    if (titleInput.value) {
      titleInput.value.focus();
      titleInput.value.select();
    }
  });
};

const saveRenameTitle = async () => {
  if (!isEditingTitle.value) return;
  const trimmed = editingTitleName.value.trim();
  if (!trimmed || trimmed === portfolio.value?.name) {
    isEditingTitle.value = false;
    return;
  }
  try {
    await store.updatePortfolio(Number(portfolioId.value), { name: trimmed });
  } catch (err) {
    console.error('Failed to rename portfolio from title:', err);
  } finally {
    isEditingTitle.value = false;
  }
};
</script>

<template>
  <div class="app-container">
    <DynamicComponent componentKey="sidebar" />

    <main class="main-content">
      <!-- Loading state if portfolios list is not populated yet -->
      <div v-if="store.loading && !store.portfolios.length" class="empty-state" style="flex: 1;">
        <Loader class="animate-spin w-10 h-10 text-accent" />
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
              
              <span v-if="portfolioId === 'unassigned'">{{ portfolio.name }}</span>
              <template v-else>
                <input
                  v-if="isEditingTitle"
                  ref="titleInput"
                  v-model="editingTitleName"
                  class="bg-bg-tertiary text-text-primary border-0 outline-none ring-0 px-2 py-0 rounded w-full font-bold tracking-tight leading-none"
                  style="font: inherit; font-size: 1.75rem;"
                  @keydown.enter="saveRenameTitle"
                  @keydown.esc="isEditingTitle = false"
                  @blur="saveRenameTitle"
                />
                <span 
                  v-else 
                  @dblclick="startRenameTitle" 
                  class="cursor-pointer select-none"
                  title="Double click to rename"
                >
                  {{ portfolio.name }}
                </span>
              </template>
            </h1>
            <p>{{ portfolio.description || 'Custom asset strategy plan' }}</p>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button v-if="portfolioId !== 'unassigned'" @click="handleDeletePortfolio" class="btn btn-danger" title="Delete Portfolio">
              <Trash2 style="width: 16px; height: 16px;" />
              <span>Delete Strategy</span>
            </button>
            <DynamicComponent 
              v-if="portfolioId !== 'unassigned'"
              componentKey="add-position-button"
              @open-manual="showCreatePosModal = true" 
              @open-import="triggerImportFile" 
            />
          </div>
        </header>


        <div class="dashboard-content mt-6">
          <!-- Metric Cards specific to this portfolio -->
          <PortfolioKpisGrid 
            :value="portfolioValue"
            :positions-count="portfolioPositions.length"
            :is-consolidated="false"
            :yield-multiplier="0.091"
          />

          <!-- Visual Portfolio Allocation Bar -->
          <PortfolioAllocationBar 
            :allocations="portfolioAllocations"
            :portfolioName="portfolio.name"
          />

          <!-- Local Filtered Positions Table -->
          <StrategyHoldingsTable 
            :positions="portfolioPositions"
            :portfolioId="portfolioId"
            :portfolios="store.portfolios"
            @delete-position="handleDeletePosition"
            @move-position="({ posId, targetPortfolioId }) => handleMovePosition(posId, targetPortfolioId)"
            @open-add-modal="showCreatePosModal = true"
          />
        </div>

        <!-- Add Position Modal -->
        <DynamicComponent 
          componentKey="create-position-modal"
          v-if="showCreatePosModal" 
          :portfolio="portfolio" 
          @close="showCreatePosModal = false" 
          @success="handleManualSuccess" 
        />

        <!-- Hidden file input for direct upload -->
        <input 
          type="file" 
          ref="fileInput" 
          accept=".csv" 
          style="display: none;" 
          @change="onFileSelected" 
        />

        <!-- Import Positions Modal -->
        <ImportTransactionsModal 
          v-if="showImportModal" 
          :portfolio="portfolio" 
          :initialFile="initialImportFile"
          @close="() => { showImportModal = false; initialImportFile = null; }" 
          @success="() => { store.fetchAllData(); showImportModal = false; initialImportFile = null; }" 
        />

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
      </template>
    </main>
  </div>
</template>

