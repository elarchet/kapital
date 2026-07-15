<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { ChevronLeft, ChevronRight } from '@lucide/vue';
import OperationTypeMappingPanel from './mapping/OperationTypeMappingPanel.vue';
import OpTypeSelector from './mapping/OpTypeSelector.vue';
import CsvColumnTray from './mapping/CsvColumnTray.vue';
import FieldSlotList from './mapping/FieldSlotList.vue';
import FieldConfigModal from './mapping/FieldConfigModal.vue';
import SimulationVerificationModal from '../modals/SimulationVerificationModal.vue';
import { useFieldSlots } from './mapping/useFieldSlots';
import { useDragDrop } from './mapping/useDragDrop';
import type { FieldConfigContext } from './mapping/useFieldConfigModal';
import {
  isFieldRelevantForOpType,
  isFieldRequiredForOpType,
  parseDateTimeWithFormat,
} from '../../../services/import';
import type { ColMapping, ImportField, OpTypeSettings } from '../../../services/import/types';

const props = defineProps<{
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string }>;
  columnConfigMap: Record<string, { typeSpecific: Record<string, ColMapping> }>;
  operationTypeMappings: Record<string, string>;
  uniqueOperationTypes: string[];
  activeDbOpTypes: string[];
  importFields: ImportField[];
  allRawRows: string[][];
  operationTypeColumnIdx: number | null;
  matchingRowsByType: Record<string, { csvRow: string[]; rowIdx: number }[]>;
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
  (e: 'update-optype-mapping', payload: { rawAction: string; dbOpType: string }): void;
  (e: 'update-optype-settings', payload: { opType: string; settings: OpTypeSettings }): void;
  (e: 'touch-config'): void;
  (e: 'back'): void;
}>();

// ---- Selected op type + example row cycling ----
const selectedOpType = ref('');
watch(() => props.activeDbOpTypes, (types) => {
  if (!types.includes(selectedOpType.value)) selectedOpType.value = types[0] || '';
}, { immediate: true });

const exampleOffsets = ref<Record<string, number>>({});
const matchesForSelected = computed(() => props.matchingRowsByType?.[selectedOpType.value] || []);
const exampleOffset = computed(() => {
  const offset = exampleOffsets.value[selectedOpType.value] || 0;
  return matchesForSelected.value.length ? offset % matchesForSelected.value.length : 0;
});
const exampleRow = computed<string[]>(() => matchesForSelected.value[exampleOffset.value]?.csvRow || []);
const cycleExample = (delta: number) => {
  const total = matchesForSelected.value.length;
  if (total <= 1) return;
  exampleOffsets.value[selectedOpType.value] = (exampleOffset.value + delta + total) % total;
};

const rowCountsByRawAction = computed<Record<string, number>>(() => {
  const counts: Record<string, number> = {};
  if (props.operationTypeColumnIdx === null) return counts;
  props.allRawRows.forEach(row => {
    const raw = row[props.operationTypeColumnIdx!]?.trim();
    if (raw) counts[raw] = (counts[raw] || 0) + 1;
  });
  return counts;
});

// ---- Slots + drag & drop ----
const columnConfigMapRef = computed({
  get: () => props.columnConfigMap,
  set: () => emit('touch-config'),
});

const fieldSlots = useFieldSlots({
  columnConfigMap: columnConfigMapRef as any,
  uiColumns: computed(() => props.uiColumns),
  importFields: computed(() => props.importFields),
  operationTypeMappings: computed(() => props.operationTypeMappings),
  selectedOpType,
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

// ---- Per-op-type completion stats for the selector pills ----
const opTypeStats = computed(() => {
  const stats: Record<string, { requiredMapped: number; requiredTotal: number; rowCount: number }> = {};
  props.activeDbOpTypes.forEach(opType => {
    const rawActions = Object.keys(props.operationTypeMappings).filter(r => props.operationTypeMappings[r] === opType);
    const keys = [opType, ...rawActions];
    const requiredFields = props.importFields.filter(f =>
      f.key !== 'operation_type' && isFieldRelevantForOpType(f, opType) && isFieldRequiredForOpType(f, opType)
    );
    const mapped = requiredFields.filter(f =>
      keys.some(key =>
        Object.values(props.columnConfigMap).some(conf => conf?.typeSpecific?.[key]?.dbKey === f.key)
      )
    ).length;
    stats[opType] = {
      requiredMapped: mapped,
      requiredTotal: requiredFields.length,
      rowCount: props.matchingRowsByType?.[opType]?.length || 0,
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
  const field = props.importFields.find(f => f.key === fieldKey);
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
    opTypeSettings: props.opTypeSettings?.[selectedOpType.value] ?? null,
    decimalSeparator: props.importDecimalSep,
  };
  showConfigModal.value = true;
};

const assignField = (fieldKey: string, colId: string) => {
  fieldSlots.assignColumn(colId, fieldKey);
  emit('touch-config');
  // Enum fields can't import without value mappings; datetimes that fail
  // auto-parse need an explicit format. Open the modal right away.
  const field = props.importFields.find(f => f.key === fieldKey);
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
    emit('update-optype-settings', { opType: selectedOpType.value, settings: payload.opTypeSettings });
  }
  emit('touch-config');
  showConfigModal.value = false;
};

const onModalClear = () => {
  fieldSlots.clearField(configFieldKey.value);
  emit('touch-config');
  showConfigModal.value = false;
};

// ---- Per-op-type verification ----
const showVerification = ref(false);
const aggregatedStats = computed(() => {
  const rawActions = Object.keys(props.operationTypeMappings).filter(r => props.operationTypeMappings[r] === selectedOpType.value);
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
        Map one transaction type at a time: drag CSV columns onto the database fields below.
      </p>
      <button @click="emit('back')" class="btn btn-sm shrink-0">&larr; Back to Step 1</button>
    </div>

    <!-- Raw action -> DB type mapping -->
    <OperationTypeMappingPanel
      :uniqueOperationTypes="uniqueOperationTypes"
      :operationTypeMappings="operationTypeMappings"
      :importFields="importFields"
      :rowCountsByRawAction="rowCountsByRawAction"
      @update-optype-mapping="(payload) => emit('update-optype-mapping', payload)"
    />

    <!-- Op type pills -->
    <OpTypeSelector
      v-if="activeDbOpTypes.length"
      :opTypes="activeDbOpTypes"
      :selected="selectedOpType"
      :stats="opTypeStats"
      @select="(t: string) => selectedOpType = t"
    />
    <p v-else class="text-[0.78rem] text-warning-color m-0">
      Map at least one of your file's actions to a transaction type above to start mapping columns.
    </p>

    <template v-if="selectedOpType">
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
        <span>Example row</span>
        <button type="button" class="btn btn-sm !p-0.5" :disabled="matchesForSelected.length <= 1" @click="cycleExample(-1)">
          <ChevronLeft class="w-3.5 h-3.5" />
        </button>
        <span class="font-mono">{{ matchesForSelected.length ? exampleOffset + 1 : 0 }}/{{ matchesForSelected.length }}</span>
        <button type="button" class="btn btn-sm !p-0.5" :disabled="matchesForSelected.length <= 1" @click="cycleExample(1)">
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
        :exampleRow="exampleRow"
        :decimalSeparator="importDecimalSep"
        :enrichedNames="enrichedNames"
        :opTypeSettings="opTypeSettings?.[selectedOpType]"
        :dropEnabled="!!dnd.draggingColId.value || !!dnd.armedColId.value"
        @drop-column="({ fieldKey, event }) => onSlotDrop(fieldKey, event)"
        @assign="({ fieldKey, colId }) => assignField(fieldKey, colId)"
        @clear="fieldSlots.clearField"
        @configure="openConfig"
        @slot-click="onSlotClick"
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
