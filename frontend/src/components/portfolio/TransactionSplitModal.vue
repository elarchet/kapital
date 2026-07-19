<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue';
import { Loader, Merge, Plus, Scissors, Trash2, X } from '@lucide/vue';
import { useValuationStore } from '../../store/valuation';
import { useNotifications } from '../../composables/useNotifications';
import type { Portfolio } from '../../store';
import type { Allocation, AllocationLineInput, RawTransaction } from '../../services/portfolioApi';

const props = defineProps<{
  transaction: RawTransaction;
  allocations: Allocation[];
  portfolios: Portfolio[];
  portfolioId: number | 'unassigned';
  positionId: number;
  positionIds: number[];
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'saved'): void;
}>();

const valuationStore = useValuationStore();
const { notifySuccess, notifyError } = useNotifications();

type Method = 'percentage' | 'quantity' | 'amount';

// Distinct, theme-neutral segment colors (readable on light and dark).
const SEGMENT_COLORS = ['#6366f1', '#14b8a6', '#f59e0b', '#ec4899', '#06b6d4', '#8b5cf6', '#84cc16', '#ef4444'];
const MIN_FRACTION = 1e-6;

interface Line {
  // 'pos:<id>' = an existing constituent position; 'pf:<id>' = a portfolio
  // (the backend finds or creates the matching position there).
  target: string;
  fraction: number;
}

const parentQty = computed(() => Math.abs(Number(props.transaction.quantity ?? 0)));
const parentAmt = computed(() => Math.abs(Number(props.transaction.total_amount ?? 0)));
const hasQty = computed(() => parentQty.value > 0);

// The position the transaction currently routes to — recombine collapses here,
// and a fresh split defaults its single line to it (preserving routing).
const primaryPositionId = computed(() => {
  const preferred = props.allocations.find(a => a.is_default) ?? props.allocations[0];
  return preferred?.position_id ?? props.positionId;
});

// Fraction of the parent an existing allocation represents.
const allocationFraction = (a: Allocation): number => {
  if (hasQty.value) return Math.abs(Number(a.quantity)) / parentQty.value;
  if (parentAmt.value) return Math.abs(Number(a.amount)) / parentAmt.value;
  return 0;
};

const buildInitialLines = (): Line[] => {
  if (!props.allocations.length) {
    return [{ target: `pos:${primaryPositionId.value}`, fraction: 1 }];
  }
  const raw = props.allocations.map(a => ({ target: `pos:${a.position_id}`, fraction: allocationFraction(a) }));
  // Renormalize so the set sums to exactly 1 (the last line absorbs drift).
  const head = raw.slice(0, -1);
  const usedByHead = head.reduce((s, l) => s + l.fraction, 0);
  raw[raw.length - 1].fraction = Math.max(1 - usedByHead, 0);
  return raw;
};

const method = ref<Method>(hasQty.value ? 'quantity' : 'amount');
const lines = ref<Line[]>(buildInitialLines());
const saving = ref(false);
const confirmingRecombine = ref(false);

const lastIndex = computed(() => lines.value.length - 1);
const isLast = (i: number) => i === lastIndex.value;

// Cumulative left edge (0..1) of each segment, for rendering + drag math.
const starts = computed(() => {
  const acc: number[] = [];
  let sum = 0;
  for (const l of lines.value) {
    acc.push(sum);
    sum += l.fraction;
  }
  return acc;
});

const formatCurrency = (val: number) =>
  new Intl.NumberFormat('fr-FR', { style: 'currency', currency: props.transaction.currency || 'EUR' }).format(val);

const METHOD_UNITS: { key: Method; label: string }[] = [
  { key: 'quantity', label: 'Shares' },
  { key: 'percentage', label: '%' },
  { key: 'amount', label: 'Amount' },
];
const availableMethods = computed(() => METHOD_UNITS.filter(m => m.key !== 'quantity' || hasQty.value));

// Resolve a fraction into the currently-selected unit, for inputs and labels.
const toUnit = (fraction: number): number => {
  if (method.value === 'percentage') return fraction * 100;
  if (method.value === 'quantity') return fraction * parentQty.value;
  return fraction * parentAmt.value;
};

const displayUnit = (fraction: number): string => {
  if (method.value === 'percentage') return `${(fraction * 100).toFixed(1)}%`;
  if (method.value === 'quantity') return toUnit(fraction).toLocaleString('fr-FR', { maximumFractionDigits: 4 });
  return formatCurrency(toUnit(fraction));
};

const fromUnit = (value: number): number => {
  if (method.value === 'percentage') return value / 100;
  if (method.value === 'quantity') return parentQty.value ? value / parentQty.value : 0;
  return parentAmt.value ? value / parentAmt.value : 0;
};

const colorFor = (i: number) => SEGMENT_COLORS[i % SEGMENT_COLORS.length];

// The last line always absorbs the remainder so the set sums to exactly 1.
const rebalanceLast = () => {
  const usedByHead = lines.value.slice(0, -1).reduce((s, l) => s + l.fraction, 0);
  lines.value[lastIndex.value].fraction = Math.max(1 - usedByHead, 0);
};

const setLineUnit = (i: number, raw: string) => {
  if (isLast(i)) return; // last is auto-balanced
  const parsed = Number(raw);
  if (Number.isNaN(parsed)) return;
  const others = lines.value.reduce((s, l, idx) => (idx === i || isLast(idx) ? s : s + l.fraction), 0);
  const maxForI = Math.max(1 - others, 0); // leave the last line >= 0
  lines.value[i].fraction = Math.min(Math.max(fromUnit(parsed), 0), maxForI);
  rebalanceLast();
};

const addLine = () => {
  const last = lines.value[lastIndex.value];
  const half = last.fraction / 2;
  last.fraction = half;
  lines.value.push({ target: `pf:${props.portfolios[0]?.id ?? ''}`, fraction: half });
};

const removeLine = (i: number) => {
  if (lines.value.length === 1) return;
  lines.value.splice(i, 1);
  rebalanceLast();
};

// ---- Draggable dividers -----------------------------------------------------

const barRef = ref<HTMLElement | null>(null);
const dragIndex = ref<number | null>(null);

const onDragMove = (event: PointerEvent) => {
  const divider = dragIndex.value;
  if (divider === null || !barRef.value) return;
  const rect = barRef.value.getBoundingClientRect();
  const boundary = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
  // The divider sits between segment `divider` and `divider + 1`; moving it
  // trades proportion between those two neighbours, so the total stays 1.
  const leftEdge = starts.value[divider];
  const rightEdge = starts.value[divider + 1] + lines.value[divider + 1].fraction;
  const clamped = Math.min(Math.max(boundary, leftEdge), rightEdge);
  lines.value[divider].fraction = clamped - leftEdge;
  lines.value[divider + 1].fraction = rightEdge - clamped;
};

const endDrag = () => {
  dragIndex.value = null;
  window.removeEventListener('pointermove', onDragMove);
  window.removeEventListener('pointerup', endDrag);
};

const startDrag = (divider: number, event: PointerEvent) => {
  event.preventDefault();
  dragIndex.value = divider;
  window.addEventListener('pointermove', onDragMove);
  window.addEventListener('pointerup', endDrag);
};

onBeforeUnmount(endDrag);

// ---- Save / recombine -------------------------------------------------------

const existingPositionTargets = computed(() => {
  const ids = new Set<string>();
  props.allocations.forEach(a => ids.add(String(a.position_id)));
  ids.add(String(primaryPositionId.value));
  return [...ids];
});

const canSave = computed(
  () =>
    !saving.value &&
    lines.value.length > 0 &&
    lines.value.every(l => l.target && !l.target.endsWith(':') && l.fraction >= MIN_FRACTION)
);

const toApiLines = (): AllocationLineInput[] => {
  const head = lines.value.slice(0, -1);
  const headPcts = head.map(l => Number((l.fraction * 100).toFixed(8)));
  const lastPct = Number((100 - headPcts.reduce((s, p) => s + p, 0)).toFixed(8));
  return lines.value.map((line, i) => {
    const value = String(isLast(i) ? lastPct : headPcts[i]);
    const base = { method: 'percentage' as const, value };
    return line.target.startsWith('pf:')
      ? { ...base, portfolio_id: Number(line.target.slice(3)) }
      : { ...base, position_id: Number(line.target.slice(4)) };
  });
};

const save = async () => {
  if (!canSave.value) return;
  saving.value = true;
  try {
    await valuationStore.applySplit(props.transaction.id, toApiLines(), {
      portfolioId: props.portfolioId,
      positionIds: props.positionIds,
    });
    notifySuccess('Transaction split saved', {
      message: `Spread over ${lines.value.length} allocation line${lines.value.length === 1 ? '' : 's'}.`,
    });
    emit('saved');
    emit('close');
  } catch (err: any) {
    notifyError('Split rejected', { message: err.message || 'The server refused this split.' });
  } finally {
    saving.value = false;
  }
};

const canRecombine = computed(
  () => props.allocations.length > 1 || props.allocations.some(a => !a.is_default)
);

const doRecombine = async () => {
  if (!confirmingRecombine.value) {
    confirmingRecombine.value = true;
    return;
  }
  saving.value = true;
  try {
    await valuationStore.recombine(props.transaction.id, primaryPositionId.value, {
      portfolioId: props.portfolioId,
      positionIds: props.positionIds,
    });
    notifySuccess('Transaction recombined', {
      message: 'Restored to a single 100% allocation on its current position.',
    });
    emit('saved');
    emit('close');
  } catch (err: any) {
    notifyError('Recombine failed', { message: err.message || 'The server refused the recombine.' });
  } finally {
    saving.value = false;
    confirmingRecombine.value = false;
  }
};
</script>

<template>
  <div class="modal-overlay z-[130]" @click.self="emit('close')">
    <div class="modal-card max-w-2xl w-full max-h-[90vh]">
      <!-- Header -->
      <div class="modal-header">
        <div class="flex items-center gap-2">
          <Scissors class="w-4 h-4 text-accent" />
          <h3 class="text-base font-bold text-text-primary">Split Transaction</h3>
        </div>
        <button class="btn-logout p-1" title="Close" @click="emit('close')">
          <X class="w-4 h-4 text-text-tertiary" />
        </button>
      </div>

      <!-- Body (scrolls) -->
      <div class="modal-body overflow-y-auto flex flex-col gap-5">
        <!-- Parent transaction summary -->
        <div class="bg-bg-tertiary border border-border-color rounded-md px-4 py-3 flex flex-wrap gap-x-6 gap-y-1 text-xs">
          <span class="text-text-secondary">
            Asset <strong class="text-text-primary">{{ transaction.name || transaction.ticker || '—' }}</strong>
          </span>
          <span v-if="hasQty" class="text-text-secondary">
            Quantity <strong class="font-mono text-text-primary">{{ parentQty }}</strong>
          </span>
          <span class="text-text-secondary">
            Amount <strong class="font-mono text-text-primary">{{ formatCurrency(parentAmt) }}</strong>
          </span>
          <span class="text-text-secondary">
            Date <strong class="font-mono text-text-primary">{{ new Date(transaction.executed_at).toLocaleDateString('fr-FR') }}</strong>
          </span>
        </div>

        <!-- Draggable proportion bar -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-[11px] font-bold uppercase tracking-wider text-text-tertiary">Proportions</span>
            <div class="flex items-center gap-0 rounded-md border border-border-color overflow-hidden" role="radiogroup" aria-label="Display unit">
              <button
                v-for="m in availableMethods"
                :key="m.key"
                type="button"
                role="radio"
                :aria-checked="method === m.key"
                class="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide cursor-pointer transition-colors"
                :class="method === m.key ? 'bg-accent-light text-accent' : 'bg-bg-tertiary text-text-tertiary hover:text-text-secondary'"
                @click="method = m.key"
              >
                {{ m.label }}
              </button>
            </div>
          </div>

          <div
            ref="barRef"
            class="relative flex h-11 rounded-md overflow-hidden border border-border-color select-none"
          >
            <template v-for="(line, i) in lines" :key="i">
              <div
                class="relative h-full flex items-center justify-center overflow-hidden transition-[width] duration-75"
                :style="{ width: line.fraction * 100 + '%', backgroundColor: colorFor(i) }"
              >
                <span
                  v-if="line.fraction > 0.07"
                  class="text-[10px] font-bold text-white/95 px-1 truncate pointer-events-none"
                >
                  {{ displayUnit(line.fraction) }}
                </span>
              </div>
              <!-- Divider handle between this segment and the next -->
              <div
                v-if="i < lastIndex"
                class="absolute top-0 bottom-0 w-3 -ml-1.5 cursor-ew-resize flex items-center justify-center group z-10"
                :style="{ left: (starts[i] + line.fraction) * 100 + '%' }"
                role="separator"
                :aria-label="'Adjust split between segment ' + (i + 1) + ' and ' + (i + 2)"
                @pointerdown="startDrag(i, $event)"
              >
                <div class="w-1 h-6 rounded-full bg-white shadow ring-1 ring-black/10 group-hover:h-8 transition-all"></div>
              </div>
            </template>
          </div>
          <p class="text-[10px] text-text-tertiary mt-1.5">
            Drag the handles to rebalance. The last line balances automatically so the split always covers 100%.
          </p>
        </div>

        <!-- Per-line targets -->
        <div class="flex flex-col gap-2">
          <div
            v-for="(line, i) in lines"
            :key="i"
            class="flex items-center gap-2 flex-wrap bg-bg-secondary border border-border-color rounded-md px-3 py-2"
          >
            <span class="w-3 h-3 rounded-sm shrink-0" :style="{ backgroundColor: colorFor(i) }" aria-hidden="true"></span>

            <select
              v-model="line.target"
              class="form-control !w-auto flex-1 min-w-[160px] !py-1.5 text-xs"
              :aria-label="'Target of line ' + (i + 1)"
            >
              <optgroup label="Existing positions">
                <option v-for="id in existingPositionTargets" :key="'pos' + id" :value="'pos:' + id">
                  {{ String(id) === String(primaryPositionId) ? 'Current position' : 'Position #' + id }}
                </option>
              </optgroup>
              <optgroup label="Portfolios (find or create)">
                <option v-for="p in portfolios" :key="'pf' + p.id" :value="'pf:' + p.id">
                  {{ p.emoji ? p.emoji + ' ' : '' }}{{ p.name }}
                </option>
              </optgroup>
            </select>

            <div class="flex items-center gap-1.5 shrink-0">
              <input
                v-if="!isLast(i)"
                :value="Number(toUnit(line.fraction).toFixed(method === 'amount' ? 2 : 4))"
                type="number"
                min="0"
                step="any"
                class="form-control !w-24 !py-1.5 text-right font-mono text-xs"
                :aria-label="'Value of line ' + (i + 1)"
                @input="setLineUnit(i, ($event.target as HTMLInputElement).value)"
              />
              <span
                v-else
                class="w-24 text-right font-mono text-xs text-text-secondary bg-bg-tertiary border border-border-color rounded px-2 py-1.5"
                title="Automatically balanced to complete 100%"
              >
                {{ displayUnit(line.fraction) }}
              </span>
              <span class="text-[10px] text-text-tertiary w-10">{{ (line.fraction * 100).toFixed(0) }}%</span>
            </div>

            <button
              class="btn-logout p-1 shrink-0"
              title="Remove this line"
              :disabled="lines.length === 1"
              @click="removeLine(i)"
            >
              <Trash2 class="w-3.5 h-3.5 text-text-tertiary" />
            </button>
          </div>

          <button
            class="btn btn-sm bg-bg-tertiary border border-border-color text-text-secondary self-start flex items-center gap-1"
            @click="addLine"
          >
            <Plus class="w-3.5 h-3.5" />
            <span>Add target</span>
          </button>
        </div>
      </div>

      <!-- Footer -->
      <div class="modal-footer justify-between">
        <button
          v-if="canRecombine"
          class="btn btn-sm flex items-center gap-1.5"
          :class="confirmingRecombine ? 'btn-danger-solid' : 'bg-bg-secondary border border-border-color text-text-secondary'"
          :disabled="saving"
          @click="doRecombine"
        >
          <Merge class="w-3.5 h-3.5" />
          <span>{{ confirmingRecombine ? 'Confirm recombine' : 'Recombine' }}</span>
        </button>
        <span v-else></span>

        <div class="flex items-center gap-2">
          <button class="btn btn-sm bg-bg-secondary border border-border-color text-text-secondary" :disabled="saving" @click="emit('close')">
            Cancel
          </button>
          <button class="btn btn-sm btn-primary flex items-center gap-1.5" :disabled="!canSave" @click="save">
            <Loader v-if="saving" class="w-3.5 h-3.5 animate-spin" />
            <span>Save split</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
