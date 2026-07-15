import type { FormulaToken } from './types';

// Client mirror of backend/src/services/import_formula.py — preview only.
// JS floats are acceptable here; the backend Decimal evaluation is authoritative.
// Null semantics must stay identical: blank column -> null; +/- treat null as 0;
// * and / propagate null; division by zero -> null.

const PRECEDENCE: Record<string, number> = { '+': 1, '-': 1, '*': 2, '/': 2 };
const MAX_FORMULA_TOKENS = 64;

export function parseNumericCell(raw: string | undefined | null, decimalSep: string): number | null {
  if (!raw || !raw.trim()) return null;
  let cleaned = raw.trim();
  if (decimalSep === '.') {
    cleaned = cleaned.replace(/,/g, '');
  } else {
    cleaned = cleaned.replace(/\./g, '').replace(/ /g, '').split(decimalSep).join('.');
  }
  const num = Number(cleaned);
  return Number.isFinite(num) ? num : null;
}

function toRpn(tokens: FormulaToken[]): FormulaToken[] | null {
  const output: FormulaToken[] = [];
  const opStack: string[] = [];
  let expectOperand = true;
  for (const token of tokens) {
    if ('col' in token || 'num' in token) {
      if (!expectOperand) return null;
      output.push(token);
      expectOperand = false;
    } else if ('op' in token) {
      if (!(token.op in PRECEDENCE) || expectOperand) return null;
      while (opStack.length && opStack[opStack.length - 1] in PRECEDENCE
        && PRECEDENCE[opStack[opStack.length - 1]] >= PRECEDENCE[token.op]) {
        output.push({ op: opStack.pop() } as FormulaToken);
      }
      opStack.push(token.op);
      expectOperand = true;
    } else if ('paren' in token && token.paren === '(') {
      if (!expectOperand) return null;
      opStack.push('(');
    } else if ('paren' in token && token.paren === ')') {
      if (expectOperand) return null;
      while (opStack.length && opStack[opStack.length - 1] !== '(') {
        output.push({ op: opStack.pop() } as FormulaToken);
      }
      if (!opStack.length) return null;
      opStack.pop();
    } else {
      return null;
    }
  }
  if (expectOperand || opStack.includes('(')) return null;
  while (opStack.length) output.push({ op: opStack.pop() } as FormulaToken);
  return output;
}

function applyOp(op: string, left: number | null, right: number | null): number | null {
  if (op === '+' || op === '-') {
    const a = left ?? 0;
    const b = right ?? 0;
    return op === '+' ? a + b : a - b;
  }
  if (left === null || right === null) return null;
  if (op === '/') return right === 0 ? null : left / right;
  return left * right;
}

export function isValidFormula(tokens: FormulaToken[]): boolean {
  return tokens.length > 0 && tokens.length <= MAX_FORMULA_TOKENS && toRpn(tokens) !== null;
}

export function evaluateFormulaTokens(
  tokens: FormulaToken[],
  row: Record<string, string>,
  decimalSep: string
): number | null {
  if (!Array.isArray(tokens) || !tokens.length || tokens.length > MAX_FORMULA_TOKENS) return null;
  const rpn = toRpn(tokens);
  if (!rpn) return null;

  const stack: Array<number | null> = [];
  for (const token of rpn) {
    if ('col' in token) {
      stack.push(parseNumericCell(row?.[token.col], decimalSep));
    } else if ('num' in token) {
      const num = Number(token.num);
      if (!Number.isFinite(num)) return null;
      stack.push(num);
    } else if ('op' in token) {
      if (stack.length < 2) return null;
      const right = stack.pop()!;
      const left = stack.pop()!;
      stack.push(applyOp(token.op, left, right));
    }
  }
  return stack.length === 1 ? stack[0] : null;
}

export function formulaToDisplayString(tokens: FormulaToken[]): string {
  return tokens.map(t => {
    if ('col' in t) return t.col;
    if ('num' in t) return t.num;
    if ('op' in t) return { '+': '+', '-': '−', '*': '×', '/': '÷' }[t.op];
    return 'paren' in t ? t.paren : '';
  }).join(' ');
}
