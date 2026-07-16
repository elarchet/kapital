<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { ChevronLeft, ChevronRight } from '@lucide/vue';
import OpTypeSelector from './mapping/OpTypeSelector.vue';
import CsvColumnTray from './mapping/CsvColumnTray.vue';
import FieldSlotList from './mapping/FieldSlotList.vue';
import FieldConfigModal from './mapping/FieldConfigModal.vue';
import SimulationVerificationModal from '../modals/SimulationVerificationModal.vue';
import { useFieldSlots, type MappingVariant } from './mapping/useFieldSlots';
import { useDragDrop } from './mapping/useDragDrop';
import type { FieldConfigContext } from './mapping/useFieldConfigModal';
import {
  isFieldRelevantForOpType,
  isFieldRequiredForOpType,
  parseDateTimeWithFormat,
  extraGroupFields,
  highestMappedGroup,
  groupKindOf,
  groupIndex,
  baseFieldKey,
  GROUP_SEP,
  type FeeGroupKind,
} from '../../../services/import';
import type { ColMapping, ColumnConfig, ImportField, OpTypeSettings } from '../../../services/import/types';

const props = defineProps<{
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string }>;
  columnConfigMap: Record<string, ColumnConfig>;
  operationTypeMappings: Record<string, string>;
  uniqueOperationTypes: string[];
  activeDbOpTypes: string[];
  importFields: ImportField[];
  allRawRows: string[][];
  operationTypeColumnIdx: number | null;
  matchingRowsByType: Record<string, { csvRow: string[]; rowIdx: number }[]>;
  matchingRowsByRawAction: Record<string, { csvRow: string[]; rowIdx: number }[]>;
  splitOpTypes: string[];
  feeTaxGroupCounts: Record<string, { fee: number; tax: number }>;
  opTypeSettings: Record<string, OpTypeSettings>;
  importDecimalSep: string;
  liveValidationStats: any;
  validationErrors: string[];
  enrichedNames: Record<string, string>;
  saveMappingTemplate: boolean;
  mappingTemplateName: string;
}>();

const emit = defineEmits<{
  (e: 'update:saveMappingTemplate', val: boolean): void;
  (e: 'update:mappingTemplateName', val: string): void;
  (e: 'update-optype-settings', payload: { opType: string; settings: OpTypeSettings }): void;
  (e: 'update-group-count', payload: { key: string; kind: FeeGroupKind; count: number }): void;
  (e: 'touch-config'): void;
  (e: 'back'): void;
}>();

// ---- Mapping variants (merged types: one per opType; split types: one per raw action) ----
const mappingVariants = computed<MappingVariant[]>(() => {
  const variants: MappingVariant[] = [];
  props.activeDbOpTypes.forEach(opType => {
    if (props.splitOpTypes.includes(opType)) {
      Object.keys(props.operationTypeMappings)
        .filter(raw => props.operationTypeMappings[raw] === opType)
        .forEach(raw => variants.push({ opType, key: raw, rawAction: raw }));
    } else {
      variants.push({ opType, key: opType });
    }
  });
  return variants;
});

// ---- Selected variants (Ctrl+click adds to the selection) + example row cycling ----
const selectedKeys = ref<string[]>([]);
watch(mappingVariants, (variants) => {
  const valid = selectedKeys.value.filter(k => variants.some(v => v.key === k));
  selectedKeys.value = valid.length ? valid : (variants[0] ? [variants[0].key] : []);
}, { immediate: true });

const onSelectPill = ({ key, additive }: { key: string; additive: boolean }) => {
  if (!additive) {
    selectedKeys.value = [key];
  } else if (selectedKeys.value.includes(key)) {
    if (selectedKeys.value.length > 1) selectedKeys.value = selectedKeys.value.filter(k => k !== key);
  } else {
    selectedKeys.value = [...selectedKeys.value, key];
  }
};

const selectedVariants = computed<MappingVariant[]>(() =>
  selectedKeys.value
    .map(k => mappingVariants.value.find(v => v.key === k))
    .filter((v): v is MappingVariant => !!v)
);
// Primary variant: single-variant consumers (config modal, verification) follow it.
const primaryKey = computed(() => selectedKeys.value[0] || '');
const selectedVariant = computed(() => selectedVariants.value[0] || null);
const selectedOpType = computed(() => selectedVariant.value?.opType || '');

const exampleOffsets = ref<Record<string, number>>({});
const matchesFor = (variant: MappingVariant | null) => {
  if (!variant) return [];
  return variant.rawAction
    ? (props.matchingRowsByRawAction?.[variant.rawAction] || [])
    : (props.matchingRowsByType?.[variant.opType] || []);
};
const matchesForSelected = computed(() => matchesFor(selectedVariant.value));
const offsetFor = (variant: MappingVariant) => {
  const total = matchesFor(variant).length;
  return total ? (exampleOffsets.value[variant.key] || 0) % total : 0;
};
const exampleOffset = computed(() => selectedVariant.value ? offsetFor(selectedVariant.value) : 0);
const exampleRow = computed<string[]>(() => matchesForSelected.value[exampleOffset.value]?.csvRow || []);

// One example entry per selected variant; labels only show in multi-select.
const exampleEntries = computed(() =>
  selectedVariants.value.map(v => ({
    key: v.key,
    label: selectedVariants.value.length > 1 ? (v.rawAction ? `${v.opType} · ${v.rawAction}` : v.opType) : null,
    row: matchesFor(v)[offsetFor(v)]?.csvRow || [],
  }))
);

const canCycle = computed(() => selectedVariants.value.some(v => matchesFor(v).length > 1));
const cycleExample = (delta: number) => {
  selectedVariants.value.forEach(v => {
    const total = matchesFor(v).length;
    if (total <= 1) return;
    exampleOffsets.value[v.key] = (offsetFor(v) + delta + total) % total;
  });
};

// ---- Extra fee/tax groups (fee_amount__2, tax_amount__2, ...) ----
// Mapping keys the selected variants read/write (mirrors useFieldSlots.keysToCheck).
const variantKeys = computed(() => {
  const keys = new Set<string>();
  selectedVariants.value.forEach(variant => {
    if (variant.rawAction) {
      keys.add(variant.rawAction);
    } else {
      keys.add(variant.opType);
      Object.keys(props.operationTypeMappings)
        .filter(r => props.operationTypeMappings[r] === variant.opType)
        .forEach(r => keys.add(r));
    }
  });
  return [...keys];
});

const mappedDbKeysForVariant = computed(() => {
  const keys: string[] = [];
  variantKeys.value.forEach(key => {
    Object.values(props.columnConfigMap).forEach(conf => {
      (conf?.typeSpecific?.[key] || []).forEach(m => { if (m.dbKey) keys.push(m.dbKey); });
    });
  });
  return keys;
});

// Effective count = groups the user added this session or groups already mapped
// (restores extra groups when a saved template is loaded).
const groupCount = (kind: FeeGroupKind) => Math.max(
  1,
  ...selectedKeys.value.map(k => props.feeTaxGroupCounts?.[k]?.[kind] || 1),
  highestMappedGroup(mappedDbKeysForVariant.value, kind)
);
const feeGroupCount = computed(() => groupCount('fee'));
const taxGroupCount = computed(() => groupCount('tax'));

const effectiveImportFields = computed<ImportField[]>(() => [
  ...props.importFields,
  ...extraGroupFields(props.importFields, 'fee', feeGroupCount.value),
  ...extraGroupFields(props.importFields, 'tax', taxGroupCount.value),
]);

const canAddGroup = (kind: FeeGroupKind) =>
  selectedVariants.value.length > 0
  && props.importFields.some(f =>
    f.key === `${kind}_amount`
    && selectedVariants.value.every(v => isFieldRelevantForOpType(f, v.opType))
  );

const addGroup = (kind: FeeGroupKind) => {
  const count = groupCount(kind) + 1;
  selectedKeys.value.forEach(key => emit('update-group-count', { key, kind, count }));
};

const removeGroup = ({ kind, index }: { kind: FeeGroupKind; index: number }) => {
  // Drop the group's mappings and compact higher group indexes down by one.
  variantKeys.value.forEach(key => {
    Object.values(props.columnConfigMap).forEach(conf => {
      const list = conf?.typeSpecific?.[key];
      if (!list?.length) return;
      conf.typeSpecific[key] = list
        .filter(m => !(m.dbKey && groupKindOf(m.dbKey) === kind && groupIndex(m.dbKey) === index))
        .map(m => {
          if (m.dbKey && groupKindOf(m.dbKey) === kind && groupIndex(m.dbKey) > index) {
            return { ...m, dbKey: `${baseFieldKey(m.dbKey)}${GROUP_SEP}${groupIndex(m.dbKey) - 1}` };
          }
          return m;
        });
    });
  });
  emit('touch-config');
  const count = groupCount(kind) - 1;
  selectedKeys.value.forEach(key => emit('update-group-count', { key, kind, count }));
};

// ---- Slots + drag & drop ----
const columnConfigMapRef = computed({
  get: () => props.columnConfigMap,
  set: () => emit('touch-config'),
});

const fieldSlots = useFieldSlots({
  columnConfigMap: columnConfigMapRef as any,
  uiColumns: computed(() => props.uiColumns),
  importFields: effectiveImportFields,
  operationTypeMappings: computed(() => props.operationTypeMappings),
  selectedVariants,
});

const dnd = useDragDrop();

const onEscape = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && dnd.armedColId.value) {
    e.stopPropagation();
    dnd.disarm();
  }
};
onMounted(() => window.addEventListener('keydown', onEscape, true));
onBeforeUnmount(() => window.removeEventListener('keydown', onEscape, true));

// ---- Per-variant completion stats for the selector pills ----
const variantStats = computed(() => {
  const stats: Record<string, { requiredMapped: number; requiredTotal: number; rowCount: number }> = {};
  mappingVariants.value.forEach(variant => {
    const { opType } = variant;
    // Split variants only count their own rawAction-keyed mappings; merged
    // variants also accept legacy rawAction-keyed entries of their group.
    const keys = variant.rawAction
      ? [variant.rawAction]
      : [opType, ...Object.keys(props.operationTypeMappings).filter(r => props.operationTypeMappings[r] === opType)];
    const requiredFields = props.importFields.filter(f =>
      f.key !== 'operation_type' && isFieldRelevantForOpType(f, opType) && isFieldRequiredForOpType(f, opType)
    );
    const mapped = requiredFields.filter(f =>
      keys.some(key =>
        Object.values(props.columnConfigMap).some(conf => conf?.typeSpecific?.[key]?.some(m => m.dbKey === f.key))
      )
    ).length;
    stats[variant.key] = {
      requiredMapped: mapped,
      requiredTotal: requiredFields.length,
      rowCount: variant.rawAction
        ? (props.matchingRowsByRawAction?.[variant.rawAction]?.length || 0)
        : (props.matchingRowsByType?.[opType]?.length || 0),
    };
  });
  return stats;
});

// ---- Assignment (drop / click-to-place / dropdown) ----
const showConfigModal = ref(false);
const configContext = ref<FieldConfigContext | null>(null);
const configFieldKey = ref('');

const rowByHeader = computed(() => {
  const map: Record<string, string> = {};
  props.uiColumns.forEach(c => {
    if (c?.name !== undefined) map[c.name] = exampleRow.value?.[c.colIdx] ?? '';
  });
  return map;
});

const uniqueValuesForCol = (colId: string | null): string[] => {
  if (!colId) return [];
  const col = props.uiColumns.find(c => c.id === colId);
  if (!col) return [];
  const uniqueSet = new Set<string>();
  (matchesForSelected.value.length ? matchesForSelected.value.map(m => m.csvRow) : []).forEach(row => {
    const v = row[col.colIdx];
    if (v?.trim()) uniqueSet.add(v.trim());
  });
  return Array.from(uniqueSet);
};

const openConfig = (fieldKey: string) => {
  const field = effectiveImportFields.value.find(f => f.key === fieldKey);
  if (!field) return;
  const found = fieldSlots.findMapping(fieldKey);
  const col = found ? props.uiColumns.find(c => c.id === found.colId) : null;
  const tickerMapping = fieldSlots.findMapping('ticker');
  const tickerCol = tickerMapping ? props.uiColumns.find(c => c.id === tickerMapping.colId) : null;

  configFieldKey.value = fieldKey;
  configContext.value = {
    field,
    opType: selectedOpType.value,
    mappedHeader: col?.name ?? null,
    initialMapping: found?.mapping ?? null,
    uniqueCsvValues: uniqueValuesForCol(found?.colId ?? null),
    exampleValue: col ? (exampleRow.value?.[col.colIdx] ?? '') : '',
    exampleRowByHeader: rowByHeader.value,
    tickerMapped: !!tickerMapping,
    exampleTicker: tickerCol ? (exampleRow.value?.[tickerCol.colIdx] ?? '').trim() : '',
    // Settings are stored per variant key so split variants configure independently.
    // Multi-select: the modal shows the primary variant's settings; saving
    // applies them to every selected variant.
    opTypeSettings: props.opTypeSettings?.[primaryKey.value] ?? null,
    decimalSeparator: props.importDecimalSep,
  };
  showConfigModal.value = true;
};

const assignField = (fieldKey: string, colId: string) => {
  fieldSlots.assignColumn(colId, fieldKey);
  emit('touch-config');
  // Enum fields can't import without value mappings; datetimes that fail
  // auto-parse need an explicit format. Open the modal right away.
  const field = effectiveImportFields.value.find(f => f.key === fieldKey);
  const col = props.uiColumns.find(c => c.id === colId);
  const example = col ? (exampleRow.value?.[col.colIdx] ?? '') : '';
  const needsConfig = field?.type === 'enum'
    || (field?.type === 'datetime' && !!example.trim() && !parseDateTimeWithFormat(example, 'auto'));
  if (needsConfig) openConfig(fieldKey);
};

const onSlotDrop = (fieldKey: string, e: DragEvent) => {
  const colId = dnd.resolveDrop(e);
  if (colId) assignField(fieldKey, colId);
};

const onSlotClick = (fieldKey: string) => {
  if (!dnd.armedColId.value) return;
  const colId = dnd.resolveDrop();
  if (colId) assignField(fieldKey, colId);
};

const onModalSave = (payload: { mapping: ColMapping; opTypeSettings?: OpTypeSettings }) => {
  if (payload.mapping.dbKey && (fieldSlots.findMapping(configFieldKey.value) || payload.mapping.formula?.length)) {
    fieldSlots.updateMapping(configFieldKey.value, payload.mapping);
  }
  if (payload.opTypeSettings) {
    selectedKeys.value.forEach(key =>
      emit('update-optype-settings', { opType: key, settings: payload.opTypeSettings! })
    );
  }
  emit('touch-config');
  showConfigModal.value = false;
};

const onModalClear = () => {
  fieldSlots.clearField(configFieldKey.value);
  emit('touch-config');
  showConfigModal.value = false;
};

// ---- Per-variant verification ----
const showVerification = ref(false);
const aggregatedStats = computed(() => {
  const rawActions = new Set<string>();
  selectedVariants.value.forEach(variant => {
    if (variant.rawAction) {
      rawActions.add(variant.rawAction);
    } else {
      Object.keys(props.operationTypeMappings)
        .filter(r => props.operationTypeMappings[r] === variant.opType)
        .forEach(r => rawActions.add(r));
    }
  });
  const agg = { total: 0, success: 0, failed: 0, errors: [] as any[] };
  rawActions.forEach(raw => {
    const s = props.liveValidationStats?.[raw];
    if (!s) return;
    agg.total += s.total;
    agg.success += s.success;
    agg.failed += s.failed;
    agg.errors.push(...(s.errors || []));
  });
  return agg;
});
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex justify-between items-center gap-4">
      <p class="text-xs text-text-secondary m-0 flex-1">
        Map one transaction type at a time — or Ctrl+click several pills to map their shared columns together.
      </p>
      <button @click="emit('back')" class="btn btn-sm shrink-0">&larr; Back to Step 1</button>
    </div>

    <!-- Variant pills (one per DB type, or one per raw action for split types) -->
    <OpTypeSelector
      v-if="mappingVariants.length"
      :variants="mappingVariants"
      :selected="selectedKeys"
      :stats="variantStats"
      @select="onSelectPill"
    />
    <p v-else class="text-[0.78rem] text-warning-color m-0">
      Map at least one of your file's actions to a transaction type in Step 1 to start mapping columns.
    </p>

    <template v-if="primaryKey">
      <!-- Sticky CSV column tray -->
      <CsvColumnTray
        :uiColumns="uiColumns"
        :exampleRow="exampleRow"
        :usedColIds="fieldSlots.usedColIds.value"
        :armedColId="dnd.armedColId.value"
        @chip-dragstart="({ colId, event }) => dnd.onChipDragStart(colId, event)"
        @chip-dragend="dnd.onChipDragEnd()"
        @chip-arm="dnd.toggleArmChip"
      />

      <!-- Example row pager + verification -->
      <div class="flex items-center gap-2 text-[0.72rem] text-text-secondary">
        <span>Example row{{ selectedKeys.length > 1 ? 's' : '' }}</span>
        <button type="button" class="btn btn-sm !p-0.5" :disabled="!canCycle" @click="cycleExample(-1)">
          <ChevronLeft class="w-3.5 h-3.5" />
        </button>
        <span class="font-mono">{{ matchesForSelected.length ? exampleOffset + 1 : 0 }}/{{ matchesForSelected.length }}</span>
        <button type="button" class="btn btn-sm !p-0.5" :disabled="!canCycle" @click="cycleExample(1)">
          <ChevronRight class="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          class="ml-auto text-[0.72rem] font-semibold underline decoration-dotted"
          :class="aggregatedStats.failed > 0 ? 'text-danger-color' : 'text-success-color'"
          @click="showVerification = true"
        >
          {{ aggregatedStats.success }}/{{ aggregatedStats.total }} rows parse cleanly
        </button>
      </div>

      <!-- Field slots -->
      <FieldSlotList
        :slots="fieldSlots.slots.value"
        :uiColumns="uiColumns"
        :exampleEntries="exampleEntries"
        :decimalSeparator="importDecimalSep"
        :enrichedNames="enrichedNames"
        :opTypeSettings="opTypeSettings?.[primaryKey]"
        :dropEnabled="!!dnd.draggingColId.value || !!dnd.armedColId.value"
        :canAddFee="canAddGroup('fee')"
        :canAddTax="canAddGroup('tax')"
        @drop-column="({ fieldKey, event }) => onSlotDrop(fieldKey, event)"
        @assign="({ fieldKey, colId }) => assignField(fieldKey, colId)"
        @clear="fieldSlots.clearField"
        @configure="openConfig"
        @slot-click="onSlotClick"
        @add-group="addGroup"
        @remove-group="removeGroup"
      />
    </template>

    <!-- Validation summary -->
    <div v-if="validationErrors.length" class="border border-danger-color/40 bg-danger-light rounded-sm p-2">
      <div class="text-[0.7rem] font-bold uppercase tracking-wider text-danger-color mb-1">Before importing</div>
      <ul class="m-0 pl-4 text-[0.72rem] text-danger-color flex flex-col gap-0.5">
        <li v-for="(err, idx) in validationErrors.slice(0, 6)" :key="idx">{{ err }}</li>
        <li v-if="validationErrors.length > 6">…and {{ validationErrors.length - 6 }} more</li>
      </ul>
    </div>

    <!-- Save template options -->
    <div class="border-t border-border-color pt-2 flex flex-col gap-1.5">
      <label class="flex items-center gap-2 font-medium normal-case text-sm">
        <input
          type="checkbox"
          :checked="saveMappingTemplate"
          @change="emit('update:saveMappingTemplate', ($event.target as HTMLInputElement).checked)"
          class="w-4 h-4 cursor-pointer"
        />
        <span>Save this configuration mapping as a template</span>
      </label>
      <div v-if="saveMappingTemplate" class="form-group mt-2 mb-0 max-w-[400px]">
        <label>Template Name</label>
        <input
          :value="mappingTemplateName"
          @input="emit('update:mappingTemplateName', ($event.target as HTMLInputElement).value)"
          type="text"
          class="form-control"
          placeholder="e.g. My Custom Broker CSV"
          required
        />
      </div>
    </div>

    <!-- Advanced field configuration -->
    <FieldConfigModal
      :show="showConfigModal"
      :context="configContext"
      :headers="uiColumns.map(c => c.name)"
      :columnOptions="uiColumns.map(c => ({ value: c.id, label: c.name }))"
      @close="showConfigModal = false"
      @save="onModalSave"
      @clear="onModalClear"
      @map-ticker="(colId: string) => fieldSlots.assignColumn(colId, 'ticker')"
    />

    <SimulationVerificationModal
      :show="showVerification"
      :dbOpType="selectedOpType"
      :stats="aggregatedStats"
      @close="showVerification = false"
    />
  </div>
</template>
