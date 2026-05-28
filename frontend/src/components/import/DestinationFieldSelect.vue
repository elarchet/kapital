<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  importFields: Array<{
    key: string;
    label: string;
    is_required: boolean;
    type: string;
    enum_values?: string[];
  }>;
  activeOpType: string;
}>();

const selectedDbKey = defineModel<string>('selectedDbKey', { required: true });

const isDropdownOpen = ref(false);
const searchQuery = ref('');

const selectedField = computed(() => {
  return props.importFields.find(f => f.key === selectedDbKey.value);
});

const isFieldRelevant = (fieldKey: string, opType: string) => {
  const universal = ['executed_at', 'name', 'total_amount', 'currency', 'transaction_id', 'exchange_rate', 'notes'];
  if (universal.includes(fieldKey)) return true;

  if (opType === 'buy' || opType === 'sell' || opType === 'limit_buy' || opType === 'limit_sell') {
    return ['ticker', 'isin', 'quantity', 'unit_price', 'fee_amount', 'fee_currency', 'fee_type', 'tax_amount', 'tax_currency', 'limit_price'].includes(fieldKey);
  }
  if (opType === 'dividend') {
    return ['ticker', 'isin', 'unit_price', 'tax_amount', 'tax_currency'].includes(fieldKey);
  }
  if (opType === 'interest') {
    return [];
  }
  if (opType === 'transfer_in') {
    return ['source_reference'].includes(fieldKey);
  }
  if (opType === 'transfer_out') {
    return ['destination_reference', 'fee_amount', 'fee_currency', 'fee_type'].includes(fieldKey);
  }
  if (opType === 'expense' || opType === 'revenue') {
    return ['merchant_name', 'merchant_category', 'tax_amount', 'tax_currency'].includes(fieldKey);
  }
  if (opType === 'fx_rate_change') {
    return ['source_currency', 'target_currency', 'source_reference', 'destination_reference'].includes(fieldKey);
  }
  if (opType === 'stock_split') {
    return ['ticker', 'isin', 'quantity'].includes(fieldKey);
  }
  if (opType === 'fee') {
    return ['fee_amount', 'fee_currency', 'fee_type'].includes(fieldKey);
  }
  if (opType === 'tax') {
    return ['tax_amount', 'tax_currency'].includes(fieldKey);
  }
  return true;
};

const filteredFields = computed(() => {
  let fields = props.importFields;
  if (props.activeOpType) {
    fields = fields.filter(f => isFieldRelevant(f.key, props.activeOpType));
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase();
    fields = fields.filter(f => f.label.toLowerCase().includes(q) || f.key.toLowerCase().includes(q));
  }
  return fields;
});

const toggleDropdown = () => {
  isDropdownOpen.value = !isDropdownOpen.value;
  searchQuery.value = '';
};

const selectField = (key: string) => {
  selectedDbKey.value = key;
  isDropdownOpen.value = false;
};
</script>

<template>
  <div class="form-group" style="margin-top: 1.25rem; position: relative;">
    <label>Database Destination Field</label>
    <div class="custom-select-container">
      <button type="button" @click="toggleDropdown" class="custom-select-trigger">
        <span v-if="selectedField" :style="{ color: selectedField.is_required ? 'var(--color-danger)' : 'var(--text-primary)', fontWeight: selectedField.is_required ? '600' : 'normal' }">
          {{ selectedField.label }}
        </span>
        <span v-else style="color: var(--text-tertiary);">-- Ignore Column (Do Not Map) --</span>
        <span v-if="selectedField" class="type-badge" :class="'type-' + selectedField.type">{{ selectedField.type }}</span>
        <span class="chevron-arrow">&#9662;</span>
      </button>

      <!-- Dropdown Options Panel -->
      <div v-if="isDropdownOpen" class="custom-select-dropdown">
        <input 
          type="text" 
          v-model="searchQuery" 
          class="form-control select-search-input" 
          placeholder="Search destination fields..."
          @click.stop
        />
        <div class="custom-select-options">
          <div 
            @click="selectField('')" 
            class="custom-select-option"
            :class="{ active: selectedDbKey === '' }"
          >
            <span style="color: var(--text-tertiary); font-size: 0.8rem;">-- Ignore Column (Do Not Map) --</span>
          </div>
          <div 
            v-for="field in filteredFields" 
            :key="field.key"
            @click="selectField(field.key)" 
            class="custom-select-option"
            :class="{ active: selectedDbKey === field.key }"
          >
            <span :style="{ color: field.is_required ? 'var(--color-danger)' : 'var(--text-primary)', fontWeight: field.is_required ? '600' : 'normal' }">
              {{ field.label }}
            </span>
            <span class="type-badge" :class="'type-' + field.type">{{ field.type }}</span>
          </div>
          <div v-if="filteredFields.length === 0" style="padding: 1rem; text-align: center; color: var(--text-tertiary); font-size: 0.8rem;">
            No fields match query.
          </div>
        </div>
      </div>

      <!-- Intercept outside click backdrop -->
      <div v-if="isDropdownOpen" class="custom-select-backdrop" @click="isDropdownOpen = false"></div>
    </div>
  </div>
</template>

<style scoped>
.custom-select-container {
  position: relative;
  width: 100%;
}

.custom-select-trigger {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  outline: none;
  transition: all var(--transition-fast);
  text-align: left;
}

.custom-select-trigger:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px var(--accent-light);
}

.chevron-arrow {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.custom-select-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  margin-top: 0.25rem;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg);
  z-index: 160;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.select-search-input {
  padding: 0.5rem;
  font-size: 0.8rem;
}

.custom-select-options {
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.custom-select-option {
  padding: 0.5rem 0.75rem;
  font-size: 0.85rem;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background-color var(--transition-fast);
}

.custom-select-option:hover {
  background-color: var(--bg-tertiary);
}

.custom-select-option.active {
  background-color: var(--accent-light);
  color: var(--accent-color);
}

.custom-select-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 150;
  background: transparent;
}

.type-badge {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  letter-spacing: 0.02em;
}

.type-numeric { background-color: #eff6ff; color: #2563eb; }
.type-enum { background-color: #fffbeb; color: #d97706; }
.type-datetime { background-color: #f5f3ff; color: #7c3aed; }
.type-string { background-color: #f3f4f6; color: #4b5563; }
</style>
