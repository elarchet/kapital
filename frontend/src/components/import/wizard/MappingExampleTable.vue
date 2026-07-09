<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import { Trash2, MoreHorizontal, ArrowUpDown, Copy } from '@lucide/vue';
import type { ColMapping } from '../../../services/import/types';
import DynamicComponent from '../../DynamicComponent.vue';
import { useTableGridSelection } from './useTableGridSelection';

const props = defineProps<{
  importFileHeaders: string[];
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean; width?: number }>;
  operationTypeColumnIdx: number | null;
  columnConfigMap: Record<string, {
    global?: ColMapping;
    typeSpecific: Record<string, ColMapping>;
  }>;
  activeDbOpTypes: string[];
  uniqueOperationTypes: string[];
  operationTypeMappings: Record<string, string>;
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
  enrichedNames: Record<string, string>;
}>()

const emit = defineEmits<{
  (e: 'open-wizard', payload: { colId: string; opType: string | null; targets?: Array<{ colId: string; opType: string | null }>; rawAction?: string | null }): void;
  (e: 'prev-example', opType: string): void;
  (e: 'next-example', opType: string): void;
  (e: 'update-mapping', payload: { colId: string; opType: string | null; mapping: any }): void;
  (e: 'update-optype-mapping', payload: { rawAction: string; dbOpType: string }): void;
  (e: 'duplicate-column', colId: string): void;
  (e: 'delete-column', colId: string): void;
  (e: 'show-verification', dbOpType: string): void;
  (e: 'resize-column', payload: { colId: string; width: number }): void;
  (e: 'sort-column', payload: { colKey: 'raw' | 'db'; direction: 'asc' | 'desc' }): void;
}>();

// --- Manual Sticky Header Logic ---
const tableWrapperRef = ref<HTMLElement | null>(null);
const stickyTranslateY = ref(0);

const handleScroll = (e?: Event) => {
  if (!tableWrapperRef.value) return;
  // Fallback to searching DOM if event target isn't useful, but prioritize closest
  const scrollContainer = tableWrapperRef.value.closest('.overflow-y-auto') || document.documentElement;
  
  const containerRect = scrollContainer.getBoundingClientRect();
  const wrapperRect = tableWrapperRef.value.getBoundingClientRect();

  const offset = containerRect.top - wrapperRect.top;

  if (offset > 0) {
    const maxOffset = wrapperRect.height - 40; // rough header height
    stickyTranslateY.value = Math.min(offset, maxOffset);
  } else {
    stickyTranslateY.value = 0;
  }
};

onMounted(() => {
  // Use capture: true because 'scroll' events do NOT bubble.
  // This guarantees we catch the scroll event on ANY scrollable ancestor, regardless of Vue mounting order!
  window.addEventListener('scroll', handleScroll, { capture: true, passive: true });
  window.addEventListener('resize', handleScroll);
  // Initial check in case it's already scrolled
  setTimeout(handleScroll, 100);
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll, { capture: true });
  window.removeEventListener('resize', handleScroll);
});

const {
  copiedMapping,
  recentlyFlashed,
  getCellOutlineStyle,
  handleCellClick,
  openWizardForSelected,
  selectColumn,
  getResolvedKeyForCell,
  sanitizeId,
} = useTableGridSelection(props, emit);

const prevExampleForType = (opType: string) => emit('prev-example', opType);
const nextExampleForType = (opType: string) => emit('next-example', opType);
const duplicateCol = (colId: string) => emit('duplicate-column', colId);
const deleteCol = (colId: string) => emit('delete-column', colId);

// ─── Column menu (··· dropdown) ────────────────────────────────────────────
const openMenuColId = ref<string | null>(null);

const toggleMenu = (colId: string, e: MouseEvent) => {
  e.stopPropagation();
  openMenuColId.value = openMenuColId.value === colId ? null : colId;
};

const closeMenu = () => { openMenuColId.value = null; };

const handleDocClick = () => closeMenu();
onMounted(() => document.addEventListener('click', handleDocClick));
onBeforeUnmount(() => document.removeEventListener('click', handleDocClick));

// ─── Frozen column widths ──────────────────────────────────────────────────
const RAW_MIN = 120;
const DB_MIN = 75;
const rawActionWidth = ref<number>(190);
const dbTypeWidth = ref<number>(170);

// ─── Column Resizing ───────────────────────────────────────────────────────
const resizingCol = ref<{ id: string | 'raw' | 'db'; startX: number; startWidth: number } | null>(null);

const startColumnResize = (e: MouseEvent, col: any) => {
  resizingCol.value = { id: col.id, startX: e.clientX, startWidth: col.width || 180 };
  document.addEventListener('mousemove', onColumnMouseMove);
  document.addEventListener('mouseup', onColumnMouseUp);
  e.stopPropagation();
};

const startFrozenResize = (e: MouseEvent, type: 'raw' | 'db') => {
  resizingCol.value = {
    id: type,
    startX: e.clientX,
    startWidth: type === 'raw' ? rawActionWidth.value : dbTypeWidth.value
  };
  document.addEventListener('mousemove', onColumnMouseMove);
  document.addEventListener('mouseup', onColumnMouseUp);
  e.stopPropagation();
};

const onColumnMouseMove = (e: MouseEvent) => {
  if (!resizingCol.value) return;
  const diffX = e.clientX - resizingCol.value.startX;
  if (resizingCol.value.id === 'raw') {
    rawActionWidth.value = Math.max(RAW_MIN, resizingCol.value.startWidth + diffX);
  } else if (resizingCol.value.id === 'db') {
    dbTypeWidth.value = Math.max(DB_MIN, resizingCol.value.startWidth + diffX);
  } else {
    const newWidth = Math.max(60, resizingCol.value.startWidth + diffX);
    emit('resize-column', { colId: resizingCol.value.id, width: newWidth });
  }
};

const onColumnMouseUp = () => {
  resizingCol.value = null;
  document.removeEventListener('mousemove', onColumnMouseMove);
  document.removeEventListener('mouseup', onColumnMouseUp);
};

// ─── DB op type options ────────────────────────────────────────────────────
const dbOpOptions = computed(() => {
  const enumVals = props.importFields.find(f => f.key === 'operation_type')?.enum_values || [];
  return enumVals.map((opt: string) => ({ value: opt, label: opt }));
});

// ─── Ticker index cache ────────────────────────────────────────────────────
const tickerColIdxMap = computed(() => {
  const map: Record<string, number> = {};
  props.exampleTransactions.forEach(example => {
    const opType = example.opType;
    const tickerCol = props.uiColumns.find(col => {
      const conf = props.columnConfigMap?.[col.id];
      const spec = conf?.typeSpecific[opType];
      const glob = conf?.global;
      return spec?.dbKey === 'ticker' || glob?.dbKey === 'ticker';
    });
    map[opType] = tickerCol ? tickerCol.colIdx : -1;
  });
  return map;
});

// ─── Deterministic mock TX IDs ─────────────────────────────────────────────
const rowTxIdMap = computed(() => {
  const map: Record<number, string> = {};
  props.exampleTransactions.forEach(example => {
    const s = example.csvRow.join(',');
    let h1 = 5381, h2 = 52711;
    for (let i = 0; i < s.length; i++) {
      const c = s.charCodeAt(i);
      h1 = (h1 * 33) ^ c;
      h2 = (h2 * 37) ^ c;
    }
    const a = Math.abs(h1).toString(16).padStart(8, '0');
    const b = Math.abs(h2).toString(16).padStart(8, '0');
    map[example.rowIdx] = `auto-${(a + b).slice(0, 16)}`;
  });
  return map;
});

// ─── Cell info cache ───────────────────────────────────────────────────────
const cellInfoMap = computed(() => {
  const map: Record<string, {
    dbKey: string; label: string; displayValue: string;
    valueColor: string; valueFontWeight: string;
  }> = {};

  props.exampleTransactions.forEach(example => {
    const { opType, csvRow, rowIdx } = example;

    props.uiColumns.forEach(col => {
      const colId = col.id;
      const cellVal = csvRow[col.colIdx] || '';
      const rawVal = cellVal.trim();

      const dbKey = getResolvedKeyForCell(colId, opType);
      const field = props.importFields.find(f => f.key === dbKey);
      const label = field?.label || dbKey;

      let displayValue = cellVal || '—';
      let valueColor = 'var(--text-primary)';
      let valueFontWeight = '500';

      if (dbKey === 'name') {
        const tickerIdx = tickerColIdxMap.value[opType] ?? -1;
        const ticker = tickerIdx !== -1 && tickerIdx < csvRow.length ? csvRow[tickerIdx]?.trim() : '';
        const specConf = props.columnConfigMap?.[colId]?.typeSpecific?.[opType];
        const mode = specConf?.dbKey === 'name' ? (specConf.enrichAssetNames || 'when_empty') : 'when_empty';
        if (mode === 'always') {
          const resolved = ticker ? (props.enrichedNames[ticker] || 'Resolving name...') : 'No Ticker mapped';
          displayValue = `→ ${resolved}`;
          valueColor = (resolved.includes('(Not Found)') || resolved === 'No Ticker mapped') ? 'var(--color-danger)' : 'var(--color-success)';
          valueFontWeight = 'bold';
        } else if (mode === 'when_empty' && !rawVal) {
          const resolved = ticker ? (props.enrichedNames[ticker] || 'Resolving name...') : 'No Ticker mapped';
          displayValue = `→ ${resolved}`;
          valueColor = (resolved.includes('(Not Found)') || resolved === 'No Ticker mapped') ? 'var(--color-danger)' : 'var(--color-success)';
          valueFontWeight = 'bold';
        } else if (mode === 'when_empty') {
          displayValue = cellVal;
        }
      } else if (dbKey === 'transaction_id') {
        const mockId = rowTxIdMap.value[rowIdx] || '';
        const specConf = props.columnConfigMap?.[colId]?.typeSpecific?.[opType];
        const mode = specConf?.dbKey === 'transaction_id' ? (specConf.enrichTransactionIds || 'when_empty') : 'when_empty';
        if (mode === 'always') {
          displayValue = `→ ${mockId}`;
          valueColor = 'var(--accent-color)';
          valueFontWeight = 'bold';
        } else if (mode === 'when_empty' && !rawVal) {
          displayValue = `→ ${mockId}`;
          valueColor = 'var(--color-success)';
          valueFontWeight = 'bold';
        } else if (mode === 'when_empty') {
          displayValue = cellVal;
        }
      }

      map[`${colId}:::${opType}`] = { dbKey, label, displayValue, valueColor, valueFontWeight };
    });
  });

  return map;
});
</script>

<template>
  <div class="select-none">
    <!-- Single unified scrollable table — header and body never desync -->
    <div
      ref="tableWrapperRef"
      style="width: 100%; overflow-x: auto; margin-bottom: 0.5rem; position: relative; scroll-snap-type: x mandatory; overscroll-behavior-x: none;"
    >
      <table
        class="preview-table preview-table-double-sticky"
        :style="{ '--raw-action-width': rawActionWidth + 'px' }"
        style="margin-top: 0; min-width: 100%; border: none; border-collapse: separate; border-spacing: 0;"
      >
        <!-- ── Sticky Header ─────────────────────────────────────────── -->
        <thead ref="theadRef" style="position: relative; z-index: 20;">
          <tr>
            <!-- Frozen: Raw Action -->
            <th
              class="group select-none"
              :style="{
                transform: `translateY(${stickyTranslateY}px)`, backgroundColor: 'var(--bg-tertiary)', boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                minWidth: rawActionWidth + 'px', maxWidth: rawActionWidth + 'px', width: rawActionWidth + 'px',
                padding: '0.2rem 0.35rem', fontWeight: 700, color: 'var(--text-secondary)',
                textAlign: 'center', boxSizing: 'border-box', position: 'relative',
                scrollSnapAlign: 'start'
              }"
            >
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.25rem; position: relative;">
                <span>Raw Action</span>
                <!-- ··· menu -->
                <div style="position: relative; flex-shrink: 0;">
                  <button
                    @click.stop="toggleMenu('__raw__', $event)"
                    type="button"
                    class="opacity-0 group-hover:opacity-100 transition-opacity bg-transparent border-0 p-0 cursor-pointer flex items-center text-text-secondary hover:text-text-primary"
                    style="line-height: 1;"
                    title="Column options"
                  >
                    <MoreHorizontal style="width: 14px; height: 14px;" />
                  </button>
                  <div
                    v-if="openMenuColId === '__raw__'"
                    @click.stop
                    class="col-menu"
                  >
                    <button class="col-menu-item" @click="emit('sort-column', { colKey: 'raw', direction: 'asc' }); closeMenu()">
                      <ArrowUpDown style="width: 12px; height: 12px;" /> Sort A → Z
                    </button>
                    <button class="col-menu-item" @click="emit('sort-column', { colKey: 'raw', direction: 'desc' }); closeMenu()">
                      <ArrowUpDown style="width: 12px; height: 12px;" /> Sort Z → A
                    </button>
                  </div>
                </div>
              </div>
              <!-- resize handle -->
              <div style="position: absolute; right: 0; top: 0; bottom: 0; width: 6px; cursor: col-resize; z-index: 10;" @mousedown="startFrozenResize($event, 'raw')" @click.stop></div>
            </th>

            <!-- Frozen: DB Transaction Type -->
            <th
              class="group select-none"
              :style="{
                transform: `translateY(${stickyTranslateY}px)`, backgroundColor: 'var(--bg-tertiary)', boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                minWidth: dbTypeWidth + 'px', maxWidth: dbTypeWidth + 'px', width: dbTypeWidth + 'px',
                padding: '0.2rem 0.35rem', fontWeight: 700, color: 'var(--text-secondary)',
                textAlign: 'center', boxSizing: 'border-box', position: 'relative',
                left: rawActionWidth + 'px',
                scrollSnapAlign: 'start'
              }"
            >
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.25rem; position: relative;">
                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">DB Type</span>
                <!-- ··· menu -->
                <div style="position: relative; flex-shrink: 0;">
                  <button
                    @click.stop="toggleMenu('__db__', $event)"
                    type="button"
                    class="opacity-0 group-hover:opacity-100 transition-opacity bg-transparent border-0 p-0 cursor-pointer flex items-center text-text-secondary hover:text-text-primary"
                    style="line-height: 1;"
                    title="Column options"
                  >
                    <MoreHorizontal style="width: 14px; height: 14px;" />
                  </button>
                  <div
                    v-if="openMenuColId === '__db__'"
                    @click.stop
                    class="col-menu"
                  >
                    <button class="col-menu-item" @click="emit('sort-column', { colKey: 'db', direction: 'asc' }); closeMenu()">
                      <ArrowUpDown style="width: 12px; height: 12px;" /> Sort A → Z
                    </button>
                    <button class="col-menu-item" @click="emit('sort-column', { colKey: 'db', direction: 'desc' }); closeMenu()">
                      <ArrowUpDown style="width: 12px; height: 12px;" /> Sort Z → A
                    </button>
                  </div>
                </div>
              </div>
              <!-- resize handle -->
              <div style="position: absolute; right: 0; top: 0; bottom: 0; width: 6px; cursor: col-resize; z-index: 10;" @mousedown="startFrozenResize($event, 'db')" @click.stop></div>
            </th>

            <!-- Dynamic columns -->
            <th
              v-for="(col) in uiColumns"
              :key="col.id"
              :style="{
                transform: `translateY(${stickyTranslateY}px)`, backgroundColor: 'var(--bg-tertiary)', boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                minWidth: (col.width || 180) + 'px', maxWidth: (col.width || 180) + 'px',
                width: (col.width || 180) + 'px', padding: '0.2rem 0.35rem',
                verticalAlign: 'top', boxSizing: 'border-box', position: 'relative',
                scrollSnapAlign: 'start'
              }"
              class="group select-none"
            >
              <div style="display: flex; flex-direction: column; gap: 0.15rem; position: relative; padding-right: 20px;">
                <!-- Label -->
                <div
                  style="font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer;"
                  :title="col.label"
                  @click="selectColumn(col.id)"
                >
                  {{ col.label }}
                </div>

                <!-- ··· menu button -->
                <div style="position: absolute; top: 0; right: 0; z-index: 15;">
                  <button
                    @click.stop="toggleMenu(col.id, $event)"
                    type="button"
                    class="opacity-0 group-hover:opacity-100 transition-opacity bg-transparent border-0 p-0.5 cursor-pointer flex items-center text-text-secondary hover:text-text-primary rounded"
                    title="Column options"
                  >
                    <MoreHorizontal style="width: 14px; height: 14px;" />
                  </button>
                  <!-- Dropdown -->
                  <div
                    v-if="openMenuColId === col.id"
                    @click.stop
                    class="col-menu"
                  >
                    <button class="col-menu-item" @click="duplicateCol(col.id); closeMenu()">
                      <Copy style="width: 12px; height: 12px;" /> Duplicate column
                    </button>
                    <button v-if="col.isDuplicate" class="col-menu-item col-menu-item--danger" @click="deleteCol(col.id); closeMenu()">
                      <Trash2 style="width: 12px; height: 12px;" /> Remove duplicate
                    </button>
                  </div>
                </div>
              </div>

              <!-- resize handle -->
              <div
                style="position: absolute; right: 0; top: 0; bottom: 0; width: 6px; cursor: col-resize; z-index: 10;"
                @mousedown="startColumnResize($event, col)"
                @click.stop
              ></div>
            </th>
          </tr>
        </thead>

        <!-- ── Body ─────────────────────────────────────────────────── -->
        <tbody>
          <tr
            v-for="example in exampleTransactions"
            :key="example.opType"
          >
            <!-- Frozen: Raw Action -->
            <td :style="{
              verticalAlign: 'middle', textAlign: 'left', padding: '0.25rem 0.35rem',
              minWidth: rawActionWidth + 'px', maxWidth: rawActionWidth + 'px', width: rawActionWidth + 'px',
              boxSizing: 'border-box'
            }">
              <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.35rem; overflow: hidden; width: 100%;">
                <!-- Badge -->
                <div style="flex: 1; min-width: 0; display: flex; align-items: center;">
                  <span
                    class="badge max-w-full"
                    :class="'badge-' + (operationTypeMappings[example.opType] || 'unknown')"
                    style="padding: 0.15rem 0.45rem; font-size: 0.65rem; text-transform: uppercase; width: fit-content; text-align: left; display: inline-block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle;"
                    :title="example.opType"
                  >
                    {{ example.opType }}
                  </span>
                </div>

                <!-- Nav + stats -->
                <div style="display: flex; align-items: center; gap: 0.25rem; flex-shrink: 0;">
                  <div v-if="example.totalMatches > 1" style="display: flex; align-items: center; gap: 0.15rem;">
                    <button @click.stop="prevExampleForType(example.opType)" style="background: none; border: none; padding: 0 2px; font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center;" title="Previous Example">&larr;</button>
                    <button @click.stop="nextExampleForType(example.opType)" style="background: none; border: none; padding: 0 2px; font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center;" title="Next Example">&rarr;</button>
                  </div>
                  <span
                    v-if="liveValidationStats[example.opType]"
                    @click.stop="emit('show-verification', example.opType)"
                    :title="`Click to view simulation verification for ${example.opType}`"
                    class="cursor-pointer hover:underline"
                    :style="{
                      fontSize: '0.65rem', fontWeight: 600,
                      color: liveValidationStats[example.opType].failed > 0 ? 'var(--color-danger)' : 'var(--color-success)'
                    }"
                  >
                    ({{ liveValidationStats[example.opType].success }}/{{ liveValidationStats[example.opType].total }})
                  </span>
                </div>
              </div>
            </td>

            <!-- Frozen: DB Transaction Type -->
            <td :style="{
              verticalAlign: 'middle', textAlign: 'left', padding: '0.25rem 0.35rem',
              minWidth: dbTypeWidth + 'px', maxWidth: dbTypeWidth + 'px', width: dbTypeWidth + 'px',
              boxSizing: 'border-box',
              left: rawActionWidth + 'px'
            }">
              <DynamicComponent
                componentKey="custom-dropdown"
                :model-value="operationTypeMappings[example.opType] || ''"
                @update:model-value="(dbOpType: any) => emit('update-optype-mapping', { rawAction: example.opType, dbOpType })"
                :options="dbOpOptions"
                :searchable="false"
                placeholder="-- Map DB Type --"
                :showClear="true"
                clearLabel="-- Map DB Type --"
                :compact="true"
              />
            </td>

            <!-- Dynamic cells -->
            <td
              v-for="col in uiColumns"
              :key="col.id"
              :id="`cell-${sanitizeId(example.opType)}-${col.id}`"
              tabindex="0"
              @click="handleCellClick(col.id, example.opType, $event)"
              @dblclick="openWizardForSelected()"
              :style="[
                { outline: getCellOutlineStyle(col.id, example.opType), outlineOffset: '-2px' },
                {
                  minWidth: (col.width || 180) + 'px', maxWidth: (col.width || 180) + 'px',
                  width: (col.width || 180) + 'px', verticalAlign: 'middle',
                  position: 'relative', padding: '0.15rem 0.3rem', boxSizing: 'border-box'
                }
              ]"
              class="group focus:outline-none focus:bg-slate-100/50 dark:focus:bg-slate-800/30 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-all duration-150 cursor-pointer"
              :class="recentlyFlashed[`${col.id}:::${example.opType}`] || ''"
            >
              <div style="display: flex; flex-direction: column; gap: 0.05rem; overflow: hidden;">
                <span
                  :style="{ color: cellInfoMap[`${col.id}:::${example.opType}`]?.valueColor, fontWeight: cellInfoMap[`${col.id}:::${example.opType}`]?.valueFontWeight }"
                  style="font-family: monospace; font-size: 0.7rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
                  :title="cellInfoMap[`${col.id}:::${example.opType}`]?.displayValue"
                >
                  {{ cellInfoMap[`${col.id}:::${example.opType}`]?.displayValue }}
                </span>
                <span
                  v-if="cellInfoMap[`${col.id}:::${example.opType}`]?.dbKey"
                  style="font-size: 0.65rem; color: var(--accent-color); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
                  :title="cellInfoMap[`${col.id}:::${example.opType}`]?.label"
                >
                  → {{ cellInfoMap[`${col.id}:::${example.opType}`]?.label }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Shortcuts bar -->
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

<style scoped>
/* Column context menu */
.col-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  z-index: 100;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  min-width: 160px;
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.col-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: none;
  background: transparent;
  border-radius: 4px;
  font-size: 0.75rem;
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  width: 100%;
  transition: background 0.1s;
}

.col-menu-item:hover {
  background: var(--bg-tertiary);
}

.col-menu-item--danger {
  color: var(--color-danger);
}
</style>
