<script setup lang="ts">
import { computed } from 'vue';
import DbFieldSlot from './DbFieldSlot.vue';
import type { FieldSlotView } from './useFieldSlots';
import { computeLivePreview, type LivePreviewResult } from '../../../../services/import';
import type { OpTypeSettings } from '../../../../services/import/types';

const props = defineProps<{
  slots: FieldSlotView[];
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string }>;
  exampleRow: string[];
  decimalSeparator: string;
  enrichedNames: Record<string, string>;
  opTypeSettings?: OpTypeSettings;
  dropEnabled: boolean;
}>();

const emit = defineEmits<{
  (e: 'drop-column', payload: { fieldKey: string; event: DragEvent }): void;
  (e: 'assign', payload: { fieldKey: string; colId: string }): void;
  (e: 'clear', fieldKey: string): void;
  (e: 'configure', fieldKey: string): void;
  (e: 'slot-click', fieldKey: string): void;
}>();

const requiredSlots = computed(() => props.slots.filter(s => s.isRequired));
const optionalSlots = computed(() => props.slots.filter(s => !s.isRequired));

const columnOptions = computed(() =>
  props.uiColumns.map(c => ({ value: c.id, label: c.name }))
);

const rowByHeader = computed(() => {
  const map: Record<string, string> = {};
  props.uiColumns.forEach(c => {
    if (c?.name !== undefined) map[c.name] = props.exampleRow?.[c.colIdx] ?? '';
  });
  return map;
});

const exampleValueFor = (slot: FieldSlotView): string => {
  const col = props.uiColumns.find(c => c.id === slot.colId);
  return col ? (props.exampleRow?.[col.colIdx] ?? '') : '';
};

const previewFor = (slot: FieldSlotView): LivePreviewResult | null => {
  if (!slot?.mapping?.dbKey && !slot?.mapping?.formula?.length) return null;

  const tickerSlot = props.slots.find(s => s.field?.key === 'ticker');
  const tickerValue = tickerSlot ? exampleValueFor(tickerSlot).trim() : '';

  return computeLivePreview(slot.field, exampleValueFor(slot), slot.mapping || {}, {
    decimalSeparator: props.decimalSeparator,
    rowByHeader: rowByHeader.value,
    isRequired: slot.isRequired,
    enrichMode: slot.mapping?.enrichAssetNames,
    tickerMapped: !!tickerSlot?.colId,
    exampleTicker: tickerValue,
    enrichedName: tickerValue ? props.enrichedNames?.[tickerValue] : undefined,
    autoIdMode: props.opTypeSettings?.autoTransactionId ?? slot.mapping?.enrichTransactionIds,
  });
};
</script>

<template>
  <div class="flex flex-col gap-3">
    <div v-if="requiredSlots.length">
      <div class="text-[0.68rem] font-bold uppercase tracking-wider text-danger-color mb-1.5">Required fields</div>
      <div class="flex flex-col gap-1.5">
        <DbFieldSlot
          v-for="slot in requiredSlots"
          :key="slot.field.key"
          :slotView="slot"
          :exampleValue="exampleValueFor(slot)"
          :preview="previewFor(slot)"
          :dropEnabled="dropEnabled"
          :columnOptions="columnOptions"
          :autoIdEnabled="slot.field.key === 'transaction_id' && !!opTypeSettings?.autoTransactionId && opTypeSettings.autoTransactionId !== 'never'"
          @drop-column="(e: DragEvent) => emit('drop-column', { fieldKey: slot.field.key, event: e })"
          @assign="(colId: string) => emit('assign', { fieldKey: slot.field.key, colId })"
          @clear="emit('clear', slot.field.key)"
          @configure="emit('configure', slot.field.key)"
          @slot-click="emit('slot-click', slot.field.key)"
        />
      </div>
    </div>

    <div v-if="optionalSlots.length">
      <div class="text-[0.68rem] font-bold uppercase tracking-wider text-text-secondary mb-1.5">Optional fields</div>
      <div class="flex flex-col gap-1.5">
        <DbFieldSlot
          v-for="slot in optionalSlots"
          :key="slot.field.key"
          :slotView="slot"
          :exampleValue="exampleValueFor(slot)"
          :preview="previewFor(slot)"
          :dropEnabled="dropEnabled"
          :columnOptions="columnOptions"
          :autoIdEnabled="slot.field.key === 'transaction_id' && !!opTypeSettings?.autoTransactionId && opTypeSettings.autoTransactionId !== 'never'"
          @drop-column="(e: DragEvent) => emit('drop-column', { fieldKey: slot.field.key, event: e })"
          @assign="(colId: string) => emit('assign', { fieldKey: slot.field.key, colId })"
          @clear="emit('clear', slot.field.key)"
          @configure="emit('configure', slot.field.key)"
          @slot-click="emit('slot-click', slot.field.key)"
        />
      </div>
    </div>
  </div>
</template>
