<script setup lang="ts">
import { computed } from 'vue';
import { Plus, Trash2 } from '@lucide/vue';
import DbFieldSlot from './DbFieldSlot.vue';
import type { FieldSlotView, SlotPreviewEntry } from './useFieldSlots';
import {
  computeLivePreview,
  isExtraGroupKey,
  groupKindOf,
  groupIndex,
  type FeeGroupKind,
} from '../../../../services/import';
import type { OpTypeSettings } from '../../../../services/import/types';

const props = defineProps<{
  slots: FieldSlotView[];
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string }>;
  // One example row per selected variant (a single entry outside multi-select).
  exampleEntries: Array<{ key: string; label: string | null; row: string[] }>;
  decimalSeparator: string;
  enrichedNames: Record<string, string>;
  opTypeSettings?: OpTypeSettings;
  dropEnabled: boolean;
  canAddFee: boolean;
  canAddTax: boolean;
}>();

const emit = defineEmits<{
  (e: 'drop-column', payload: { fieldKey: string; event: DragEvent }): void;
  (e: 'assign', payload: { fieldKey: string; colId: string }): void;
  (e: 'clear', fieldKey: string): void;
  (e: 'configure', fieldKey: string): void;
  (e: 'slot-click', fieldKey: string): void;
  (e: 'add-group', kind: FeeGroupKind): void;
  (e: 'remove-group', payload: { kind: FeeGroupKind; index: number }): void;
}>();

const regularSlots = computed(() => props.slots.filter(s => !isExtraGroupKey(s.field.key)));
const requiredSlots = computed(() => regularSlots.value.filter(s => s.isRequired));
const optionalSlots = computed(() => regularSlots.value.filter(s => !s.isRequired));

// Extra fee/tax groups (fee_amount__2, ...) render as their own titled sections.
const extraGroups = computed(() => {
  const groups: Record<string, { kind: FeeGroupKind; index: number; slots: FieldSlotView[] }> = {};
  props.slots.forEach(s => {
    if (!isExtraGroupKey(s.field.key)) return;
    const kind = groupKindOf(s.field.key);
    if (!kind) return;
    const index = groupIndex(s.field.key);
    const groupKey = `${kind}-${index}`;
    (groups[groupKey] ||= { kind, index, slots: [] }).slots.push(s);
  });
  return Object.values(groups).sort((a, b) =>
    a.kind === b.kind ? a.index - b.index : a.kind === 'fee' ? -1 : 1
  );
});

const columnOptions = computed(() =>
  props.uiColumns.map(c => ({ value: c.id, label: c.name }))
);

const rowByHeaderFor = (row: string[]) => {
  const map: Record<string, string> = {};
  props.uiColumns.forEach(c => {
    if (c?.name !== undefined) map[c.name] = row?.[c.colIdx] ?? '';
  });
  return map;
};

const valueFor = (colId: string | null, row: string[]): string => {
  const col = colId ? props.uiColumns.find(c => c.id === colId) : null;
  return col ? (row?.[col.colIdx] ?? '') : '';
};

// One preview line per selected variant, each computed from that variant's own
// mapping and example row.
const previewsFor = (slot: FieldSlotView): SlotPreviewEntry[] =>
  props.exampleEntries.map(entry => {
    const pv = slot.perVariant.find(p => p.key === entry.key) || null;
    const mapping = pv?.mapping;
    const exampleValue = valueFor(pv?.colId ?? null, entry.row);
    if (!mapping?.dbKey && !mapping?.formula?.length) {
      return { label: entry.label, exampleValue, preview: null };
    }

    const tickerSlot = props.slots.find(s => s.field?.key === 'ticker');
    const tickerPv = tickerSlot?.perVariant.find(p => p.key === entry.key);
    const tickerValue = tickerPv?.colId ? valueFor(tickerPv.colId, entry.row).trim() : '';

    return {
      label: entry.label,
      exampleValue,
      preview: computeLivePreview(slot.field, exampleValue, mapping || {}, {
        decimalSeparator: props.decimalSeparator,
        rowByHeader: rowByHeaderFor(entry.row),
        isRequired: slot.isRequired,
        enrichMode: mapping?.enrichAssetNames,
        tickerMapped: !!tickerPv?.colId,
        exampleTicker: tickerValue,
        enrichedName: tickerValue ? props.enrichedNames?.[tickerValue] : undefined,
        autoIdMode: props.opTypeSettings?.autoTransactionId ?? mapping?.enrichTransactionIds,
      }),
    };
  });

const autoIdEnabledFor = (slot: FieldSlotView) =>
  slot.field.key === 'transaction_id'
  && !!props.opTypeSettings?.autoTransactionId
  && props.opTypeSettings.autoTransactionId !== 'never';
</script>

<template>
  <div class="flex flex-col gap-3">
    <div v-if="requiredSlots.length">
      <div class="text-[0.68rem] font-bold uppercase tracking-wider text-danger-color mb-1.5">Required fields</div>
      <div class="grid grid-cols-[repeat(auto-fill,minmax(230px,1fr))] gap-1.5 items-stretch">
        <DbFieldSlot
          v-for="slot in requiredSlots"
          :key="slot.field.key"
          :slotView="slot"
          :previews="previewsFor(slot)"
          :dropEnabled="dropEnabled"
          :columnOptions="columnOptions"
          :autoIdEnabled="autoIdEnabledFor(slot)"
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
      <div class="grid grid-cols-[repeat(auto-fill,minmax(230px,1fr))] gap-1.5 items-stretch">
        <DbFieldSlot
          v-for="slot in optionalSlots"
          :key="slot.field.key"
          :slotView="slot"
          :previews="previewsFor(slot)"
          :dropEnabled="dropEnabled"
          :columnOptions="columnOptions"
          :autoIdEnabled="autoIdEnabledFor(slot)"
          @drop-column="(e: DragEvent) => emit('drop-column', { fieldKey: slot.field.key, event: e })"
          @assign="(colId: string) => emit('assign', { fieldKey: slot.field.key, colId })"
          @clear="emit('clear', slot.field.key)"
          @configure="emit('configure', slot.field.key)"
          @slot-click="emit('slot-click', slot.field.key)"
        />
      </div>
    </div>

    <!-- Extra fee/tax groups: each becomes an additional Fee entry on the imported row -->
    <div v-for="group in extraGroups" :key="`${group.kind}-${group.index}`">
      <div class="flex items-center gap-2 mb-1.5">
        <span class="text-[0.68rem] font-bold uppercase tracking-wider text-text-secondary">
          {{ group.kind === 'fee' ? 'Fee' : 'Tax' }} {{ group.index }}
        </span>
        <button
          type="button"
          class="p-0.5 rounded-sm text-text-secondary hover:text-danger-color hover:bg-danger-light"
          :title="`Remove this ${group.kind} group`"
          :data-testid="`remove-${group.kind}-group-${group.index}`"
          @click="emit('remove-group', { kind: group.kind, index: group.index })"
        >
          <Trash2 class="w-3.5 h-3.5" />
        </button>
      </div>
      <div class="grid grid-cols-[repeat(auto-fill,minmax(230px,1fr))] gap-1.5 items-stretch">
        <DbFieldSlot
          v-for="slot in group.slots"
          :key="slot.field.key"
          :slotView="slot"
          :previews="previewsFor(slot)"
          :dropEnabled="dropEnabled"
          :columnOptions="columnOptions"
          :autoIdEnabled="false"
          @drop-column="(e: DragEvent) => emit('drop-column', { fieldKey: slot.field.key, event: e })"
          @assign="(colId: string) => emit('assign', { fieldKey: slot.field.key, colId })"
          @clear="emit('clear', slot.field.key)"
          @configure="emit('configure', slot.field.key)"
          @slot-click="emit('slot-click', slot.field.key)"
        />
      </div>
    </div>

    <!-- Rows can carry several fees/taxes (e.g. commission + FX fee): each added
         group maps to its own CSV columns and imports as a separate fee entry. -->
    <div v-if="canAddFee || canAddTax" class="flex items-center gap-2">
      <button
        v-if="canAddFee"
        type="button"
        class="btn btn-sm flex items-center gap-1"
        data-testid="add-fee-group"
        @click="emit('add-group', 'fee')"
      >
        <Plus class="w-3.5 h-3.5" /> Add another fee
      </button>
      <button
        v-if="canAddTax"
        type="button"
        class="btn btn-sm flex items-center gap-1"
        data-testid="add-tax-group"
        @click="emit('add-group', 'tax')"
      >
        <Plus class="w-3.5 h-3.5" /> Add another tax
      </button>
      <span class="text-[0.68rem] text-text-tertiary">Each group is saved as a separate fee/tax on the transaction.</span>
    </div>
  </div>
</template>
