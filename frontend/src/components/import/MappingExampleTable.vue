<script setup lang="ts">


const props = defineProps<{
  importFileHeaders: string[];
  operationTypeColumnIdx: number | null;
  columnConfigMap: Record<number, {
    global: { dbKey: string; divisor?: number; multiplier?: number; enumMappings?: Record<string, string> };
    typeSpecific: Record<string, { dbKey: string; divisor?: number; multiplier?: number; enumMappings?: Record<string, string> }>;
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
  (e: 'open-wizard', payload: { colIdx: number; opType: string | null }): void;
  (e: 'prev-example', opType: string): void;
  (e: 'next-example', opType: string): void;
}>();

const getColumnMappingLabel = (colIdx: number) => {
  if (colIdx === props.operationTypeColumnIdx) {
    return 'Action / Type';
  }

  const conf = props.columnConfigMap[colIdx];
  if (!conf) return '-- Unmapped --';

  const resolvedKeys = new Set<string>();
  props.activeDbOpTypes.forEach(opType => {
    const key = conf.typeSpecific[opType]?.dbKey || conf.global.dbKey || '';
    resolvedKeys.add(key);
  });

  if (resolvedKeys.size > 1) {
    return '(Type-Specific)';
  }

  const singleKey = Array.from(resolvedKeys)[0];
  if (!singleKey) {
    return '-- Unmapped --';
  }

  const field = props.importFields.find(f => f.key === singleKey);
  return field ? field.label : '-- Unmapped --';
};

const getResolvedKeyForCell = (colIdx: number, opType: string) => {
  const conf = props.columnConfigMap[colIdx];
  if (!conf) return '';
  return conf.typeSpecific[opType]?.dbKey || conf.global.dbKey || '';
};

const openWizard = (colIdx: number, opType: string | null) => {
  emit('open-wizard', { colIdx, opType });
};

const prevExampleForType = (opType: string) => {
  emit('prev-example', opType);
};

const nextExampleForType = (opType: string) => {
  emit('next-example', opType);
};
</script>

<template>
  <div style="overflow-x: auto; max-width: 100%; border: 1px solid var(--border-color); border-radius: var(--radius-sm); margin-bottom: 1.5rem;">
    <table class="preview-table" style="margin-top: 0; min-width: 100%;">
      <thead>
        <tr>
          <th style="min-width: 180px; background-color: var(--bg-tertiary); font-weight: 700; color: var(--text-secondary); text-align: center;">
            Context & Stats
          </th>
          <th v-for="(h, idx) in importFileHeaders" :key="idx" style="min-width: 180px; padding: 0.75rem; vertical-align: top;">
            <div style="font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" :title="h">
              {{ h }}
            </div>
          </th>
        </tr>
      </thead>
      <tbody>
        <!-- Global Mapping row -->
        <tr style="background-color: var(--accent-light);">
          <td style="font-weight: 700; color: var(--accent-color); font-size: 0.75rem; text-align: center; vertical-align: middle;">
            Global Mapping
          </td>
          <td 
            v-for="(_, idx) in importFileHeaders" 
            :key="idx" 
            @click="idx !== operationTypeColumnIdx ? openWizard(idx, null) : null" 
            :style="{ cursor: idx !== operationTypeColumnIdx ? 'pointer' : 'default' }" 
            style="font-size: 0.75rem; font-weight: 600; text-align: center; vertical-align: middle;"
          >
            <div v-if="getColumnMappingLabel(idx) === '(Type-Specific)'" style="color: var(--text-secondary); font-style: italic; font-size: 0.7rem; font-weight: bold;">
              (Type-Specific)
            </div>
            <div v-else-if="getColumnMappingLabel(idx) !== '-- Unmapped --'" style="display: inline-flex; align-items: center; gap: 0.25rem; background-color: var(--accent-color); color: white; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.75rem;">
              {{ getColumnMappingLabel(idx) }}
              <span v-if="columnConfigMap[idx]?.global?.divisor" style="font-size: 0.6rem; opacity: 0.9;">(/{{ columnConfigMap[idx].global.divisor }})</span>
              <span v-if="columnConfigMap[idx]?.global?.multiplier" style="font-size: 0.6rem; opacity: 0.9;">(*{{ columnConfigMap[idx].global.multiplier }})</span>
            </div>
            <span v-else style="color: var(--text-tertiary); font-weight: normal;">-- Unmapped --</span>
          </td>
        </tr>

        <!-- Example rows per type -->
        <tr v-for="example in exampleTransactions" :key="example.opType">
          <td style="vertical-align: middle; text-align: left; padding: 0.35rem 0.5rem;">
            <div style="display: flex; flex-direction: column; align-items: flex-start; gap: 0.15rem; padding: 0.15rem;">
              <div style="display: flex; align-items: center; gap: 0.35rem; width: 100%;">
                <span class="badge" :class="'badge-' + example.opType" style="padding: 0.15rem 0.35rem; font-size: 0.65rem; text-transform: uppercase; min-width: 110px; text-align: center; display: inline-block;">
                  {{ example.opType }}
                </span>
                
                <!-- Compact Switcher Controls -->
                <div v-if="example.totalMatches > 1" style="display: flex; align-items: center; gap: 0.15rem;">
                  <button @click.stop="prevExampleForType(example.opType)" style="background: none; border: none; padding: 0 2px; font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center;" title="Previous Example">&larr;</button>
                  <button @click.stop="nextExampleForType(example.opType)" style="background: none; border: none; padding: 0 2px; font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center;" title="Next Example">&rarr;</button>
                </div>
              </div>

              <span v-if="liveValidationStats[example.opType]" :style="{
                fontSize: '0.65rem',
                fontWeight: 600,
                color: liveValidationStats[example.opType].failed > 0 ? 'var(--color-danger)' : 'var(--color-success)'
              }" style="margin-top: 0.1rem; padding-left: 0.25rem;">
                {{ liveValidationStats[example.opType].success }} / {{ liveValidationStats[example.opType].total }} parsed
              </span>
            </div>
          </td>
          <td 
            v-for="(cell, idx) in example.csvRow" 
            :key="idx" 
            @click="idx !== operationTypeColumnIdx ? openWizard(idx, example.opType) : null" 
            :style="{ cursor: idx !== operationTypeColumnIdx ? 'pointer' : 'default' }" 
            style="vertical-align: middle;"
          >
            <div style="display: flex; flex-direction: column; gap: 0.25rem;">
              <span style="font-family: monospace; font-size: 0.75rem; color: var(--text-secondary);">
                {{ cell || '—' }}
              </span>
              <div v-if="getColumnMappingLabel(idx) === '(Type-Specific)' && getResolvedKeyForCell(idx, example.opType)" style="font-size: 0.65rem; color: var(--accent-color); font-weight: 600;">
                → {{ importFields.find(f => f.key === getResolvedKeyForCell(idx, example.opType))?.label }}
              </div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
  margin-top: 0.5rem;
  border: 1px solid var(--border-color);
}
.preview-table th, .preview-table td {
  border: 1px solid var(--border-color);
  padding: 0.35rem 0.5rem;
  text-align: left;
}
.preview-table th {
  background-color: var(--bg-tertiary);
  font-weight: 600;
  color: var(--text-secondary);
}

/* polymorphic action badges */
.badge-buy { background-color: rgba(37, 99, 235, 0.15); color: #3b82f6; }
.badge-sell { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }
.badge-dividend { background-color: rgba(16, 185, 129, 0.15); color: #10b981; }
.badge-interest { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.badge-expense { background-color: rgba(236, 72, 153, 0.15); color: #ec4899; }
.badge-revenue { background-color: rgba(139, 92, 246, 0.15); color: #8b5cf6; }
.badge-fx_rate_change { background-color: rgba(6, 182, 212, 0.15); color: #06b6d4; }
.badge-transfer_in { background-color: rgba(16, 185, 129, 0.15); color: #10b981; }
.badge-transfer_out { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }
.badge-stock_split { background-color: rgba(139, 92, 246, 0.15); color: #8b5cf6; }
.badge-fee { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.badge-tax { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }
.badge-limit_buy { background-color: rgba(37, 99, 235, 0.15); color: #3b82f6; }
.badge-limit_sell { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }
.badge-unknown { background-color: var(--bg-tertiary); color: var(--text-secondary); }

/* Sticky first column in Step 2 preview table */
.preview-table th:first-child,
.preview-table td:first-child {
  position: sticky;
  left: 0;
  z-index: 5;
  background-color: var(--bg-secondary);
  border-right: 2px solid var(--border-color);
  box-shadow: 2px 0 5px rgba(0, 0, 0, 0.05);
}
.preview-table th:first-child {
  z-index: 6;
  background-color: var(--bg-tertiary);
}
</style>
