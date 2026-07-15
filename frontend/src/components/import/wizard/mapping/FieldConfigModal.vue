<script setup lang="ts">
import { computed, onBeforeUnmount, toRef, watch } from 'vue';
import { X, Sparkles, Hash } from '@lucide/vue';
import DynamicComponent from '../../../DynamicComponent.vue';
import NumericTransformations from '../NumericTransformations.vue';
import EnumValueMapper from '../EnumValueMapper.vue';
import DateFormatSelector from '../DateFormatSelector.vue';
import LiveConversionPreview from '../LiveConversionPreview.vue';
import FormulaBuilder from './FormulaBuilder.vue';
import HashColumnsPicker from './HashColumnsPicker.vue';
import { useFieldConfigModal, type FieldConfigContext } from './useFieldConfigModal';
import type { ColMapping, OpTypeSettings } from '../../../../services/import/types';

const props = defineProps<{
  show: boolean;
  context: FieldConfigContext | null;
  headers: string[];
  columnOptions: Array<{ value: string; label: string }>;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'save', payload: { mapping: ColMapping; opTypeSettings?: OpTypeSettings }): void;
  (e: 'clear'): void;
  (e: 'map-ticker', colId: string): void;
}>();

const form = useFieldConfigModal(toRef(props, 'show'), toRef(props, 'context'));

const enrichOptions: Array<{ value: 'never' | 'when_empty' | 'always'; label: string; hint: string }> = [
  { value: 'never', label: 'Never', hint: 'use the raw value only' },
  { value: 'when_empty', label: 'When empty', hint: 'fill in only missing values' },
  { value: 'always', label: 'Always', hint: 'override the raw value' },
];

const isNumeric = computed(() => props.context?.field?.type === 'numeric');
const isEnum = computed(() => props.context?.field?.type === 'enum');
const isDatetime = computed(() => props.context?.field?.type === 'datetime');

const handleSave = () => {
  if (form.isSaveDisabled.value || !props.context) return;
  if (form.tickerColumnPick.value) {
    emit('map-ticker', form.tickerColumnPick.value);
  }
  emit('save', {
    mapping: form.draftMapping.value,
    ...(form.isTransactionId.value
      ? {
          opTypeSettings: {
            autoTransactionId: form.autoTransactionId.value,
            hashColumns: form.hashColumns.value.length ? form.hashColumns.value : undefined,
          },
        }
      : {}),
  });
};

// Capture-phase window listener: Escape closes this modal without bubbling to
// the drawer's own Escape handler.
const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    e.stopPropagation();
    emit('close');
  }
};
watch(() => props.show, (open) => {
  if (open) window.addEventListener('keydown', onKeydown, true);
  else window.removeEventListener('keydown', onKeydown, true);
});
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown, true));
</script>

<template>
  <div
    v-if="show && context"
    class="fixed inset-0 bg-slate-900/20 backdrop-blur-[2px] flex items-center justify-center z-[200]"
    @click.self="emit('close')"
  >
    <div class="bg-bg-primary border border-border-color rounded-md shadow-xl w-[560px] max-w-[94vw] max-h-[88vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center gap-2 py-2.5 px-4 border-b border-border-color">
        <span class="text-[0.9rem] font-bold">{{ context.field?.label }}</span>
        <span class="badge" :class="`badge-${context.opType}`">{{ context.opType }}</span>
        <span v-if="context.mappedHeader" class="text-[0.72rem] font-mono bg-bg-tertiary border border-border-color rounded-sm py-0.5 px-1.5 truncate">
          {{ context.mappedHeader }}
        </span>
        <button type="button" class="ml-auto p-1 rounded-sm text-text-secondary hover:text-text-primary" @click="emit('close')">
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Sections (only those relevant to the field type appear) -->
      <div class="flex-1 overflow-y-auto px-4 pb-2">
        <!-- Source & math -->
        <div v-if="isNumeric" class="mt-4">
          <div class="flex items-center gap-2 mb-2">
            <h5 class="text-[0.8rem] font-bold uppercase text-text-secondary tracking-wider m-0 flex-1">Source & Math</h5>
            <div class="flex rounded-sm border border-border-color overflow-hidden">
              <button
                type="button"
                class="py-1 px-2.5 text-[0.72rem] font-semibold"
                :class="form.sourceMode.value === 'simple' ? 'bg-accent-light text-accent' : 'bg-bg-primary text-text-secondary'"
                @click="form.sourceMode.value = 'simple'"
              >Simple value</button>
              <button
                type="button"
                class="py-1 px-2.5 text-[0.72rem] font-semibold border-l border-border-color"
                :class="form.sourceMode.value === 'formula' ? 'bg-accent-light text-accent' : 'bg-bg-primary text-text-secondary'"
                @click="form.sourceMode.value = 'formula'"
              >ƒ Formula</button>
            </div>
          </div>
          <FormulaBuilder
            v-if="form.sourceMode.value === 'formula'"
            v-model:formula="form.formula.value"
            :headers="headers"
            :exampleRowByHeader="context.exampleRowByHeader"
            :decimalSeparator="context.decimalSeparator"
          />
          <NumericTransformations
            v-else
            v-model:transformationType="form.transformationType.value"
            v-model:transformationValue="form.transformationValue.value"
            class="!mt-0"
          />
        </div>

        <!-- Enum coercion -->
        <EnumValueMapper
          v-if="isEnum"
          v-model:enumMappings="form.enumMappings.value"
          :selectedField="context.field"
          :uniqueCsvValues="context.uniqueCsvValues"
        />

        <!-- Date format -->
        <DateFormatSelector v-if="isDatetime" v-model:dateFormat="form.dateFormat.value" />

        <!-- Auto-ID & hash columns -->
        <div v-if="form.isTransactionId.value" class="mt-4 bg-bg-primary border border-border-color rounded-sm p-3">
          <h5 class="text-[0.8rem] font-bold uppercase text-text-secondary tracking-wider mb-2 flex items-center gap-1.5">
            <Hash class="w-3.5 h-3.5" /> Auto-generated Transaction ID
          </h5>
          <div class="flex flex-col gap-1 mb-2">
            <label v-for="opt in enrichOptions" :key="opt.value" class="flex items-center gap-2 text-[0.78rem] cursor-pointer">
              <input type="radio" :value="opt.value" v-model="form.autoTransactionId.value" class="cursor-pointer" />
              <span class="font-semibold">{{ opt.label }}</span>
              <span class="text-text-tertiary text-[0.7rem]">{{ opt.hint }}</span>
            </label>
          </div>
          <HashColumnsPicker
            v-if="form.autoTransactionId.value !== 'never'"
            v-model:hashColumns="form.hashColumns.value"
            :headers="headers"
          />
        </div>

        <!-- Asset-name enrichment -->
        <div v-if="form.isName.value" class="mt-4 bg-bg-primary border border-border-color rounded-sm p-3">
          <h5 class="text-[0.8rem] font-bold uppercase text-text-secondary tracking-wider mb-2 flex items-center gap-1.5">
            <Sparkles class="w-3.5 h-3.5 text-amber-500" /> Auto-enrich Asset Name
          </h5>
          <p class="text-[0.72rem] text-text-secondary mt-0 mb-2">
            Looks up the full asset name from the ticker when the file value is missing.
          </p>
          <div class="flex flex-col gap-1">
            <label
              v-for="opt in enrichOptions"
              :key="opt.value"
              class="flex items-center gap-2 text-[0.78rem]"
              :class="opt.value !== 'never' && form.needsTickerPrompt.value && form.enrichAssetNames.value === 'never' ? 'opacity-60' : 'cursor-pointer'"
            >
              <input type="radio" :value="opt.value" v-model="form.enrichAssetNames.value" class="cursor-pointer" />
              <span class="font-semibold">{{ opt.label }}</span>
              <span class="text-text-tertiary text-[0.7rem]">{{ opt.hint }}</span>
            </label>
          </div>
          <!-- Ticker dependency prompt -->
          <div
            v-if="form.needsTickerPrompt.value"
            class="mt-2 border border-amber-400/60 bg-amber-50/60 dark:bg-amber-500/10 rounded-sm p-2"
          >
            <p class="text-[0.72rem] text-amber-700 font-semibold m-0 mb-1.5">
              Enrichment needs a ticker column for "{{ context.opType }}" — pick it now:
            </p>
            <DynamicComponent
              componentKey="custom-dropdown"
              v-model="form.tickerColumnPick.value"
              :options="columnOptions"
              :searchable="true"
              placeholder="-- Select the Ticker column --"
              :compact="true"
            />
          </div>
        </div>

        <!-- Live preview -->
        <LiveConversionPreview :liveConversion="form.liveConversion.value" :shouldShake="false" />
      </div>

      <!-- Footer -->
      <div class="flex items-center gap-2 py-2.5 px-4 border-t border-border-color">
        <button type="button" class="btn btn-sm text-danger-color" @click="emit('clear')">Clear mapping</button>
        <div class="flex-1"></div>
        <button type="button" class="btn btn-sm" @click="emit('close')">Cancel</button>
        <button type="button" class="btn btn-sm btn-primary" :disabled="form.isSaveDisabled.value" @click="handleSave">Save</button>
      </div>
    </div>
  </div>
</template>
