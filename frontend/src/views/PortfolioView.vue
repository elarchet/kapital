<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useKapitalStore } from '../store';
import { assetKey, useValuationStore } from '../store/valuation';
import DynamicComponent from '../components/DynamicComponent.vue';
import ImportTransactionsModal from '../components/import/ImportTransactionsModal.vue';
import StrategyHoldingsTable from '../components/portfolio/StrategyHoldingsTable.vue';
import PortfolioValueChart from '../components/portfolio/PortfolioValueChart.vue';
import PortfolioAllocationDonut from '../components/portfolio/PortfolioAllocationDonut.vue';
import PositionTransactionsDrawer from '../components/portfolio/PositionTransactionsDrawer.vue';
import TransactionSplitModal from '../components/portfolio/TransactionSplitModal.vue';
import { useConfirmModal } from '../composables/useConfirmModal';
import { Loader, ArrowLeft, Grid, Trash2 } from '@lucide/vue';
import type { PositionValuation, RangeKey, RawTransaction } from '../services/portfolioApi';

const route = useRoute();
const router = useRouter();
const store = useKapitalStore();
const valuationStore = useValuationStore();

const showCreatePosModal = ref(false);
const showImportModal = ref(false);
const initialImportFiles = ref<File[] | null>(null);

// Rename title states
const isEditingTitle = ref(false);
const editingTitleName = ref('');
const titleInput = ref<HTMLInputElement | null>(null);

// Drilldown / split tool states. "Position" here is an asset row: one asset,
// possibly aggregating several underlying positions (position_ids).
const selectedPosition = ref<PositionValuation | null>(null);
const splitTransaction = ref<RawTransaction | null>(null);

// Opens the import wizard on its empty state: the user picks new files there
// or re-imports a previously stored one.
const triggerImportFile = () => {
  initialImportFiles.value = null;
  showImportModal.value = true;
};

const portfolioId = computed<number | 'unassigned'>(() => {
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

const valuation = computed(() => valuationStore.valuation);
const positions = computed(() => valuation.value?.positions ?? []);
const currency = computed(() => valuation.value?.currency ?? 'EUR');

const drawerTransactions = computed(() =>
  selectedPosition.value
    ? valuationStore.transactionsByAsset[assetKey(selectedPosition.value.position_ids)] ?? []
    : []
);

const refreshValuation = async () => {
  valuationStore.clearDrilldownCache();
  await valuationStore.fetchValuation(portfolioId.value);
};

const handleRangeChange = async (range: RangeKey) => {
  await valuationStore.fetchValuation(portfolioId.value, range);
};

onMounted(async () => {
  await Promise.all([store.fetchAllData(), valuationStore.fetchValuation(portfolioId.value)]);
});

watch(() => (route.params as Record<string, string>).id, async () => {
  // Clear transient states when changing portfolios
  showCreatePosModal.value = false;
  showImportModal.value = false;
  isEditingTitle.value = false;
  selectedPosition.value = null;
  splitTransaction.value = null;
  await refreshValuation();
});

const { popupState, triggerPopup, handlePopupConfirm, handlePopupCancel } = useConfirmModal();

const handleManualSuccess = async () => {
  showCreatePosModal.value = false;
  await Promise.all([store.fetchAllData(), refreshValuation()]);
};

const handleImportSuccess = async () => {
  await Promise.all([store.fetchAllData(), refreshValuation()]);
};

// ---- Row drilldown -> transactions drawer -> split modal --------------------

const handleSelectPosition = async (position: PositionValuation) => {
  selectedPosition.value = position;
  await valuationStore.fetchAssetTransactions(position.position_ids);
};

const handleOpenSplit = (transaction: RawTransaction) => {
  splitTransaction.value = transaction;
};

const handleSplitSaved = async () => {
  splitTransaction.value = null;
  await store.fetchAllData();
  // Keep the drawer in sync: after a split the asset rows may have regrouped,
  // so re-find the row sharing a constituent position with the selected one.
  const previous = selectedPosition.value;
  if (previous) {
    const refreshed = valuation.value?.positions.find(p =>
      p.position_ids.some(id => previous.position_ids.includes(id))
    );
    selectedPosition.value = refreshed ?? null;
    if (refreshed) await valuationStore.fetchAssetTransactions(refreshed.position_ids, true);
  }
};

// ---- Existing header / position management flows ---------------------------

const handleDeletePosition = (position: PositionValuation) => {
  const count = position.position_ids.length;
  triggerPopup({
    title: 'Delete Asset?',
    message: count > 1
      ? `This asset aggregates ${count} positions — all of them will be permanently deleted from your strategy folders.`
      : 'Are you sure you want to permanently delete this asset position from your strategy folder?',
    confirmText: count > 1 ? `Delete ${count} Positions` : 'Delete Position',
    cancelText: 'Cancel',
    variant: 'danger',
    onConfirm: async () => {
      try {
        for (const id of position.position_ids) {
          await store.deletePosition(id);
        }
        await refreshValuation();
      } catch (err: any) {
        triggerPopup({
          title: 'Error Deleting Position',
          message: err.message || 'An unexpected failure occurred while trying to delete the position.',
          confirmText: 'OK',
          variant: 'danger',
          hideCancel: true,
        });
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

const handleMovePosition = async (position: PositionValuation, targetPortfolioId: number) => {
  if (!targetPortfolioId) return;
  try {
    for (const id of position.position_ids) {
      await store.movePosition(id, targetPortfolioId);
    }
    await refreshValuation();
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
      <div v-if="store.loading && !store.portfolios.length" class="empty-state flex-1">
        <Loader class="animate-spin w-10 h-10 text-accent" />
        <p class="mt-4 font-medium">Aggregating portfolios...</p>
      </div>

      <!-- Strategy not found fallback -->
      <div v-else-if="!portfolio" class="empty-state flex-1 pt-24">
        <Grid class="empty-icon text-color-danger" />
        <h3>Strategy Folder Not Found</h3>
        <p class="text-sm max-w-[340px] mt-2 mb-6">
          The requested portfolio folder has either been removed or you do not have sufficient authorization levels to view it.
        </p>
        <router-link to="/" class="btn btn-sm btn-primary">
          <ArrowLeft class="w-3.5 h-3.5" />
          <span>Back to Global View</span>
        </router-link>
      </div>

      <!-- Active Portfolio view -->
      <template v-else>
        <!-- Page Header -->
        <header class="page-header">
          <div class="page-title-group">
            <h1 class="flex items-center gap-2">
              <router-link to="/" class="text-text-tertiary flex items-center" title="Back to Global Dashboard">
                <ArrowLeft class="w-5 h-5" />
              </router-link>

              <span v-if="portfolioId === 'unassigned'">{{ portfolio.name }}</span>
              <template v-else>
                <input
                  v-if="isEditingTitle"
                  ref="titleInput"
                  v-model="editingTitleName"
                  class="bg-bg-tertiary text-text-primary border-0 outline-none ring-0 px-2 py-0 rounded w-full font-bold tracking-tight leading-none text-[1.75rem]"
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
          <div class="flex gap-3">
            <button v-if="portfolioId !== 'unassigned'" @click="handleDeletePortfolio" class="btn btn-danger" title="Delete Portfolio">
              <Trash2 class="w-4 h-4" />
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

        <!-- Bento layout: value hero (headline + chart) | allocation rail, then the asset table -->
        <div class="dashboard-content mt-6 flex flex-col gap-5">
          <div class="grid grid-cols-1 xl:grid-cols-3 gap-5">
            <div class="xl:col-span-2 min-w-0">
              <PortfolioValueChart
                :series="valuation?.series ?? []"
                :current="valuation?.current ?? null"
                :currency="currency"
                :loading="valuationStore.loading"
                :range="valuationStore.range"
                @update:range="handleRangeChange"
              />
            </div>
            <div class="min-w-0">
              <PortfolioAllocationDonut
                :allocation="valuation?.allocation ?? []"
                :currency="currency"
              />
            </div>
          </div>

          <!-- Repartition table: one row per asset, click to inspect transactions -->
          <StrategyHoldingsTable
            :positions="positions"
            :portfolioId="portfolioId"
            :portfolios="store.portfolios"
            :currency="currency"
            @select-position="handleSelectPosition"
            @delete-position="handleDeletePosition"
            @move-position="({ position, targetPortfolioId }) => handleMovePosition(position, targetPortfolioId)"
            @open-add-modal="showCreatePosModal = true"
          />
        </div>

        <!-- Transactions drawer for the clicked asset row -->
        <PositionTransactionsDrawer
          v-if="selectedPosition"
          :position="selectedPosition"
          :transactions="drawerTransactions"
          :allocations-by-transaction="valuationStore.allocationsByTransaction"
          :loading="valuationStore.transactionsLoading"
          @close="selectedPosition = null"
          @open-split="handleOpenSplit"
        />

        <!-- Split tool over the drawer -->
        <TransactionSplitModal
          v-if="splitTransaction && selectedPosition"
          :transaction="splitTransaction"
          :allocations="valuationStore.allocationsByTransaction[splitTransaction.id] ?? []"
          :portfolios="store.portfolios"
          :portfolio-id="portfolioId"
          :position-id="selectedPosition.position_id"
          :position-ids="selectedPosition.position_ids"
          @close="splitTransaction = null"
          @saved="handleSplitSaved"
        />

        <!-- Add Position Modal -->
        <DynamicComponent
          componentKey="create-position-modal"
          v-if="showCreatePosModal"
          :portfolio="portfolio"
          @close="showCreatePosModal = false"
          @success="handleManualSuccess"
        />

        <!-- Import Positions Modal. Stays open on success so the summary screen
             shows; its Done button emits close. -->
        <ImportTransactionsModal
          v-if="showImportModal"
          :portfolio="portfolio"
          :initialFiles="initialImportFiles"
          @close="() => { showImportModal = false; initialImportFiles = null; }"
          @success="handleImportSuccess"
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
