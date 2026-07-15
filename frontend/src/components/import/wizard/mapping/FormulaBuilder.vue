<script setup lang="ts">
import { computed, ref } from 'vue';
import { X } from '@lucide/vue';
import DynamicComponent from '../../../DynamicComponent.vue';
import type { FormulaToken } from '../../../../services/import/types';
import { evaluateFormulaTokens, isValidFormula } from '../../../../services/import';

const props = defineProps<{
  headers: string[];
  exampleRowByHeader: Record<string, string>;
  decimalSeparator: string;
}>();

const formula = defineModel<FormulaToken[]>('formula', { required: true });

const numberInput = ref('');
// Auto-inserted between two consecutive operands: picking 4 fee columns in a row
// builds "a + b + c + d" without touching the operator buttons.
const lastOperator = ref<'+' | '-' | '*' | '/'>('+');

const OPERATORS: Array<{ op: '+' | '-' | '*' | '/'; label: string }> = [
  { op: '+', label: '+' },
  { op: '-', label: '−' },
  { op: '*', label: '×' },
  { op: '/', label: '÷' },
];

const columnOptions = computed(() => props.headers.map(h => ({ value: h, label: h })));

const endsWithOperand = computed(() => {
  const last = formula.value[formula.value.length - 1];
  return !!last && ('col' in last || 'num' in last || ('paren' in last && last.paren === ')'));
});

const pushOperand = (token: FormulaToken) => {
  const tokens = [...formula.value];
  if (endsWithOperand.value) tokens.push({ op: lastOperator.value });
  tokens.push(token);
  formula.value = tokens;
};

const addColumn = (header: string) => {
  if (header) pushOperand({ col: header });
};

const addNumber = () => {
  const val = numberInput.value.trim();
  if (!val || !Number.isFinite(Number(val))) return;
  pushOperand({ num: val });
  numberInput.value = '';
};

const addOperator = (op: '+' | '-' | '*' | '/') => {
  lastOperator.value = op;
  if (endsWithOperand.value) formula.value = [...formula.value, { op }];
};

const addParen = (paren: '(' | ')') => {
  formula.value = [...formula.value, { paren }];
};

const removeToken = (idx: number) => {
  formula.value = formula.value.filter((_, i) => i !== idx);
};

const tokenLabel = (token: FormulaToken): string => {
  if ('col' in token) return token.col;
  if ('num' in token) return token.num;
  if ('op' in token) return { '+': '+', '-': '−', '*': '×', '/': '÷' }[token.op];
  return 'paren' in token ? token.paren : '';
};

const isValid = computed(() => isValidFormula(formula.value));
const liveResult = computed(() =>
  isValid.value ? evaluateFormulaTokens(formula.value, props.exampleRowByHeader, props.decimalSeparator) : null
);
</script>

<template>
  <div class="flex flex-col gap-2">
    <!-- Expression chips -->
    <div class="flex flex-wrap items-center gap-1 min-h-[38px] border border-border-color rounded-sm p-1.5 bg-bg-secondary">
      <span
        v-for="(token, idx) in formula"
        :key="idx"
        class="group flex items-center gap-1 py-0.5 px-1.5 rounded-sm text-[0.75rem] font-mono border"
        :class="'col' in token
          ? 'bg-accent-light border-accent/40 text-accent'
          : 'op' in token
            ? 'bg-bg-tertiary border-border-color font-bold'
            : 'bg-bg-primary border-border-color'"
      >
        {{ tokenLabel(token) }}
        <button type="button" class="opacity-40 group-hover:opacity-100 hover:text-danger-color" @click="removeToken(idx)">
          <X class="w-3 h-3" />
        </button>
      </span>
      <span v-if="!formula.length" class="text-[0.72rem] text-text-tertiary px-1">
        Build a formula: add columns, numbers and operators…
      </span>
    </div>

    <!-- Token inputs -->
    <div class="flex flex-wrap items-center gap-2">
      <div class="min-w-[160px]">
        <DynamicComponent
          componentKey="custom-dropdown"
          modelValue=""
          :options="columnOptions"
          :searchable="true"
          placeholder="+ Column…"
          :compact="true"
          @update:modelValue="addColumn"
        />
      </div>
      <div class="flex items-center gap-1">
        <input
          v-model="numberInput"
          type="number"
          step="any"
          class="form-control !w-24 !py-1 !text-[0.75rem]"
          placeholder="Number"
          @keydown.enter.prevent="addNumber"
        />
        <button type="button" class="btn btn-sm" @click="addNumber">Add</button>
      </div>
      <div class="flex items-center gap-1">
        <button
          v-for="o in OPERATORS"
          :key="o.op"
          type="button"
          class="btn btn-sm !px-2.5 font-bold"
          :class="lastOperator === o.op ? '!border-accent text-accent' : ''"
          @click="addOperator(o.op)"
        >{{ o.label }}</button>
        <button type="button" class="btn btn-sm !px-2.5 font-bold" @click="addParen('(')">(</button>
        <button type="button" class="btn btn-sm !px-2.5 font-bold" @click="addParen(')')">)</button>
      </div>
    </div>

    <!-- Live result -->
    <div v-if="formula.length" class="text-[0.72rem]" :class="isValid ? 'text-text-secondary' : 'text-danger-color'">
      <template v-if="!isValid">Incomplete or invalid expression — finish it before saving.</template>
      <template v-else-if="liveResult !== null">
        ✓ On the current example row: <span class="font-mono font-semibold text-text-primary">{{ liveResult }}</span>
      </template>
      <template v-else>Formula is valid but cannot be computed on the current example row (blank operand in × or ÷).</template>
    </div>
  </div>
</template>
