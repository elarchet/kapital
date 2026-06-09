<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { Plus, Trash2 } from '@lucide/vue';
import CustomDropdown from '../../CustomDropdown.vue';

const props = defineProps<{
  importFileHeaders: string[];
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }>;
  operationTypeColumnIdx: number | null;
  columnConfigMap: Record<string, {
    global: { dbKey: string; divisor?: number; multiplier?: number; enumMappings?: Record<string, string>; dateFormat?: string };
    typeSpecific: Record<string, { dbKey: string; divisor?: number; multiplier?: number; enumMappings?: Record<string, string>; dateFormat?: string }>;
  }>;
  activeDbOpTypes: string[];
  uniqueOperationTypes: string[];
  operationTypeMappings: Record<string, string>;
  importFields: any[];
  exampleTransactions: Array<{
    opType: string; // This holds the raw CSV action value
    csvRow: string[];
    rowIdx: number;
    totalMatches: number;
    currentOffset: number;
  }>;
  liveValidationStats: Record<string, {
    total: number;
    success: number;
    failed: number;
    errors: any[];
  }>;
}>();

const emit = defineEmits<{
  (e: 'open-wizard', payload: { colId: string; opType: string | null; targets?: Array<{ colId: string; opType: string | null }>; rawAction?: string | null }): void;
  (e: 'prev-example', opType: string): void;
  (e: 'next-example', opType: string): void;
  (e: 'update-mapping', payload: { colId: string; opType: string | null; mapping: any }): void;
  (e: 'update-optype-mapping', payload: { rawAction: string; dbOpType: string }): void;
  (e: 'duplicate-column', colId: string): void;
  (e: 'delete-column', colId: string): void;
}>();

// Selected cells for keyboard selection & actions
const selectedCells = ref<Set<string>>(new Set());
const lastSelectedCell = ref<{ colId: string; opType: string } | null>(null);

// Clipboard state for copy-pasting mappings
const copiedMapping = ref<{
  colId: string;
  opType: string;
  dbKey: string;
  divisor?: number;
  multiplier?: number;
  enumMappings?: Record<string, string>;
  dateFormat?: string;
} | null>(null);

// Cell flashing state for visual shortcut feedback
const recentlyFlashed = ref<Record<string, string>>({}); // cellKey -> CSS class

const flashCell = (colId: string, opType: string, flashClass: string) => {
  const key = `${colId}:::${opType}`;
  recentlyFlashed.value[key] = flashClass;
  setTimeout(() => {
    delete recentlyFlashed.value[key];
  }, 1000);
};



const isSelected = (colId: string, opType: string): boolean => {
  const key = `${colId}:::${opType}`;
  return selectedCells.value.has(key);
};

const isCopiedSource = (colId: string, opType: string): boolean => {
  return copiedMapping.value !== null &&
         copiedMapping.value.colId === colId &&
         copiedMapping.value.opType === opType;
};

const getCellOutlineStyle = (colId: string, opType: string) => {
  if (isSelected(colId, opType)) {
    return '2px solid var(--accent-color)';
  }
  if (isCopiedSource(colId, opType)) {
    return '2px dashed var(--accent-color)';
  }
  return undefined;
};

const selectCell = (colId: string, opType: string, multiSelect: boolean) => {
  const key = `${colId}:::${opType}`;
  if (multiSelect) {
    if (selectedCells.value.has(key)) {
      selectedCells.value.delete(key);
      if (lastSelectedCell.value?.colId === colId && lastSelectedCell.value?.opType === opType) {
        const remaining = Array.from(selectedCells.value);
        if (remaining.length > 0) {
          const parts = remaining[remaining.length - 1].split(':::');
          lastSelectedCell.value = { colId: parts[0], opType: parts[1] };
        } else {
          lastSelectedCell.value = null;
        }
      }
    } else {
      selectedCells.value.add(key);
      lastSelectedCell.value = { colId, opType };
    }
  } else {
    selectedCells.value.clear();
    selectedCells.value.add(key);
    lastSelectedCell.value = { colId, opType };
  }
};

const selectColumn = (colId: string) => {
  selectedCells.value.clear();
  props.exampleTransactions.forEach(example => {
    selectedCells.value.add(`${colId}:::${example.opType}`);
  });
  if (props.exampleTransactions.length > 0) {
    const firstOpType = props.exampleTransactions[0].opType;
    lastSelectedCell.value = { colId, opType: firstOpType };
    nextTick(() => {
      const selector = `#cell-${sanitizeId(firstOpType)}-${colId}`;
      const el = document.querySelector(selector) as HTMLTableCellElement;
      if (el) el.focus();
    });
  }
};

const getFirstSelectedCell = (): { colId: string; opType: string } | null => {
  const firstKey = Array.from(selectedCells.value)[0];
  if (!firstKey) return null;
  const parts = firstKey.split(':::');
  return { colId: parts[0], opType: parts[1] };
};

const openWizardForSelected = () => {
  if (selectedCells.value.size === 0) return;

  const primary = lastSelectedCell.value || getFirstSelectedCell();
  if (!primary) return;

  const targets = Array.from(selectedCells.value).map(key => {
    const parts = key.split(':::');
    return { colId: parts[0], opType: parts[1] };
  });

  const isGlobal = targets.length > 1;
  const dbOpType = primary.opType ? props.operationTypeMappings[primary.opType] : null;

  emit('open-wizard', {
    colId: primary.colId,
    opType: isGlobal ? null : dbOpType,
    targets: isGlobal
      ? [{ colId: primary.colId, opType: null }]
      : targets.map(t => ({ colId: t.colId, opType: t.opType })),
    rawAction: primary.opType
  });
};

const handleCellClick = (colId: string, opType: string, event: MouseEvent) => {
  const isCtrl = event.ctrlKey || event.metaKey;
  const isAlreadySelected = isSelected(colId, opType);

  if (!isCtrl && isAlreadySelected && selectedCells.value.size === 1) {
    openWizardForSelected();
  } else {
    selectCell(colId, opType, isCtrl);
    (event.currentTarget as HTMLTableCellElement).focus();
  }
};

const copyMapping = (colId: string, opType: string) => {
  const conf = props.columnConfigMap[colId];
  if (!conf) return;

  const mappingToCopy = conf.typeSpecific[opType] || (props.operationTypeMappings[opType] ? conf.typeSpecific[props.operationTypeMappings[opType]] : null);

  if (mappingToCopy && mappingToCopy.dbKey) {
    copiedMapping.value = {
      colId,
      opType,
      dbKey: mappingToCopy.dbKey,
      divisor: mappingToCopy.divisor,
      multiplier: mappingToCopy.multiplier,
      enumMappings: mappingToCopy.enumMappings ? { ...mappingToCopy.enumMappings } : undefined,
      dateFormat: mappingToCopy.dateFormat
    };
    flashCell(colId, opType, 'bg-indigo-100/50 dark:bg-indigo-950/30 transition-all duration-300');
  }
};

const canPaste = (colId: string, opType: string): boolean => {
  if (!copiedMapping.value) return false;
  if (copiedMapping.value.colId === colId && copiedMapping.value.opType === opType) return false;
  return true;
};

const pasteMappingToSelected = () => {
  if (!copiedMapping.value || selectedCells.value.size === 0) return;

  selectedCells.value.forEach(key => {
    const parts = key.split(':::');
    const targetColId = parts[0];
    const targetOpType = parts[1];

    if (canPaste(targetColId, targetOpType)) {
      emit('update-mapping', {
        colId: targetColId,
        opType: targetOpType,
        mapping: {
          dbKey: copiedMapping.value!.dbKey,
          divisor: copiedMapping.value!.divisor,
          multiplier: copiedMapping.value!.multiplier,
          enumMappings: copiedMapping.value!.enumMappings,
          dateFormat: copiedMapping.value!.dateFormat
        }
      });
      flashCell(targetColId, targetOpType, 'bg-emerald-100/50 dark:bg-emerald-950/30 transition-all duration-300');
    }
  });
};

const clearMappingForSelected = () => {
  if (selectedCells.value.size === 0) return;

  selectedCells.value.forEach(key => {
    const parts = key.split(':::');
    const targetColId = parts[0];
    const targetOpType = parts[1];

    emit('update-mapping', {
      colId: targetColId,
      opType: targetOpType || null,
      mapping: null
    });
    flashCell(targetColId, targetOpType, 'bg-rose-100/50 dark:bg-rose-950/30 transition-all duration-300');
  });
};

const navigateGrid = (key: string) => {
  const primary = lastSelectedCell.value || getFirstSelectedCell();
  if (!primary) return;

  const colId = primary.colId;
  const opType = primary.opType;

  const rowIdx = props.exampleTransactions.findIndex(e => e.opType === opType);
  if (rowIdx === -1) return;

  const numCols = props.uiColumns.length;
  const numRows = props.exampleTransactions.length;

  let currentColIdx = props.uiColumns.findIndex(c => c.id === colId);
  if (currentColIdx === -1) currentColIdx = 0;

  let nextColIdx = currentColIdx;
  let nextRowIdx = rowIdx;

  if (key === 'ArrowLeft') {
    nextColIdx = nextColIdx - 1;
    if (nextColIdx < 0) nextColIdx = numCols - 1;
  } else if (key === 'ArrowRight') {
    nextColIdx = nextColIdx + 1;
    if (nextColIdx >= numCols) nextColIdx = 0;
  } else if (key === 'ArrowUp') {
    nextRowIdx = rowIdx - 1;
    if (nextRowIdx < 0) nextRowIdx = numRows - 1;
  } else if (key === 'ArrowDown') {
    nextRowIdx = rowIdx + 1;
    if (nextRowIdx >= numRows) nextRowIdx = 0;
  }

  const nextColId = props.uiColumns[nextColIdx].id;
  const nextOpType = props.exampleTransactions[nextRowIdx].opType;

  selectedCells.value.clear();
  const nextKey = `${nextColId}:::${nextOpType}`;
  selectedCells.value.add(nextKey);
  lastSelectedCell.value = { colId: nextColId, opType: nextOpType };

  nextTick(() => {
    const selector = `#cell-${sanitizeId(nextOpType)}-${nextColId}`;
    const el = document.querySelector(selector) as HTMLTableCellElement;
    if (el) el.focus();
  });
};

const handleKeyDown = (e: KeyboardEvent) => {
  const target = e.target as HTMLElement;
  if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
    return;
  }

  if (selectedCells.value.size === 0) return;

  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const isCopy = (isMac ? e.metaKey : e.ctrlKey) && e.key.toLowerCase() === 'c';
  const isPaste = (isMac ? e.metaKey : e.ctrlKey) && e.key.toLowerCase() === 'v';
  const isClear = e.key === 'Delete' || e.key === 'Backspace';
  const isEnter = e.key === 'Enter' || e.key === ' ';

  if (isCopy) {
    e.preventDefault();
    const primary = lastSelectedCell.value || getFirstSelectedCell();
    if (primary) {
      copyMapping(primary.colId, primary.opType);
    }
  } else if (isPaste) {
    e.preventDefault();
    pasteMappingToSelected();
  } else if (isClear) {
    e.preventDefault();
    clearMappingForSelected();
  } else if (isEnter) {
    e.preventDefault();
    openWizardForSelected();
  } else if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
    e.preventDefault();
    navigateGrid(e.key);
  }
};

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown);
});

const getResolvedKeyForCell = (colId: string, opType: string) => {
  const dbOpType = props.operationTypeMappings[opType];
  if (!dbOpType) {
    return '';
  }

  const conf = props.columnConfigMap[colId];
  if (!conf) return '';
  
  if (conf.typeSpecific[opType] !== undefined) {
    return conf.typeSpecific[opType].dbKey || '';
  }
  
  if (conf.typeSpecific[dbOpType] !== undefined) {
    return conf.typeSpecific[dbOpType].dbKey || '';
  }
  
  return conf.global?.dbKey || '';
};

const prevExampleForType = (opType: string) => {
  emit('prev-example', opType);
};

const nextExampleForType = (opType: string) => {
  emit('next-example', opType);
};

const duplicateCol = (colId: string) => {
  emit('duplicate-column', colId);
};

const deleteCol = (colId: string) => {
  emit('delete-column', colId);
};

const sanitizeId = (val: string) => {
  return encodeURIComponent(val).replace(/%/g, '_');
};

const dbOpOptions = computed(() => {
  const enumVals = props.importFields.find(f => f.key === 'operation_type')?.enum_values || [];
  return enumVals.map((opt: string) => ({
    value: opt,
    label: opt
  }));
});
</script>

<template>
  <div>
    <div style="overflow: auto; max-height: 400px; max-width: 100%; border: 1px solid var(--border-color); border-radius: var(--radius-sm); margin-bottom: 0.5rem; position: relative;">
      <table class="preview-table" style="margin-top: 0; min-width: 100%;">
        <thead>
          <tr>
            <th style="min-width: 180px; padding: 0.2rem 0.35rem; background-color: var(--bg-tertiary); font-weight: 700; color: var(--text-secondary); text-align: center;">
              Raw File Action & DB Type
            </th>
            <th 
              v-for="col in uiColumns" 
              :key="col.id"
              style="min-width: 140px; padding: 0.2rem 0.35rem; vertical-align: top; transition: background-color 0.15s ease;"
              class="group select-none"
            >
              <div style="display: flex; flex-direction: column; gap: 0.15rem;">
                <div style="font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer;" :title="col.label" @click="selectColumn(col.id)">
                  {{ col.label }}
                </div>
                <div style="display: flex; gap: 0.25rem; margin-top: 0.15rem;">
                  <button 
                    @click="duplicateCol(col.id)" 
                    type="button" 
                    title="Duplicate Column mapping"
                    class="bg-transparent border-0 p-0 text-text-secondary hover:text-accent-color cursor-pointer flex items-center justify-center transition-colors"
                  >
                    <Plus style="width: 12px; height: 12px;" />
                  </button>
                  <button 
                    v-if="col.isDuplicate"
                    @click="deleteCol(col.id)" 
                    type="button" 
                    title="Remove duplicate mapping"
                    class="bg-transparent border-0 p-0 text-text-secondary hover:text-color-danger cursor-pointer flex items-center justify-center transition-colors"
                  >
                    <Trash2 style="width: 12px; height: 12px; color: var(--color-danger);" />
                  </button>
                </div>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Example rows per type -->
          <tr v-for="example in exampleTransactions" :key="example.opType">
            <td style="vertical-align: middle; text-align: left; padding: 0.25rem 0.35rem; min-width: 180px; background-color: var(--bg-secondary);">
              <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                <div style="display: flex; align-items: center; gap: 0.35rem; padding: 0.05rem; white-space: nowrap;">
                  <span class="badge" :class="'badge-' + (operationTypeMappings[example.opType] || 'unknown')" style="padding: 0.15rem 0.35rem; font-size: 0.65rem; text-transform: uppercase; min-width: 85px; text-align: center; display: inline-block;">
                     {{ example.opType }}
                  </span>
                  
                  <!-- Compact Switcher Controls -->
                  <div v-if="example.totalMatches > 1" style="display: flex; align-items: center; gap: 0.15rem;">
                    <button @click.stop="prevExampleForType(example.opType)" style="background: none; border: none; padding: 0 2px; font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center;" title="Previous Example">&larr;</button>
                    <button @click.stop="nextExampleForType(example.opType)" style="background: none; border: none; padding: 0 2px; font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center;" title="Next Example">&rarr;</button>
                  </div>
    
                  <span v-if="liveValidationStats[operationTypeMappings[example.opType]]" :style="{
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    color: liveValidationStats[operationTypeMappings[example.opType]].failed > 0 ? 'var(--color-danger)' : 'var(--color-success)'
                  }">
                    ({{ liveValidationStats[operationTypeMappings[example.opType]].success }}/{{ liveValidationStats[operationTypeMappings[example.opType]].total }})
                  </span>
                </div>
                
                <!-- Direct Database Type Dropdown Select -->
                <CustomDropdown
                  :model-value="operationTypeMappings[example.opType] || ''"
                  @update:model-value="dbOpType => emit('update-optype-mapping', { rawAction: example.opType, dbOpType })"
                  :options="dbOpOptions"
                  :searchable="false"
                  placeholder="-- Map to DB Transaction Type --"
                  :showClear="true"
                  clearLabel="-- Map to DB Transaction Type --"
                  :compact="true"
                />
              </div>
            </td>
            <td 
              v-for="col in uiColumns" 
              :key="col.id" 
              :id="`cell-${sanitizeId(example.opType)}-${col.id}`"
              tabindex="0"
              @click="handleCellClick(col.id, example.opType, $event)" 
              @dblclick="openWizardForSelected()"
              :style="{ 
                outline: getCellOutlineStyle(col.id, example.opType),
                outlineOffset: '-2px'
              }" 
              class="group focus:outline-none focus:bg-slate-100/50 dark:focus:bg-slate-800/30 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-all duration-150 cursor-pointer"
              :class="recentlyFlashed[`${col.id}-${example.opType}`] || ''"
              style="vertical-align: middle; position: relative; padding: 0.15rem 0.3rem; max-width: 160px;"
            >
              <div style="display: flex; flex-direction: column; gap: 0.05rem; overflow: hidden;">
                <span style="font-family: monospace; font-size: 0.7rem; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="example.csvRow[col.colIdx] || '—'">
                  {{ example.csvRow[col.colIdx] || '—' }}
                </span>
                <span v-if="getResolvedKeyForCell(col.id, example.opType)" style="font-size: 0.65rem; color: var(--accent-color); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="importFields.find(f => f.key === getResolvedKeyForCell(col.id, example.opType))?.label || getResolvedKeyForCell(col.id, example.opType)">
                  → {{ importFields.find(f => f.key === getResolvedKeyForCell(col.id, example.opType))?.label || getResolvedKeyForCell(col.id, example.opType) }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Discrete Shortcuts Tip & Clipboard Status Bar -->
    <div class="mt-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-text-secondary px-1 py-1 border-t border-border-color/30">
      <div class="flex items-center gap-1.5">
        <span class="inline-block w-1.5 h-1.5 rounded-full bg-accent-color opacity-85"></span>
        <span>Click to select. Use <kbd class="px-1.5 py-0.5 bg-bg-tertiary border border-border-color rounded text-[0.65rem] font-bold shadow-sm font-sans">Ctrl+C</kbd> / <kbd class="px-1.5 py-0.5 bg-bg-tertiary border border-border-color rounded text-[0.65rem] font-bold shadow-sm font-sans">Ctrl+V</kbd> to copy/paste, <kbd class="px-1.5 py-0.5 bg-bg-tertiary border border-border-color rounded text-[0.65rem] font-bold shadow-sm font-sans">Del</kbd> to clear. Double-click or press <kbd class="px-1.5 py-0.5 bg-bg-tertiary border border-border-color rounded text-[0.65rem] font-bold shadow-sm font-sans">Enter</kbd> to edit.</span>
      </div>
      <div v-if="copiedMapping" class="flex items-center gap-1.5 text-accent-color font-semibold animate-[fadeIn_0.2s_ease-out]">
        <span>Clipboard active: "{{ importFields.find(f => f.key === copiedMapping?.dbKey)?.label || copiedMapping?.dbKey }}"</span>
        <button @click="copiedMapping = null" type="button" class="text-text-secondary hover:text-accent-color p-0 bg-transparent border-0 cursor-pointer text-[1.1rem] leading-none transition-colors" title="Clear clipboard">&times;</button>
      </div>
    </div>
  </div>
</template>

