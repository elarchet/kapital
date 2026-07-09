<script setup lang="ts">
import { watch, onBeforeUnmount, ref, nextTick } from 'vue';
import { Trash2 } from '@lucide/vue';
import DiscardChangesConfirmModal from '../modals/DiscardChangesConfirmModal.vue';
import DestinationFieldSelect from './DestinationFieldSelect.vue';
import NumericTransformations from './NumericTransformations.vue';
import EnumValueMapper from './EnumValueMapper.vue';
import LiveConversionPreview from './LiveConversionPreview.vue';
import DateFormatSelector from './DateFormatSelector.vue';
import { useColumnMappingWizard } from './useColumnMappingWizard';

const wizardContainerRef = ref<HTMLElement | null>(null);

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
  activeOpTypes?: string[];
  delimiter: string;
  decimalSeparator: string;
  uniqueCsvValues: string[];
  initialMapping?: {
    dbKey: string;
    scope: 'global' | 'type';
    divisor?: number;
    multiplier?: number;
    enumMappings?: Record<string, string>;
    dateFormat?: string;
  };
  uiColumns?: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }>;
  columnConfigMap?: Record<string, { typeSpecific: Record<string, any> }>;
  exampleRow?: string[];
  operationTypeMappings?: Record<string, string>;
  currentColId?: string;
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
    dateFormat?: string;
    enrichAssetNames?: 'never' | 'when_empty' | 'always';
    enrichTransactionIds?: 'never' | 'when_empty' | 'always';
  }): void;
}>();

const {
  selectedDbKey,
  transformationType,
  transformationValue,
  enumMappings,
  dateFormat,
  shouldShake,
  showExitConfirm,
  selectedField,
  isTickerMapped,
  hasPartialTickerMapping,
  liveConversion,
  isSaveDisabled,
  localEnrichAssetNames,
  localEnrichTransactionIds,
  handleSave,
  handleClear,
  attemptClose,
  handleKeyDown,
} = useColumnMappingWizard(props, emit);

watch(() => props.show, (newVal) => {
  if (newVal) {
    window.addEventListener('keydown', handleKeyDown, true); // Use capture phase to intercept Escape early
    nextTick(() => {
      if (wizardContainerRef.value) {
        const btn = wizardContainerRef.value.querySelector('.overflow-y-auto button') as HTMLButtonElement;
        if (btn) btn.focus();
      }
    });
  } else {
    window.removeEventListener('keydown', handleKeyDown, true);
  }
}, { immediate: true });

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown, true);
});
</script>

<template>
  <div v-if="show" class="fixed inset-0 w-screen h-screen bg-slate-900/20 backdrop-blur-[2px] flex items-center justify-center z-[200] px-2 sm:px-4 animate-[fadeIn_0.15s_ease-out_forwards]" @click.self="attemptClose">
    <div ref="wizardContainerRef" class="w-full max-w-[650px] max-h-[92vh] bg-bg-secondary border border-border-color rounded-md shadow-lg flex flex-col overflow-hidden animate-[slideUp_0.2s_ease-out]" style="position: relative;">
      
      <!-- Custom exit confirmation dialog -->
      <DiscardChangesConfirmModal 
        :show="showExitConfirm" 
        @cancel="showExitConfirm = false" 
        @confirm="emit('close')" 
      />

      <div class="py-4 px-6 border-b border-border-color flex justify-between items-center bg-bg-secondary rounded-t-md shrink-0">
        <h4 style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">
          {{ activeOpType ? `Configure Mapping for "${activeOpType}"` : 'Configure Global Mapping' }}
        </h4>
        <button @click="attemptClose" class="bg-transparent border-0 cursor-pointer text-2xl text-text-secondary leading-none hover:text-text-primary">&times;</button>
      </div>

      <div class="p-4 sm:p-6 overflow-y-auto flex-1 min-h-0">
        <!-- Read-only Column Info -->
        <div class="grid grid-cols-2 gap-4 bg-bg-primary py-3 px-4 rounded-sm border border-border-color">
          <div>
            <div class="text-[0.65rem] font-bold text-text-tertiary uppercase tracking-wider mb-0.5">File Column Header</div>
            <div class="text-[0.85rem] font-semibold text-text-primary">{{ csvHeaderName }}</div>
          </div>
          <div>
            <div class="text-[0.65rem] font-bold text-text-tertiary uppercase tracking-wider mb-0.5">Example Cell Value</div>
            <div class="text-[0.85rem] font-semibold text-text-primary" style="font-family: monospace; background-color: var(--bg-tertiary); padding: 0.15rem 0.4rem; border-radius: 4px; display: inline-block;">
              {{ exampleValue || '—' }}
            </div>
          </div>
        </div>

        <!-- Custom Dropdown Select Destination Field -->
        <DestinationFieldSelect
          v-model:selectedDbKey="selectedDbKey"
          :importFields="importFields"
          :activeOpType="activeOpType"
          :activeOpTypes="activeOpTypes"
          :columnConfigMap="columnConfigMap"
          :currentColId="currentColId"
          :uiColumns="uiColumns"
          :operationTypeMappings="operationTypeMappings"
        />

        <!-- Dynamic options based on target type -->
        <template v-if="selectedField">
          <!-- Transformations for numeric fields -->
          <NumericTransformations
            v-if="selectedField.type === 'numeric'"
            v-model:transformationType="transformationType"
            v-model:transformationValue="transformationValue"
          />

          <!-- Date format options for datetime fields -->
          <DateFormatSelector
            v-if="selectedField.type === 'datetime'"
            v-model:dateFormat="dateFormat"
          />

          <!-- Enum Mapper for enum fields -->
          <EnumValueMapper
            v-slot:default
            v-if="selectedField.type === 'enum'"
            :selectedField="selectedField"
            :uniqueCsvValues="uniqueCsvValues"
            v-model:enumMappings="enumMappings"
          />

          <!-- Auto-Enrichment Option for Asset Name field -->
          <div v-if="selectedDbKey === 'name'" style="margin-top: 1rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600; color: var(--text-primary);">
              Auto-Enrich Asset Names
            </label>
            <p style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.1rem; margin-bottom: 0.5rem;">
              Choose when to automatically fetch asset names using the ticker (requires Ticker column mapped).
            </p>
            
            <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.25rem;">
              <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; color: var(--text-primary); cursor: pointer;" :style="{ opacity: isTickerMapped ? 1 : 0.5 }">
                <input type="radio" value="when_empty" v-model="localEnrichAssetNames" :disabled="!isTickerMapped" />
                <span>Only when empty (blank in file)</span>
              </label>
              <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; color: var(--text-primary); cursor: pointer;" :style="{ opacity: isTickerMapped ? 1 : 0.5 }">
                <input type="radio" value="always" v-model="localEnrichAssetNames" :disabled="!isTickerMapped" />
                <span>Always (overwrite name from file)</span>
              </label>
            </div>
            
            <p v-if="!isTickerMapped" style="font-size: 0.65rem; color: var(--color-warning); font-weight: 500; margin-top: 0.25rem;">
              ⚠️ Ticker column must be mapped first to use auto-enrichment.
            </p>
            <p v-else-if="hasPartialTickerMapping" style="font-size: 0.65rem; color: var(--color-warning); font-weight: 500; margin-top: 0.25rem;">
              ⚠️ Ticker column is not mapped for some of the selected transaction types. Auto-enrichment will only apply to types with a mapped ticker.
            </p>
          </div>

          <!-- Auto-Generate Option for Transaction ID field -->
          <div v-if="selectedDbKey === 'transaction_id'" style="margin-top: 1rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
            <label style="font-size: 0.8rem; font-weight: 600; color: var(--text-primary);">
              Auto-Generate Transaction IDs
            </label>
            <p style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.1rem; margin-bottom: 0.5rem;">
              Choose when to automatically generate deterministic transaction IDs (based on all row fields).
            </p>
            
            <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.25rem;">
              <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; color: var(--text-primary); cursor: pointer;">
                <input type="radio" value="when_empty" v-model="localEnrichTransactionIds" />
                <span>Only when empty (blank in file)</span>
              </label>
              <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; color: var(--text-primary); cursor: pointer;">
                <input type="radio" value="always" v-model="localEnrichTransactionIds" />
                <span>Always (overwrite ID from file)</span>
              </label>
            </div>
          </div>
        </template>

        <!-- Live Conversion Preview Section -->
        <LiveConversionPreview
          :liveConversion="liveConversion"
          :shouldShake="shouldShake"
        />

      </div>

      <div class="py-4 px-6 border-t border-border-color flex justify-end gap-3 bg-bg-primary shrink-0">
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
@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
</style>
