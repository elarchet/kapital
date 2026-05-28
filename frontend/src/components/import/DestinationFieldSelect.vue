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
    <div class="relative w-full">
      <button type="button" @click="toggleDropdown" class="w-full py-3 px-4 text-sm border border-border-color rounded-sm bg-bg-secondary text-text-primary flex justify-between items-center cursor-pointer outline-none transition-all duration-150 ease-in-out text-left focus:border-accent focus:shadow-[0_0_0_3px] focus:shadow-accent-light">
        <span v-if="selectedField" :style="{ color: selectedField.is_required ? 'var(--color-danger)' : 'var(--text-primary)', fontWeight: selectedField.is_required ? '600' : 'normal' }">
          {{ selectedField.label }}
        </span>
        <span v-else style="color: var(--text-tertiary);">-- Ignore Column (Do Not Map) --</span>
        <span v-if="selectedField" class="text-[0.65rem] font-bold uppercase py-0.5 px-1.5 rounded-[4px] tracking-wide" :class="{
          'bg-blue-50 text-blue-600': selectedField.type === 'numeric',
          'bg-amber-50 text-amber-600': selectedField.type === 'enum',
          'bg-violet-50 text-violet-600': selectedField.type === 'datetime',
          'bg-gray-100 text-gray-600': selectedField.type === 'string'
        }">{{ selectedField.type }}</span>
        <span class="text-text-tertiary text-[0.75rem]">&#9662;</span>
      </button>

      <!-- Dropdown Options Panel -->
      <div v-if="isDropdownOpen" class="absolute top-full left-0 w-full mt-1 bg-bg-secondary border border-border-color rounded-sm shadow-lg z-[160] p-2 flex flex-col gap-2">
        <input 
          type="text" 
          v-model="searchQuery" 
          class="form-control p-2 text-[0.8rem]" 
          placeholder="Search destination fields..."
          @click.stop
        />
        <div class="max-h-[400px] overflow-y-auto flex flex-col gap-0.5">
          <div 
            @click="selectField('')" 
            class="py-2 px-3 text-[0.85rem] cursor-pointer rounded-[4px] flex justify-between items-center transition-colors duration-150 ease-in-out hover:bg-bg-tertiary"
            :class="{ 'bg-accent-light text-accent': selectedDbKey === '' }"
          >
            <span style="color: var(--text-tertiary); font-size: 0.8rem;">-- Ignore Column (Do Not Map) --</span>
          </div>
          <div 
            v-for="field in filteredFields" 
            :key="field.key"
            @click="selectField(field.key)" 
            class="py-2 px-3 text-[0.85rem] cursor-pointer rounded-[4px] flex justify-between items-center transition-colors duration-150 ease-in-out hover:bg-bg-tertiary"
            :class="{ 'bg-accent-light text-accent': selectedDbKey === field.key }"
          >
            <span :style="{ color: field.is_required ? 'var(--color-danger)' : 'var(--text-primary)', fontWeight: field.is_required ? '600' : 'normal' }">
              {{ field.label }}
            </span>
            <span class="text-[0.65rem] font-bold uppercase py-0.5 px-1.5 rounded-[4px] tracking-wide" :class="{
              'bg-blue-50 text-blue-600': field.type === 'numeric',
              'bg-amber-50 text-amber-600': field.type === 'enum',
              'bg-violet-50 text-violet-600': field.type === 'datetime',
              'bg-gray-100 text-gray-600': field.type === 'string'
            }">{{ field.type }}</span>
          </div>
          <div v-if="filteredFields.length === 0" style="padding: 1rem; text-align: center; color: var(--text-tertiary); font-size: 0.8rem;">
            No fields match query.
          </div>
        </div>
      </div>

      <!-- Intercept outside click backdrop -->
      <div v-if="isDropdownOpen" class="fixed inset-0 w-screen h-screen z-[150] bg-transparent" @click="isDropdownOpen = false"></div>
    </div>
  </div>
</template>
