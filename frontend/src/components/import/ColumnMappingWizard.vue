<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue';
import { Trash2 } from '@lucide/vue';
import DiscardChangesConfirmModal from './DiscardChangesConfirmModal.vue';
import DestinationFieldSelect from './DestinationFieldSelect.vue';
import NumericTransformations from './NumericTransformations.vue';
import EnumValueMapper from './EnumValueMapper.vue';
import LiveConversionPreview from './LiveConversionPreview.vue';
import DateFormatSelector from './DateFormatSelector.vue';
import { parseDateTimeWithFormat } from '../../services/import/validation';

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
  }): void;
}>();

// Form states
const selectedDbKey = ref('');
const transformationType = ref<'none' | 'divisor' | 'multiplier'>('none');
const transformationValue = ref<number | null>(null);
const enumMappings = ref<Record<string, string>>({});
const dateFormat = ref('auto');

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

  // check date format
  const initialDateFormat = initial?.dateFormat || 'auto';
  if (dateFormat.value !== initialDateFormat) return true;

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
      dateFormat.value = props.initialMapping.dateFormat || 'auto';
    } else {
      selectedDbKey.value = '';
      transformationType.value = 'none';
      transformationValue.value = null;
      enumMappings.value = {};
      dateFormat.value = 'auto';
    }
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
    const parsedDate = parseDateTimeWithFormat(cleaned, dateFormat.value);
    if (!parsedDate) {
      return { success: false, error: `"${rawVal}" cannot be parsed as a valid timestamp with format "${dateFormat.value}".` };
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

const handleSave = () => {
  if (isSaveDisabled.value) return;

  emit('save', {
    dbKey: selectedDbKey.value,
    scope: scope.value,
    divisor: transformationType.value === 'divisor' ? (transformationValue.value || undefined) : undefined,
    multiplier: transformationType.value === 'multiplier' ? (transformationValue.value || undefined) : undefined,
    enumMappings: selectedField.value?.type === 'enum' ? enumMappings.value : undefined,
    dateFormat: selectedField.value?.type === 'datetime' ? dateFormat.value : undefined
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
  <div v-if="show" class="fixed inset-0 w-screen h-screen bg-slate-900/20 backdrop-blur-[2px] flex items-center justify-center z-[200] px-2 sm:px-4 animate-[fadeIn_0.15s_ease-out_forwards]" @click.self="attemptClose">
    <div class="w-full max-w-[650px] max-h-[92vh] bg-bg-secondary border border-border-color rounded-md shadow-lg flex flex-col overflow-hidden animate-[slideUp_0.2s_ease-out]" style="position: relative;">
      
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
