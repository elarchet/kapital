<script setup lang="ts">
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps<{
  importFileHeaders: string[];
  operationTypeColumnIdx: number | null;
  columnConfigMap: Record<number, {
    global: { dbKey: string; divisor?: number; multiplier?: number; enumMappings?: Record<string, string>; dateFormat?: string };
    typeSpecific: Record<string, { dbKey: string; divisor?: number; multiplier?: number; enumMappings?: Record<string, string>; dateFormat?: string }>;
  }>;
  activeDbOpTypes: string[];
  importFields: any[];
  exampleTransactions: Array<{
    opType: string;
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
  (e: 'open-wizard', payload: { colIdx: number; opType: string | null; targets?: Array<{ colIdx: number; opType: string | null }> }): void;
  (e: 'prev-example', opType: string): void;
  (e: 'next-example', opType: string): void;
  (e: 'update-mapping', payload: { colIdx: number; opType: string | null; mapping: any }): void;
}>();

// Selected cells for keyboard selection & actions
const selectedCells = ref<Set<string>>(new Set());
const lastSelectedCell = ref<{ colIdx: number; opType: string } | null>(null);

// Clipboard state for copy-pasting mappings
const copiedMapping = ref<{
  colIdx: number;
  opType: string;
  dbKey: string;
  divisor?: number;
  multiplier?: number;
  enumMappings?: Record<string, string>;
  dateFormat?: string;
} | null>(null);

// Cell flashing state for visual shortcut feedback
const recentlyFlashed = ref<Record<string, string>>({}); // cellKey -> CSS class

const flashCell = (colIdx: number, opType: string, flashClass: string) => {
  const key = `${colIdx}-${opType}`;
  recentlyFlashed.value[key] = flashClass;
  setTimeout(() => {
    delete recentlyFlashed.value[key];
  }, 1000);
};

const isSelected = (colIdx: number, opType: string): boolean => {
  const key = `${colIdx}-${opType}`;
  return selectedCells.value.has(key);
};

const isCopiedSource = (colIdx: number, opType: string): boolean => {
  return copiedMapping.value !== null &&
         copiedMapping.value.colIdx === colIdx &&
         copiedMapping.value.opType === opType;
};

const getCellOutlineStyle = (colIdx: number, opType: string) => {
  if (isSelected(colIdx, opType)) {
    return '2px solid var(--accent-color)';
  }
  if (isCopiedSource(colIdx, opType)) {
    return '2px dashed var(--accent-color)';
  }
  return undefined;
};

const selectCell = (colIdx: number, opType: string, multiSelect: boolean) => {
  const key = `${colIdx}-${opType}`;
  if (multiSelect) {
    if (selectedCells.value.has(key)) {
      selectedCells.value.delete(key);
      if (lastSelectedCell.value?.colIdx === colIdx && lastSelectedCell.value?.opType === opType) {
        const remaining = Array.from(selectedCells.value);
        if (remaining.length > 0) {
          const [c, o] = remaining[remaining.length - 1].split('-');
          lastSelectedCell.value = { colIdx: parseInt(c), opType: o };
        } else {
          lastSelectedCell.value = null;
        }
      }
    } else {
      selectedCells.value.add(key);
      lastSelectedCell.value = { colIdx, opType };
    }
  } else {
    selectedCells.value.clear();
    selectedCells.value.add(key);
    lastSelectedCell.value = { colIdx, opType };
  }
};

const selectColumn = (colIdx: number) => {
  if (colIdx === props.operationTypeColumnIdx) return;

  selectedCells.value.clear();
  props.exampleTransactions.forEach(example => {
    selectedCells.value.add(`${colIdx}-${example.opType}`);
  });
  if (props.exampleTransactions.length > 0) {
    const firstOpType = props.exampleTransactions[0].opType;
    lastSelectedCell.value = { colIdx, opType: firstOpType };
    nextTick(() => {
      const selector = `#cell-${firstOpType}-${colIdx}`;
      const el = document.querySelector(selector) as HTMLTableCellElement;
      if (el) el.focus();
    });
  }
};

const getFirstSelectedCell = (): { colIdx: number; opType: string } | null => {
  const firstKey = Array.from(selectedCells.value)[0];
  if (!firstKey) return null;
  const [c, o] = firstKey.split('-');
  return { colIdx: parseInt(c), opType: o };
};

const openWizardForSelected = () => {
  if (selectedCells.value.size === 0) return;

  const primary = lastSelectedCell.value || getFirstSelectedCell();
  if (!primary) return;

  const targets = Array.from(selectedCells.value).map(key => {
    const [c, o] = key.split('-');
    return { colIdx: parseInt(c), opType: o };
  });

  const isGlobal = targets.length > 1;

  emit('open-wizard', {
    colIdx: primary.colIdx,
    opType: isGlobal ? null : primary.opType,
    targets: isGlobal ? [{ colIdx: primary.colIdx, opType: null }] : targets
  });
};

const handleCellClick = (colIdx: number, opType: string, event: MouseEvent) => {
  if (colIdx === props.operationTypeColumnIdx) return;

  const isCtrl = event.ctrlKey || event.metaKey;
  const isAlreadySelected = isSelected(colIdx, opType);

  if (!isCtrl && isAlreadySelected && selectedCells.value.size === 1) {
    openWizardForSelected();
  } else {
    selectCell(colIdx, opType, isCtrl);
    // Focus the cell to receive keyboard events
    (event.currentTarget as HTMLTableCellElement).focus();
  }
};

const copyMapping = (colIdx: number, opType: string) => {
  const conf = props.columnConfigMap[colIdx];
  if (!conf) return;

  const mappingToCopy = conf.typeSpecific[opType];

  if (mappingToCopy && mappingToCopy.dbKey) {
    copiedMapping.value = {
      colIdx,
      opType,
      dbKey: mappingToCopy.dbKey,
      divisor: mappingToCopy.divisor,
      multiplier: mappingToCopy.multiplier,
      enumMappings: mappingToCopy.enumMappings ? { ...mappingToCopy.enumMappings } : undefined,
      dateFormat: mappingToCopy.dateFormat
    };
    flashCell(colIdx, opType, 'bg-indigo-100/50 dark:bg-indigo-950/30 transition-all duration-300');
  }
};

const canPaste = (colIdx: number, opType: string): boolean => {
  if (!copiedMapping.value) return false;
  if (colIdx === props.operationTypeColumnIdx) return false;
  if (copiedMapping.value.colIdx === colIdx && copiedMapping.value.opType === opType) return false;
  return true;
};

const pasteMappingToSelected = () => {
  if (!copiedMapping.value || selectedCells.value.size === 0) return;

  selectedCells.value.forEach(key => {
    const [cStr, oStr] = key.split('-');
    const targetColIdx = parseInt(cStr);
    const targetOpType = oStr;

    if (canPaste(targetColIdx, targetOpType)) {
      emit('update-mapping', {
        colIdx: targetColIdx,
        opType: targetOpType,
        mapping: {
          dbKey: copiedMapping.value!.dbKey,
          divisor: copiedMapping.value!.divisor,
          multiplier: copiedMapping.value!.multiplier,
          enumMappings: copiedMapping.value!.enumMappings,
          dateFormat: copiedMapping.value!.dateFormat
        }
      });
      flashCell(targetColIdx, targetOpType, 'bg-emerald-100/50 dark:bg-emerald-950/30 transition-all duration-300');
    }
  });
};

const clearMappingForSelected = () => {
  if (selectedCells.value.size === 0) return;

  selectedCells.value.forEach(key => {
    const [cStr, oStr] = key.split('-');
    const targetColIdx = parseInt(cStr);
    const targetOpType = oStr;

    emit('update-mapping', {
      colIdx: targetColIdx,
      opType: targetOpType,
      mapping: null
    });
    flashCell(targetColIdx, targetOpType, 'bg-rose-100/50 dark:bg-rose-950/30 transition-all duration-300');
  });
};

const navigateGrid = (key: string) => {
  const primary = lastSelectedCell.value || getFirstSelectedCell();
  if (!primary) return;

  const colIdx = primary.colIdx;
  const opType = primary.opType;

  // Find current row index
  const rowIdx = props.exampleTransactions.findIndex(e => e.opType === opType);
  if (rowIdx === -1) return;

  const numCols = props.importFileHeaders.length;
  const numRows = props.exampleTransactions.length;

  let nextCol = colIdx;
  let nextRowIdx = rowIdx;

  if (key === 'ArrowLeft') {
    do {
      nextCol = nextCol - 1;
      if (nextCol < 0) nextCol = numCols - 1;
    } while (nextCol === props.operationTypeColumnIdx);
  } else if (key === 'ArrowRight') {
    do {
      nextCol = nextCol + 1;
      if (nextCol >= numCols) nextCol = 0;
    } while (nextCol === props.operationTypeColumnIdx);
  } else if (key === 'ArrowUp') {
    nextRowIdx = rowIdx - 1;
    if (nextRowIdx < 0) nextRowIdx = numRows - 1;
  } else if (key === 'ArrowDown') {
    nextRowIdx = rowIdx + 1;
    if (nextRowIdx >= numRows) nextRowIdx = 0;
  }

  const nextOpType = props.exampleTransactions[nextRowIdx].opType;

  selectedCells.value.clear();
  const nextKey = `${nextCol}-${nextOpType}`;
  selectedCells.value.add(nextKey);
  lastSelectedCell.value = { colIdx: nextCol, opType: nextOpType };

  nextTick(() => {
    const selector = `#cell-${nextOpType}-${nextCol}`;
    const el = document.querySelector(selector) as HTMLTableCellElement;
    if (el) el.focus();
  });
};

const handleKeyDown = (e: KeyboardEvent) => {
  const target = e.target as HTMLElement;
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
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
      copyMapping(primary.colIdx, primary.opType);
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

const getResolvedKeyForCell = (colIdx: number, opType: string) => {
  const conf = props.columnConfigMap[colIdx];
  if (!conf) return '';
  return conf.typeSpecific[opType]?.dbKey || '';
};

const prevExampleForType = (opType: string) => {
  emit('prev-example', opType);
};

const nextExampleForType = (opType: string) => {
  emit('next-example', opType);
};
</script>

<template>
  <div>
    <div style="overflow: auto; max-height: 400px; max-width: 100%; border: 1px solid var(--border-color); border-radius: var(--radius-sm); margin-bottom: 0.5rem; position: relative;">
      <table class="preview-table" style="margin-top: 0; min-width: 100%;">
        <thead>
          <tr>
            <th style="min-width: 120px; padding: 0.2rem 0.35rem; background-color: var(--bg-tertiary); font-weight: 700; color: var(--text-secondary); text-align: center;">
              Context & Stats
            </th>
            <th 
              v-for="(h, idx) in importFileHeaders" 
              :key="idx"
              @click="selectColumn(idx)"
              @dblclick="idx !== operationTypeColumnIdx ? (selectColumn(idx), openWizardForSelected()) : null"
              :style="{ cursor: idx !== operationTypeColumnIdx ? 'pointer' : 'default' }"
              :class="[
                idx !== operationTypeColumnIdx ? 'hover:bg-slate-50 dark:hover:bg-slate-800/40 select-none' : ''
              ]"
              style="min-width: 120px; padding: 0.2rem 0.35rem; vertical-align: top; transition: background-color 0.15s ease;"
            >
              <div style="font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" :title="h">
                {{ h }}
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Example rows per type -->
          <tr v-for="example in exampleTransactions" :key="example.opType">
            <td style="vertical-align: middle; text-align: left; padding: 0.15rem 0.3rem;">
              <div style="display: flex; align-items: center; gap: 0.35rem; padding: 0.05rem; white-space: nowrap;">
                <span class="badge" :class="'badge-' + example.opType" style="padding: 0.15rem 0.35rem; font-size: 0.65rem; text-transform: uppercase; min-width: 85px; text-align: center; display: inline-block;">
                  {{ example.opType }}
                </span>
                
                <!-- Compact Switcher Controls -->
                <div v-if="example.totalMatches > 1" style="display: flex; align-items: center; gap: 0.15rem;">
                  <button @click.stop="prevExampleForType(example.opType)" style="background: none; border: none; padding: 0 2px; font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center;" title="Previous Example">&larr;</button>
                  <button @click.stop="nextExampleForType(example.opType)" style="background: none; border: none; padding: 0 2px; font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center;" title="Next Example">&rarr;</button>
                </div>
 
                <span v-if="liveValidationStats[example.opType]" :style="{
                  fontSize: '0.65rem',
                  fontWeight: 600,
                  color: liveValidationStats[example.opType].failed > 0 ? 'var(--color-danger)' : 'var(--color-success)'
                }">
                  ({{ liveValidationStats[example.opType].success }}/{{ liveValidationStats[example.opType].total }})
                </span>
              </div>
            </td>
            <td 
              v-for="(cell, idx) in example.csvRow" 
              :key="idx" 
              :id="`cell-${example.opType}-${idx}`"
              :tabindex="idx !== operationTypeColumnIdx ? 0 : -1"
              @click="idx !== operationTypeColumnIdx ? handleCellClick(idx, example.opType, $event) : null" 
              @dblclick="idx !== operationTypeColumnIdx ? openWizardForSelected() : null"
              :style="{ 
                cursor: idx !== operationTypeColumnIdx ? 'pointer' : 'default',
                outline: getCellOutlineStyle(idx, example.opType),
                outlineOffset: '-2px'
              }" 
              :class="[
                idx !== operationTypeColumnIdx ? 'group focus:outline-none focus:bg-slate-100/50 dark:focus:bg-slate-800/30 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-all duration-150' : '',
                recentlyFlashed[`${idx}-${example.opType}`] || ''
              ]"
              style="vertical-align: middle; position: relative; padding: 0.15rem 0.3rem; max-width: 160px;"
            >
              <div style="display: flex; flex-direction: column; gap: 0.05rem; overflow: hidden;">
                <span style="font-family: monospace; font-size: 0.7rem; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="cell || '—'">
                  {{ cell || '—' }}
                </span>
                <span v-if="getResolvedKeyForCell(idx, example.opType)" style="font-size: 0.65rem; color: var(--accent-color); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="importFields.find(f => f.key === getResolvedKeyForCell(idx, example.opType))?.label || getResolvedKeyForCell(idx, example.opType)">
                  → {{ importFields.find(f => f.key === getResolvedKeyForCell(idx, example.opType))?.label || getResolvedKeyForCell(idx, example.opType) }}
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

