<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue';
import { CheckCircle, AlertCircle, Trash2 } from '@lucide/vue';
import DiscardChangesConfirmModal from './DiscardChangesConfirmModal.vue';

const props = defineProps<{
  show: boolean;
  csvHeaderName: string;
  exampleValue: string;
  importFields: Array<{
    key: string;
    label: string;
    is_required: boolean;
    type: string;
    enum_values?: string[];
  }>;
  activeOpType: string;
  delimiter: string;
  decimalSeparator: string;
  uniqueCsvValues: string[];
  initialMapping?: {
    dbKey: string;
    scope: 'global' | 'type';
    divisor?: number;
    multiplier?: number;
    enumMappings?: Record<string, string>;
  };
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'clear'): void;
  (e: 'save', payload: {
    dbKey: string;
    scope: 'global' | 'type';
    divisor?: number;
    multiplier?: number;
    enumMappings?: Record<string, string>;
  }): void;
}>();

// Form states
const selectedDbKey = ref('');
const transformationType = ref<'none' | 'divisor' | 'multiplier'>('none');
const transformationValue = ref<number | null>(null);
const enumMappings = ref<Record<string, string>>({});

// Custom dropdown select states
const isDropdownOpen = ref(false);
const searchQuery = ref('');

// Shake animation state
const shouldShake = ref(false);

// Custom exit confirmation state
const showExitConfirm = ref(false);

// Automated scope mapping based on activeOpType prop
const scope = computed<'global' | 'type'>(() => props.activeOpType ? 'type' : 'global');

// Detect unsaved changes (dirty state check)
const isWizardDirty = computed(() => {
  const initial = props.initialMapping;
  const initialKey = initial?.dbKey || '';
  if (selectedDbKey.value !== initialKey) return true;

  // check transformations
  const initialDiv = initial?.divisor;
  const initialMul = initial?.multiplier;
  const currentDiv = transformationType.value === 'divisor' ? transformationValue.value : undefined;
  const currentMul = transformationType.value === 'multiplier' ? transformationValue.value : undefined;
  if (currentDiv !== initialDiv || currentMul !== initialMul) return true;

  // check enum mappings
  const initialEnums = initial?.enumMappings || {};
  const uniqueVals = props.uniqueCsvValues;
  for (const val of uniqueVals) {
    const initialVal = initialEnums[val] || '';
    const currentVal = enumMappings.value[val] || '';
    if (currentVal !== initialVal) return true;
  }

  return false;
});

// Initialize form from props
watch(() => props.show, (newVal) => {
  if (newVal) {
    if (props.initialMapping) {
      selectedDbKey.value = props.initialMapping.dbKey || '';
      if (props.initialMapping.divisor) {
        transformationType.value = 'divisor';
        transformationValue.value = props.initialMapping.divisor;
      } else if (props.initialMapping.multiplier) {
        transformationType.value = 'multiplier';
        transformationValue.value = props.initialMapping.multiplier;
      } else {
        transformationType.value = 'none';
        transformationValue.value = null;
      }
      enumMappings.value = { ...(props.initialMapping.enumMappings || {}) };
    } else {
      selectedDbKey.value = '';
      transformationType.value = 'none';
      transformationValue.value = null;
      enumMappings.value = {};
    }
    isDropdownOpen.value = false;
    searchQuery.value = '';
    showExitConfirm.value = false;
  }
}, { immediate: true });

// Auto-initialize enum values when dbKey changes to an enum type
watch(selectedDbKey, (newKey) => {
  const field = props.importFields.find(f => f.key === newKey);
  if (field && field.type === 'enum') {
    // Retain any existing mappings, and initialize missing ones
    const newMappings: Record<string, string> = {};
    props.uniqueCsvValues.forEach(val => {
      newMappings[val] = enumMappings.value[val] || '';
    });
    enumMappings.value = newMappings;
  }
});

const selectedField = computed(() => {
  return props.importFields.find(f => f.key === selectedDbKey.value);
});

// Helper checking relevance of DB fields to transaction types
const isFieldRelevant = (fieldKey: string, opType: string) => {
  // Universal fields
  const universal = ['executed_at', 'name', 'total_amount', 'currency', 'transaction_id', 'exchange_rate', 'notes'];
  if (universal.includes(fieldKey)) return true;

  // Type specific rules
  if (opType === 'buy' || opType === 'sell' || opType === 'limit_buy' || opType === 'limit_sell') {
    return ['ticker', 'isin', 'quantity', 'unit_price', 'fee_amount', 'fee_currency', 'fee_type', 'tax_amount', 'tax_currency', 'limit_price'].includes(fieldKey);
  }
  if (opType === 'dividend') {
    return ['ticker', 'isin', 'unit_price', 'tax_amount', 'tax_currency'].includes(fieldKey); // note: unit_price resolves to dividend_per_share in backend
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

// Filtered fields based on relevance and search query
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

// Live conversion engine
const liveConversion = computed(() => {
  if (!selectedDbKey.value) {
    return { success: true, value: 'Unmapped (Column ignored)' };
  }

  const rawVal = props.exampleValue;
  if (rawVal === undefined || rawVal === null || rawVal.trim() === '') {
    if (selectedField.value?.is_required) {
      return { success: false, error: 'Example cell is empty but this database field is required.' };
    }
    return { success: true, value: 'Empty value (Ignored)' };
  }

  const fieldType = selectedField.value?.type;

  if (fieldType === 'numeric') {
    // Clean string using selected decimal separator
    let cleaned = rawVal.trim();
    if (props.decimalSeparator !== '.') {
      cleaned = cleaned.replace(props.decimalSeparator, '.');
    }
    // Remove thousands separator: if decimal is dot, strip commas, else strip dots
    if (props.decimalSeparator === '.') {
      cleaned = cleaned.replace(/,/g, '');
    } else {
      cleaned = cleaned.replace(/\./g, '').replace(/\s/g, '');
    }

    let num = parseFloat(cleaned);
    if (isNaN(num)) {
      return { success: false, error: `"${rawVal}" cannot be parsed as a valid numeric decimal.` };
    }

    // Apply transformation
    if (transformationType.value === 'divisor' && transformationValue.value) {
      num /= transformationValue.value;
    } else if (transformationType.value === 'multiplier' && transformationValue.value) {
      num *= transformationValue.value;
    }

    return { success: true, value: num.toString() };
  }

  if (fieldType === 'datetime') {
    const cleaned = rawVal.trim();
    const parsedDate = new Date(cleaned);
    if (isNaN(parsedDate.getTime())) {
      return { success: false, error: `"${rawVal}" cannot be parsed as a valid timestamp.` };
    }
    return { success: true, value: parsedDate.toISOString() };
  }

  if (fieldType === 'enum') {
    const mapped = enumMappings.value[rawVal];
    if (!mapped) {
      return { success: false, error: `Value "${rawVal}" must be mapped to a DB enum option.` };
    }
    return { success: true, value: mapped };
  }

  // default is string
  return { success: true, value: rawVal };
});

const isSaveDisabled = computed(() => {
  if (!selectedDbKey.value) return false;
  if (!liveConversion.value.success) return true;
  
  // If enum, check that the example value is mapped
  if (selectedField.value?.type === 'enum') {
    if (props.exampleValue && props.exampleValue.trim()) {
      if (!enumMappings.value[props.exampleValue]) return true;
    }
  }

  return false;
});

const toggleDropdown = () => {
  isDropdownOpen.value = !isDropdownOpen.value;
  searchQuery.value = '';
};

const selectField = (key: string) => {
  selectedDbKey.value = key;
  isDropdownOpen.value = false;
};

const handleSave = () => {
  if (isSaveDisabled.value) return;

  emit('save', {
    dbKey: selectedDbKey.value,
    scope: scope.value,
    divisor: transformationType.value === 'divisor' ? (transformationValue.value || undefined) : undefined,
    multiplier: transformationType.value === 'multiplier' ? (transformationValue.value || undefined) : undefined,
    enumMappings: selectedField.value?.type === 'enum' ? enumMappings.value : undefined
  });
};

const handleClear = () => {
  emit('clear');
};

const attemptClose = () => {
  if (isWizardDirty.value) {
    showExitConfirm.value = true;
  } else {
    emit('close');
  }
};

// Enter key press triggers mapping application (or shakes conversion card if blocked)
const onEnterPress = () => {
  if (isSaveDisabled.value) {
    shouldShake.value = true;
    setTimeout(() => {
      shouldShake.value = false;
    }, 500);
  } else {
    handleSave();
  }
};

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    onEnterPress();
  } else if (e.key === 'Escape') {
    e.stopPropagation(); // Stop Escape from bubbling to parent modal
    if (showExitConfirm.value) {
      showExitConfirm.value = false;
    } else {
      attemptClose();
    }
  }
};

watch(() => props.show, (newVal) => {
  if (newVal) {
    window.addEventListener('keydown', handleKeyDown, true); // Use capture phase to intercept Escape early
  } else {
    window.removeEventListener('keydown', handleKeyDown, true);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown, true);
});
</script>

<template>
  <div v-if="show" class="wizard-modal-overlay" @click.self="attemptClose">
    <div class="wizard-card" style="position: relative;">
      
      <!-- Custom exit confirmation dialog -->
      <DiscardChangesConfirmModal 
        :show="showExitConfirm" 
        @cancel="showExitConfirm = false" 
        @confirm="emit('close')" 
      />

      <div class="wizard-header">
        <h4 style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">
          {{ activeOpType ? `Configure Mapping for "${activeOpType}"` : 'Configure Global Mapping' }}
        </h4>
        <button @click="attemptClose" class="wizard-close-btn">&times;</button>
      </div>

      <div class="wizard-body">
        <!-- Read-only Column Info -->
        <div class="info-grid">
          <div>
            <div class="info-label">File Column Header</div>
            <div class="info-value">{{ csvHeaderName }}</div>
          </div>
          <div>
            <div class="info-label">Example Cell Value</div>
            <div class="info-value" style="font-family: monospace; background-color: var(--bg-tertiary); padding: 0.15rem 0.4rem; border-radius: 4px; display: inline-block;">
              {{ exampleValue || '—' }}
            </div>
          </div>
        </div>

        <!-- Custom Dropdown Select Destination Field -->
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

        <!-- Dynamic options based on target type -->
        <template v-if="selectedField">
          <!-- Transformations for numeric fields -->
          <div v-if="selectedField.type === 'numeric'" class="options-container">
            <h5 class="options-title">Numeric Data Transformations</h5>
            <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 1rem; align-items: center;">
              <select v-model="transformationType" class="form-control">
                <option value="none">No transformation (Direct parse)</option>
                <option value="divisor">Divide value by...</option>
                <option value="multiplier">Multiply value by...</option>
              </select>
              <div v-if="transformationType !== 'none'" style="display: flex; align-items: center; gap: 0.5rem;">
                <input 
                  type="number" 
                  v-model.number="transformationValue" 
                  class="form-control" 
                  placeholder="e.g. 100" 
                  min="0.00001" 
                  required
                />
                <span style="font-size: 0.75rem; color: var(--text-secondary); white-space: nowrap;">
                  (e.g., scale GBX to GBP)
                </span>
              </div>
            </div>
          </div>

          <!-- Enum Mapper for enum fields -->
          <div v-if="selectedField.type === 'enum'" class="options-container">
            <h5 class="options-title">Map Unique CSV Values to Database Enums</h5>
            <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
              The file column contains raw labels. Map each unique label below to standard database option.
            </p>
            <div class="enum-scroll-list">
              <div v-for="val in uniqueCsvValues" :key="val" class="enum-row">
                <span class="enum-raw-badge" :title="val">{{ val || '—' }}</span>
                <select 
                  v-model="enumMappings[val]" 
                  class="form-control" 
                  style="font-size: 0.75rem; padding: 0.25rem 0.5rem; height: auto;"
                >
                  <option value="">-- Choose Option --</option>
                  <option v-for="opt in selectedField.enum_values || []" :key="opt" :value="opt">
                    {{ opt }}
                  </option>
                </select>
              </div>
              <div v-if="uniqueCsvValues.length === 0" style="text-align: center; padding: 1rem; color: var(--text-tertiary); font-size: 0.8rem;">
                No unique values found in this column.
              </div>
            </div>
          </div>
        </template>

        <!-- Live Conversion Preview Section -->
        <div 
          class="preview-box" 
          :class="{ 
            'preview-success': liveConversion.success, 
            'preview-error': !liveConversion.success,
            'shake-anim': shouldShake 
          }"
        >
          <div style="display: flex; align-items: flex-start; gap: 0.5rem;">
            <CheckCircle v-if="liveConversion.success" style="width: 18px; height: 18px; color: var(--color-success); flex-shrink: 0; margin-top: 0.1rem;" />
            <AlertCircle v-else style="width: 18px; height: 18px; color: var(--color-danger); flex-shrink: 0; margin-top: 0.1rem;" />
            <div>
              <div class="preview-heading">Live Conversion Preview</div>
              <div class="preview-result">
                <span v-if="liveConversion.success" style="font-weight: 600; color: var(--text-primary);">
                  {{ liveConversion.value }}
                </span>
                <span v-else style="color: var(--color-danger); font-size: 0.8rem;">
                  {{ liveConversion.error }}
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <div class="wizard-footer">
        <button v-if="initialMapping && initialMapping.dbKey" @click="handleClear" class="btn btn-sm btn-danger-icon" title="Remove mapping">
          <Trash2 style="width: 14px; height: 14px; color: var(--color-danger);" />
          <span>Clear Mapping</span>
        </button>
        <div style="flex-grow: 1;"></div>
        <button @click="attemptClose" class="btn btn-sm">Cancel</button>
        <button 
          @click="handleSave" 
          class="btn btn-sm btn-primary" 
          :disabled="isSaveDisabled"
        >
          Apply Mapping
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wizard-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(15, 23, 42, 0.2);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  z-index: 200;
  animation: fadeIn var(--transition-fast) forwards;
  overflow-y: auto;
  padding: 4rem 1rem;
}

.wizard-card {
  width: 100%;
  max-width: 600px;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  animation: slideUp 0.2s ease-out;
  overflow: visible; /* Allows custom dropdown menu to overlay outside without clipping */
}

.wizard-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--bg-secondary);
  border-top-left-radius: var(--radius-md);
  border-top-right-radius: var(--radius-md);
}

.wizard-close-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.5rem;
  color: var(--text-secondary);
  line-height: 1;
}

.wizard-close-btn:hover {
  color: var(--text-primary);
}

.wizard-body {
  padding: 1.5rem;
  overflow: visible; /* Prevent scrollbar container clipping */
  min-height: 280px; /* Ensure sufficient space for the custom select dropdown list */
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  background-color: var(--bg-primary);
  padding: 0.75rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.info-label {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.15rem;
}

.info-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
}

.options-container {
  margin-top: 1.25rem;
  background-color: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 1rem;
}

.options-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.enum-scroll-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 160px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0.5rem;
  background-color: var(--bg-secondary);
}

.enum-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  align-items: center;
}

.enum-raw-badge {
  font-size: 0.75rem;
  font-family: monospace;
  background-color: var(--bg-tertiary);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid var(--border-color);
}

.preview-box {
  margin-top: 1.25rem;
  border-radius: var(--radius-sm);
  padding: 0.75rem 1rem;
  border: 1px solid transparent;
  transition: transform 0.15s ease;
}

.preview-success {
  background-color: var(--color-success-light);
  border-color: rgba(16, 185, 129, 0.2);
}

.preview-error {
  background-color: var(--color-danger-light);
  border-color: rgba(239, 68, 68, 0.2);
}

.preview-heading {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
}

.preview-result {
  font-size: 0.875rem;
  margin-top: 0.15rem;
}

.wizard-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background-color: var(--bg-primary);
  border-bottom-left-radius: var(--radius-md);
  border-bottom-right-radius: var(--radius-md);
}

.btn-danger-icon {
  background: none;
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: var(--color-danger);
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.btn-danger-icon:hover {
  background-color: var(--color-danger-light);
  border-color: var(--color-danger);
}

/* Custom Select Dropdown System */
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

/* Colored Type Badges */
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

/* Delightful Shaking animation on key errors */
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-6px); }
  20%, 40%, 60%, 80% { transform: translateX(6px); }
}

.shake-anim {
  animation: shake 0.4s ease-in-out;
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
</style>
