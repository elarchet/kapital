<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { useKapitalStore } from '../store';

const props = defineProps<{
  portfolio: {
    id: number;
    name: string;
  };
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'success'): void;
}>();

const store = useKapitalStore();

// Form fields
const posAssetType = ref('stock');
const posTicker = ref('');
const posName = ref('');
const posIsin = ref('');
const posQuantity = ref(1.0);
const posCurrency = ref('EUR');
const isSubmitting = ref(false);
const submitError = ref('');

// Check if form has modifications
const isDirty = computed(() => {
  return (
    posAssetType.value !== 'stock' ||
    posTicker.value.trim() !== '' ||
    posName.value.trim() !== '' ||
    posIsin.value.trim() !== '' ||
    posQuantity.value !== 1.0 ||
    posCurrency.value !== 'EUR'
  );
});

// Safe close method
const requestClose = () => {
  if (isDirty.value) {
    if (confirm('You have unsaved changes. Are you sure you want to discard them?')) {
      emit('close');
    }
  } else {
    emit('close');
  }
};

const handleCreatePosition = async () => {
  if (!props.portfolio.id || !posName.value.trim() || posQuantity.value <= 0) return;
  isSubmitting.value = true;
  submitError.value = '';
  try {
    await store.createPosition({
      portfolio_id: props.portfolio.id,
      asset_type: posAssetType.value,
      ticker: posTicker.value.trim() || undefined,
      name: posName.value.trim(),
      isin: posIsin.value.trim() || undefined,
      quantity: posQuantity.value,
      currency: posCurrency.value,
    });
    
    // Reset form & trigger success
    posTicker.value = '';
    posName.value = '';
    posIsin.value = '';
    posQuantity.value = 1.0;
    emit('success');
  } catch (err: any) {
    submitError.value = err.message || 'Failed to add position.';
  } finally {
    isSubmitting.value = false;
  }
};

// Listeners for Escape key and overlay click
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    requestClose();
  }
};

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown);
});
</script>

<template>
  <div class="modal-overlay" @click.self="requestClose">
    <div class="modal-card">
      <div class="modal-header">
        <h3 class="table-title">Add Asset to "{{ portfolio.name }}"</h3>
        <button @click="requestClose" class="modal-close-btn">&times;</button>
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
        <button @click="requestClose" class="btn btn-sm">Cancel</button>
        <button @click="handleCreatePosition" class="btn btn-sm btn-primary" :disabled="isSubmitting || !posName.trim()">
          <span v-if="isSubmitting">Recording holding...</span>
          <span v-else>Record Holding</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-close-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.25rem;
  color: var(--text-secondary);
  transition: color var(--transition-fast);
}
.modal-close-btn:hover {
  color: var(--text-primary);
}
</style>
