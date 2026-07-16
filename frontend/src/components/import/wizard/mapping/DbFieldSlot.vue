<script setup lang="ts">
import { computed, ref } from 'vue';
import { Settings2, X, Sparkles, Hash, SigmaSquare } from '@lucide/vue';
import DynamicComponent from '../../../DynamicComponent.vue';
import type { FieldSlotView } from './useFieldSlots';
import type { LivePreviewResult } from '../../../../services/import';

const props = defineProps<{
  slotView: FieldSlotView;
  exampleValue?: string;
  preview: LivePreviewResult | null;
  dropEnabled: boolean;
  columnOptions: Array<{ value: string; label: string }>;
  autoIdEnabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'drop-column', payload: DragEvent): void;
  (e: 'assign', colId: string): void;
  (e: 'clear'): void;
  (e: 'configure'): void;
  (e: 'slot-click'): void;
}>();

const dragOver = ref(false);

const isTransactionId = computed(() => props.slotView?.field?.key === 'transaction_id');
const isMapped = computed(() => !!props.slotView?.mapping?.dbKey || !!props.slotView?.mapping?.formula?.length);
// transaction_id is configurable (auto-ID + hash columns) even with no column mapped.
const showConfigure = computed(() => isMapped.value || isTransactionId.value);

const typeBadgeClass = computed(() => ({
  numeric: 'bg-blue-50 text-blue-600',
  enum: 'bg-amber-50 text-amber-600',
  datetime: 'bg-violet-50 text-violet-600',
  string: 'bg-slate-100 text-slate-600',
}[props.slotView?.field?.type || 'string']));

const onDrop = (e: DragEvent) => {
  dragOver.value = false;
  emit('drop-column', e);
};
</script>

<template>
  <div
    class="group/slot rounded-md border transition-colors h-full"
    :data-testid="`field-slot-${slotView?.field?.key}`"
    :class="[
      dragOver ? 'border-accent ring-2 ring-accent/30 bg-accent-light/60'
        : isMapped ? 'border-border-color bg-bg-primary'
        : slotView?.isRequired ? 'border-dashed border-red-400/70 bg-bg-primary'
        : 'border-dashed border-border-color bg-bg-primary/60',
      dropEnabled ? 'cursor-pointer' : ''
    ]"
    @dragover.prevent="dragOver = true"
    @dragleave="dragOver = false"
    @drop.prevent="onDrop"
    @click="emit('slot-click')"
  >
    <div class="flex flex-col gap-1 py-1.5 px-2.5 h-full">
      <!-- Field identity + actions -->
      <div class="flex items-center gap-1.5 min-w-0">
        <span class="text-[0.78rem] font-semibold truncate" :class="slotView?.isRequired && !isMapped ? 'text-danger-color' : ''">
          {{ slotView?.field?.label }}
        </span>
        <span v-if="slotView?.isRequired" class="text-danger-color font-bold" title="Required field">*</span>
        <span class="inline-block text-[0.6rem] font-semibold uppercase rounded-sm px-1 py-px shrink-0" :class="typeBadgeClass">
          {{ slotView?.field?.type }}
        </span>
        <!-- Actions -->
        <div class="ml-auto flex items-center gap-0.5 shrink-0" @click.stop>
          <button
            v-if="showConfigure"
            type="button"
            class="p-1 rounded-sm text-text-secondary hover:text-accent hover:bg-accent-light"
            title="Advanced settings (formula, enums, hashing, enrichment)"
            @click="emit('configure')"
          >
            <Settings2 class="w-4 h-4" />
          </button>
          <button
            v-if="isMapped"
            type="button"
            class="p-1 rounded-sm text-text-secondary hover:text-danger-color hover:bg-danger-light"
            title="Clear mapping"
            @click="emit('clear')"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Mapping state -->
      <div class="min-w-0">
        <template v-if="isMapped">
          <div class="flex items-center gap-1.5 min-w-0 flex-wrap">
            <span v-if="slotView?.mapping?.formula?.length" class="flex items-center gap-1 text-[0.72rem] font-mono bg-bg-tertiary border border-border-color rounded-sm py-0.5 px-1.5 truncate max-w-full" title="Formula mapping">
              <SigmaSquare class="w-3 h-3 text-accent shrink-0" /> formula
            </span>
            <span v-else class="text-[0.72rem] font-mono bg-bg-tertiary border border-border-color rounded-sm py-0.5 px-1.5 truncate max-w-full" :title="slotView?.header || ''">
              {{ slotView?.header }}
            </span>
            <span v-if="slotView?.mapping?.divisor" class="text-[0.62rem] font-bold text-accent">÷{{ slotView?.mapping?.divisor }}</span>
            <span v-if="slotView?.mapping?.multiplier" class="text-[0.62rem] font-bold text-accent">×{{ slotView?.mapping?.multiplier }}</span>
            <span
              v-if="slotView?.field?.type === 'enum' && Object.values(slotView?.mapping?.enumMappings || {}).filter(Boolean).length"
              class="text-[0.62rem] font-bold text-amber-600"
              title="Enum values mapped"
            >{{ Object.values(slotView?.mapping?.enumMappings || {}).filter(Boolean).length }} enums</span>
            <Sparkles
              v-if="slotView?.field?.key === 'name' && slotView?.mapping?.enrichAssetNames && slotView?.mapping?.enrichAssetNames !== 'never'"
              class="w-3 h-3 text-amber-500" title="Auto-enrichment enabled"
            />
          </div>
          <div v-if="preview" class="text-[0.66rem] truncate mt-0.5" :class="preview.success ? 'text-text-secondary' : 'text-danger-color'" :title="preview.success ? preview.value : preview.error">
            <span class="font-mono">{{ exampleValue?.trim() || '—' }}</span>
            <span> → </span>
            <span class="font-mono font-semibold">{{ preview.success ? preview.value : preview.error }}</span>
          </div>
        </template>
        <template v-else>
          <div class="flex items-center gap-1.5">
            <span v-if="dropEnabled" class="text-[0.7rem] text-accent font-semibold">place here</span>
            <!-- click.stop only around the dropdown: an armed "place here" click must reach the slot. -->
            <div v-else class="flex items-center gap-1.5 min-w-0" @click.stop>
              <!-- Hover/focus-only (opacity keeps it keyboard-focusable) to cut
                   the visual noise of a dropdown on every empty slot. The
                   auto-generated placeholder stays visible: it carries state. -->
              <DynamicComponent
                componentKey="custom-dropdown"
                modelValue=""
                :options="columnOptions"
                :searchable="true"
                :placeholder="isTransactionId && autoIdEnabled ? 'auto-generated' : 'drop a column…'"
                :compact="true"
                class="min-w-[140px] transition-opacity"
                :class="isTransactionId && autoIdEnabled ? '' : 'opacity-0 group-hover/slot:opacity-100 focus-within:opacity-100'"
                @update:modelValue="(val: string) => val && emit('assign', val)"
              />
              <Hash v-if="isTransactionId && autoIdEnabled" class="w-3.5 h-3.5 text-accent shrink-0" title="Auto-generated ID enabled" />
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
