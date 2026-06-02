<script setup lang="ts">
import { computed } from 'vue';
import CustomDropdown from './CustomDropdown.vue';

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

const isFieldRelevant = (fieldKey: string, opType: string) => {
  const universal = ['executed_at', 'name', 'total_amount', 'currency', 'transaction_id', 'exchange_rate', 'notes'];
  if (universal.includes(fieldKey)) return true;

  if (opType === 'buy' || opType === 'sell' || opType === 'limit_buy' || opType === 'limit_sell') {
    return ['ticker', 'isin', 'quantity', 'unit_price', 'price_currency', 'fee_amount', 'fee_currency', 'fee_type', 'tax_amount', 'tax_currency', 'limit_price'].includes(fieldKey);
  }
  if (opType === 'dividend') {
    return ['ticker', 'isin', 'unit_price', 'price_currency', 'tax_amount', 'tax_currency'].includes(fieldKey);
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
  return fields;
});

const dropdownOptions = computed(() => {
  return filteredFields.value.map(f => {
    let badgeClass = 'bg-gray-100 text-gray-600';
    if (f.type === 'numeric') badgeClass = 'bg-blue-50 text-blue-600';
    else if (f.type === 'enum') badgeClass = 'bg-amber-50 text-amber-600';
    else if (f.type === 'datetime') badgeClass = 'bg-violet-50 text-violet-600';

    return {
      value: f.key,
      label: f.label,
      rightLabel: f.type,
      rightBadgeClass: badgeClass,
      labelClass: f.is_required ? 'text-red-500 font-semibold' : ''
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
