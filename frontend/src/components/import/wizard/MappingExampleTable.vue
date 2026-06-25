<script setup lang="ts">
import { computed } from 'vue';
import { Plus, Trash2 } from '@lucide/vue';
import type { ColMapping } from '../../../services/import/types';
import DynamicComponent from '../../DynamicComponent.vue';
import { useTableGridSelection } from './useTableGridSelection';

const props = defineProps<{
  importFileHeaders: string[];
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }>;
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
}>();

const emit = defineEmits<{
  (e: 'open-wizard', payload: { colId: string; opType: string | null; targets?: Array<{ colId: string; opType: string | null }>; rawAction?: string | null }): void;
  (e: 'prev-example', opType: string): void;
  (e: 'next-example', opType: string): void;
  (e: 'update-mapping', payload: { colId: string; opType: string | null; mapping: any }): void;
  (e: 'update-optype-mapping', payload: { rawAction: string; dbOpType: string }): void;
  (e: 'duplicate-column', colId: string): void;
  (e: 'delete-column', colId: string): void;
  (e: 'show-verification', dbOpType: string): void;
}>();

// Delegate selection, clipboard and keyboard navigation to the composable
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

const dbOpOptions = computed(() => {
  const enumVals = props.importFields.find(f => f.key === 'operation_type')?.enum_values || [];
  return enumVals.map((opt: string) => ({
    value: opt,
    label: opt
  }));
});

// Pre-compute Ticker Column Indices per Operation Type for O(1) loop searches
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

// Pre-compute Deterministic Transaction IDs per Row to avoid hashing during render loop
const rowTxIdMap = computed(() => {
  const map: Record<number, string> = {};
  props.exampleTransactions.forEach(example => {
    const serialized = example.csvRow.join(',');
    let hash1 = 5381;
    let hash2 = 52711;
    for (let i = 0; i < serialized.length; i++) {
      const char = serialized.charCodeAt(i);
      hash1 = (hash1 * 33) ^ char;
      hash2 = (hash2 * 37) ^ char;
    }
    const h1 = Math.abs(hash1).toString(16).padStart(8, '0');
    const h2 = Math.abs(hash2).toString(16).padStart(8, '0');
    const mockHash = (h1 + h2).slice(0, 16);
    map[example.rowIdx] = `auto-${mockHash}`;
  });
  return map;
});

// Cache cell rendering states to optimize rendering speed and apply styling
const cellInfoMap = computed(() => {
  const map: Record<string, {
    dbKey: string;
    label: string;
    displayValue: string;
    valueColor: string;
    valueFontWeight: string;
  }> = {};

  props.exampleTransactions.forEach(example => {
    const opType = example.opType;
    const csvRow = example.csvRow;
    const rowIdx = example.rowIdx;

    props.uiColumns.forEach(col => {
      const colId = col.id;
      const cellVal = csvRow[col.colIdx] || '';
      const rawVal = cellVal.trim();
      
      // Get mapped key and user-facing field label
      const dbKey = getResolvedKeyForCell(colId, opType);
      const field = props.importFields.find(f => f.key === dbKey);
      const label = field?.label || dbKey;

      // Default values
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
        } else if (mode === 'when_empty') {
          if (!rawVal) {
            const resolved = ticker ? (props.enrichedNames[ticker] || 'Resolving name...') : 'No Ticker mapped';
            displayValue = `→ ${resolved}`;
            valueColor = (resolved.includes('(Not Found)') || resolved === 'No Ticker mapped') ? 'var(--color-danger)' : 'var(--color-success)';
            valueFontWeight = 'bold';
          } else {
            displayValue = cellVal;
          }
        }
      } else if (dbKey === 'transaction_id') {
        const mockId = rowTxIdMap.value[rowIdx] || '';
        const specConf = props.columnConfigMap?.[colId]?.typeSpecific?.[opType];
        const mode = specConf?.dbKey === 'transaction_id' ? (specConf.enrichTransactionIds || 'when_empty') : 'when_empty';
        if (mode === 'always') {
          displayValue = `→ ${mockId}`;
          valueColor = 'var(--accent-color)';
          valueFontWeight = 'bold';
        } else if (mode === 'when_empty') {
          if (!rawVal) {
            displayValue = `→ ${mockId}`;
            valueColor = 'var(--color-success)';
            valueFontWeight = 'bold';
          } else {
            displayValue = cellVal;
          }
        }
      }

      map[`${colId}:::${opType}`] = {
        dbKey,
        label,
        displayValue,
        valueColor,
        valueFontWeight
      };
    });
  });

  return map;
});
</script>

<template>
  <div>
    <!-- Table Wrapper Container with maximized height -->
    <div style="overflow: auto; max-height: calc(100vh - 300px); min-height: 250px; max-width: 100%; border: 1px solid var(--border-color); border-radius: var(--radius-sm); margin-bottom: 0.5rem; position: relative; container-type: inline-size;">
      <table class="preview-table preview-table-double-sticky" style="margin-top: 0; min-width: 100%;">
        <thead>
          <tr>
            <th style="min-width: var(--raw-action-width); max-width: var(--raw-action-width); width: var(--raw-action-width); padding: 0.2rem 0.35rem; font-weight: 700; color: var(--text-secondary); text-align: center;">
              Raw Action
            </th>
            <th style="min-width: 170px; max-width: 170px; width: 170px; padding: 0.2rem 0.35rem; font-weight: 700; color: var(--text-secondary); text-align: center;">
              DB Transaction Type
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
            <!-- Column 1: Raw Action -->
            <td style="vertical-align: middle; text-align: left; padding: 0.25rem 0.35rem; min-width: var(--raw-action-width); max-width: var(--raw-action-width); width: var(--raw-action-width);">
              <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.35rem; padding: 0.05rem; overflow: hidden; width: 100%;">
                  <!-- Left: Transaction type value badge -->
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
                  
                  <!-- Right: Switcher controls & Validation Count -->
                  <div style="display: flex; align-items: center; gap: 0.25rem; flex-shrink: 0;">
                    <!-- Compact Switcher Controls -->
                    <div v-if="example.totalMatches > 1" style="display: flex; align-items: center; gap: 0.15rem;">
                      <button @click.stop="prevExampleForType(example.opType)" style="background: none; border: none; padding: 0 2px; font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center;" title="Previous Example">&larr;</button>
                      <button @click.stop="nextExampleForType(example.opType)" style="background: none; border: none; padding: 0 2px; font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center;" title="Next Example">&rarr;</button>
                    </div>
      
                    <!-- Clickable Simulation Stats Count -->
                    <span 
                      v-if="liveValidationStats[example.opType]" 
                      @click.stop="emit('show-verification', example.opType)"
                      :title="`Click to view simulation verification for ${example.opType}`"
                      class="cursor-pointer hover:underline"
                      :style="{
                        fontSize: '0.65rem',
                        fontWeight: 600,
                        color: liveValidationStats[example.opType].failed > 0 ? 'var(--color-danger)' : 'var(--color-success)'
                      }"
                    >
                      ({{ liveValidationStats[example.opType].success }}/{{ liveValidationStats[example.opType].total }})
                    </span>
                  </div>
                </div>
              </div>
            </td>

            <!-- Column 2: DB Transaction Type Dropdown Select -->
            <td style="vertical-align: middle; text-align: left; padding: 0.25rem 0.35rem; min-width: 170px; max-width: 170px; width: 170px;">
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
              :class="recentlyFlashed[`${col.id}:::${example.opType}`] || ''"
              style="vertical-align: middle; position: relative; padding: 0.15rem 0.3rem; max-width: 160px;"
            >
              <div style="display: flex; flex-direction: column; gap: 0.05rem; overflow: hidden;">
                <!-- The value: displays the enriched/live resolved value if enriched, or the raw CSV value -->
                <span 
                  style="font-family: monospace; font-size: 0.7rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" 
                  :style="{ color: cellInfoMap[`${col.id}:::${example.opType}`]?.valueColor, fontWeight: cellInfoMap[`${col.id}:::${example.opType}`]?.valueFontWeight }"
                  :title="cellInfoMap[`${col.id}:::${example.opType}`]?.displayValue"
                >
                  {{ cellInfoMap[`${col.id}:::${example.opType}`]?.displayValue }}
                </span>
                
                <!-- The mapping indicator: ALWAYS display the database field label in blue -->
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
