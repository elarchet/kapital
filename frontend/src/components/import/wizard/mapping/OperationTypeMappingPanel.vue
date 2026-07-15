<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ChevronDown, ChevronRight, CheckCircle, AlertTriangle } from '@lucide/vue';
import DynamicComponent from '../../../DynamicComponent.vue';

const props = defineProps<{
  uniqueOperationTypes: string[];
  operationTypeMappings: Record<string, string>;
  importFields: any[];
  rowCountsByRawAction: Record<string, number>;
}>();

const emit = defineEmits<{
  (e: 'update-optype-mapping', payload: { rawAction: string; dbOpType: string }): void;
}>();

const opTypeOptions = computed(() => {
  const opField = props.importFields.find(f => f?.key === 'operation_type');
  return (opField?.enum_values || []).map((v: string) => ({
    value: v,
    label: v,
    rightLabel: 'type',
    rightBadgeClass: `badge badge-${v}`
  }));
});

const unmappedCount = computed(() =>
  props.uniqueOperationTypes.filter(raw => !props.operationTypeMappings[raw]).length
);

// Collapsed by default once every raw action is mapped (e.g. template reload).
const collapsed = ref(unmappedCount.value === 0 && props.uniqueOperationTypes.length > 0);
watch(unmappedCount, (val, oldVal) => {
  if (oldVal > 0 && val === 0) collapsed.value = true;
});

const modelFor = (rawAction: string) => ({
  get: () => props.operationTypeMappings[rawAction] || '',
  set: (val: string) => emit('update-optype-mapping', { rawAction, dbOpType: val })
});
</script>

<template>
  <div class="border border-border-color rounded-md bg-bg-primary">
    <button
      type="button"
      class="w-full flex items-center gap-2 py-2 px-3 text-left"
      @click="collapsed = !collapsed"
    >
      <component :is="collapsed ? ChevronRight : ChevronDown" class="w-4 h-4 text-text-secondary shrink-0" />
      <span class="text-[0.75rem] font-bold uppercase tracking-wider text-text-secondary flex-1">
        Transaction Types — match your file's actions
      </span>
      <span v-if="unmappedCount === 0" class="flex items-center gap-1 text-[0.7rem] text-success-color font-semibold">
        <CheckCircle class="w-3.5 h-3.5" /> {{ uniqueOperationTypes.length }} mapped
      </span>
      <span v-else class="flex items-center gap-1 text-[0.7rem] text-warning-color font-semibold">
        <AlertTriangle class="w-3.5 h-3.5" /> {{ unmappedCount }} unmapped
      </span>
    </button>

    <div v-if="!collapsed" class="border-t border-border-color p-2 flex flex-col gap-1.5 max-h-[30vh] overflow-y-auto">
      <div
        v-for="rawAction in uniqueOperationTypes"
        :key="rawAction"
        class="grid grid-cols-[1fr_auto_1fr] gap-2 items-center"
      >
        <span
          class="text-[0.75rem] font-mono bg-bg-tertiary py-1 px-2 rounded-sm truncate border border-border-color"
          :title="rawAction"
        >
          {{ rawAction }}
          <span class="text-text-tertiary">({{ rowCountsByRawAction?.[rawAction] ?? 0 }})</span>
        </span>
        <span class="text-text-tertiary text-xs">→</span>
        <DynamicComponent
          componentKey="custom-dropdown"
          :modelValue="modelFor(rawAction).get()"
          :options="opTypeOptions"
          :searchable="true"
          placeholder="-- Ignore --"
          :showClear="true"
          clearLabel="-- Ignore these rows --"
          :compact="true"
          @update:modelValue="(val: string) => modelFor(rawAction).set(val)"
        />
      </div>
    </div>
  </div>
</template>
