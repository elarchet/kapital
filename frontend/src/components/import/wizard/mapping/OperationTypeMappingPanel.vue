<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ChevronDown, ChevronRight, CheckCircle, AlertTriangle } from '@lucide/vue';
import DynamicComponent from '../../../DynamicComponent.vue';

const props = defineProps<{
  uniqueOperationTypes: string[];
  operationTypeMappings: Record<string, string>;
  importFields: any[];
  rowCountsByRawAction: Record<string, number>;
  splitOpTypes: string[];
}>();

const emit = defineEmits<{
  (e: 'update-optype-mapping', payload: { rawAction: string; dbOpType: string }): void;
  (e: 'toggle-split', payload: { opType: string; enabled: boolean }): void;
  (e: 'preview-rows', rawAction: string): void;
}>();

// DB types fed by 2+ raw actions can be mapped once for the whole group (default)
// or split so each raw action gets its own column mappings in step 2.
const multiActionGroups = computed(() => {
  const byType: Record<string, string[]> = {};
  props.uniqueOperationTypes.forEach(raw => {
    const t = props.operationTypeMappings[raw];
    if (t) (byType[t] ||= []).push(raw);
  });
  return Object.entries(byType)
    .filter(([, raws]) => raws.length >= 2)
    .map(([opType, raws]) => ({ opType, raws }));
});

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

    <div v-if="!collapsed" class="border-t border-border-color p-2 flex flex-col gap-1.5 max-h-[40vh] overflow-y-auto">
      <div
        v-for="rawAction in uniqueOperationTypes"
        :key="rawAction"
        :data-testid="`optype-row-${rawAction}`"
        class="grid grid-cols-[1fr_auto_1fr] gap-2 items-center"
      >
        <span
          class="text-[0.75rem] font-mono bg-bg-tertiary py-1 px-2 rounded-sm border border-border-color flex items-center gap-1 min-w-0"
          :title="rawAction"
        >
          <span class="truncate">{{ rawAction }}</span>
          <button
            type="button"
            class="text-text-tertiary hover:text-accent hover:underline cursor-pointer shrink-0"
            :data-testid="`optype-count-${rawAction}`"
            title="Show the file rows with this action"
            @click.stop="emit('preview-rows', rawAction)"
          >({{ rowCountsByRawAction?.[rawAction] ?? 0 }})</button>
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

    <!-- Split/merge choice per DB type fed by several raw actions. Stays visible
         when the rows list is collapsed so the option remains discoverable. -->
    <div v-if="multiActionGroups.length" class="border-t border-border-color py-2 px-3 flex flex-col gap-1">
      <div
        v-for="group in multiActionGroups"
        :key="group.opType"
        class="flex items-center gap-2 text-[0.72rem]"
      >
        <span class="badge" :class="`badge-${group.opType}`">{{ group.opType }}</span>
        <span class="text-text-secondary">{{ group.raws.length }} file actions</span>
        <label class="ml-auto flex items-center gap-1.5 cursor-pointer font-medium" :title="`Off: all ${group.opType} actions share one column mapping. On: configure columns per action in step 2.`">
          <input
            type="checkbox"
            class="w-3.5 h-3.5 cursor-pointer"
            :data-testid="`split-toggle-${group.opType}`"
            :checked="splitOpTypes.includes(group.opType)"
            @change="emit('toggle-split', { opType: group.opType, enabled: ($event.target as HTMLInputElement).checked })"
          />
          <span>Map each action separately</span>
        </label>
      </div>
    </div>
  </div>
</template>
