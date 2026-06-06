<script setup lang="ts">
import { computed } from 'vue';
import CustomDropdown from './CustomDropdown.vue';
import { isFieldRequiredForOpType } from '../../services/import/validation';

const props = defineProps<{
  importFields: Array<{
    key: string;
    label: string;
    is_required: boolean;
    type: string;
    enum_values?: string[];
  }>;
  activeOpType: string;
  activeOpTypes?: string[];
}>();

const selectedDbKey = defineModel<string>('selectedDbKey', { required: true });

const isFieldRequired = (fieldKey: string) => {
  const field = props.importFields.find(f => f.key === fieldKey);
  if (field?.is_required) return true;
  
  if (props.activeOpType) {
    return isFieldRequiredForOpType(fieldKey, props.activeOpType);
  }
  if (props.activeOpTypes && props.activeOpTypes.length > 0) {
    return props.activeOpTypes.some(op => isFieldRequiredForOpType(fieldKey, op));
  }
  return false;
};

const isFieldRelevant = (fieldKey: string, opType: string) => {
  const universal = ['executed_at', 'name', 'total_amount', 'currency', 'transaction_id', 'exchange_rate', 'notes'];
  if (universal.includes(fieldKey)) return true;

  if (opType === 'trade') {
    return ['ticker', 'isin', 'quantity', 'unit_price', 'price_currency', 'fee_amount', 'fee_currency', 'fee_type', 'tax_amount', 'tax_currency', 'trade_side', 'order_type', 'order_status', 'limit_price', 'stop_price', 'execution_price', 'order_placed_at', 'filled_at'].includes(fieldKey);
  }
  if (opType === 'dividend') {
    return ['ticker', 'isin', 'unit_price', 'price_currency', 'tax_amount', 'tax_currency'].includes(fieldKey);
  }
  if (opType === 'interest') {
    return ['interest_type'].includes(fieldKey);
  }
  if (opType === 'transfer_in') {
    return ['source_reference'].includes(fieldKey);
  }
  if (opType === 'transfer_out') {
    return ['destination_reference', 'fee_amount', 'fee_currency', 'fee_type'].includes(fieldKey);
  }
  if (opType === 'expense') {
    return ['merchant_name', 'merchant_category', 'tax_amount', 'tax_currency', 'expense_category', 'payment_method'].includes(fieldKey);
  }
  if (opType === 'revenue') {
    return ['merchant_name', 'merchant_category', 'tax_amount', 'tax_currency', 'revenue_category', 'payment_method'].includes(fieldKey);
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
  // Sort required fields first
  return [...fields].sort((a, b) => {
    const aReq = isFieldRequired(a.key);
    const bReq = isFieldRequired(b.key);
    if (aReq && !bReq) return -1;
    if (!aReq && bReq) return 1;
    return 0;
  });
});

const dropdownOptions = computed(() => {
  return filteredFields.value.map(f => {
    let badgeClass = 'bg-gray-100 text-gray-600';
    if (f.type === 'numeric') badgeClass = 'bg-blue-50 text-blue-600';
    else if (f.type === 'enum') badgeClass = 'bg-amber-50 text-amber-600';
    else if (f.type === 'datetime') badgeClass = 'bg-violet-50 text-violet-600';

    const isRequired = isFieldRequired(f.key);

    return {
      value: f.key,
      label: f.label,
      rightLabel: f.type,
      rightBadgeClass: badgeClass,
      labelClass: isRequired ? 'text-red-500 font-semibold' : ''
    };
  });
});
</script>

<template>
  <div style="margin-top: 0.5rem; margin-bottom: 0.5rem;">
    <CustomDropdown
      v-model="selectedDbKey"
      :options="dropdownOptions"
      placeholder="-- Ignore Column (Do Not Map) --"
      searchPlaceholder="Search destination fields..."
      label="Database Destination Field"
      :showClear="true"
      clearLabel="-- Ignore Column (Do Not Map) --"
      :compact="true"
    />
  </div>
</template>
