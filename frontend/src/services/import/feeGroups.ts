import type { ImportField } from './types';

// Extra fee/tax groups are mapped as indexed db keys (fee_amount__2, tax_amount__2, ...).
// The base group keeps the unsuffixed keys, so single-fee templates and the backend
// contract are untouched; the backend expands each mapped group into one Fee row.
export const GROUP_SEP = '__';

export const FEE_GROUP_KEYS = ['fee_amount', 'fee_currency', 'fee_type'];
export const TAX_GROUP_KEYS = ['tax_amount', 'tax_currency'];

export type FeeGroupKind = 'fee' | 'tax';

const SUFFIX_RE = /^(.*?)__(\d+)$/;

export function baseFieldKey(key: string): string {
  const m = key.match(SUFFIX_RE);
  return m ? m[1] : key;
}

// 1 for base keys, N for `__N` suffixed keys.
export function groupIndex(key: string): number {
  const m = key.match(SUFFIX_RE);
  return m ? Number(m[2]) : 1;
}

export function isExtraGroupKey(key: string): boolean {
  return SUFFIX_RE.test(key);
}

export function groupKindOf(key: string): FeeGroupKind | null {
  const base = baseFieldKey(key);
  if (FEE_GROUP_KEYS.includes(base)) return 'fee';
  if (TAX_GROUP_KEYS.includes(base)) return 'tax';
  return null;
}

// Clone the base metadata field for group n (n >= 2). Extra groups are always
// optional: required_for only applies to the base group.
export function makeGroupField(base: ImportField, n: number): ImportField {
  return {
    ...base,
    key: `${base.key}${GROUP_SEP}${n}`,
    label: `${base.label} (${n})`,
    required_for: undefined,
  };
}

// Generated fields for groups 2..groupCount of the given kind.
export function extraGroupFields(
  importFields: ImportField[],
  kind: FeeGroupKind,
  groupCount: number
): ImportField[] {
  const baseKeys = kind === 'fee' ? FEE_GROUP_KEYS : TAX_GROUP_KEYS;
  const fields: ImportField[] = [];
  for (let n = 2; n <= groupCount; n++) {
    baseKeys.forEach(key => {
      const base = importFields.find(f => f.key === key);
      if (base) fields.push(makeGroupField(base, n));
    });
  }
  return fields;
}

// Highest group index found among mapped db keys of the given kind (1 = base only).
// Used to restore extra groups when a saved template is loaded.
export function highestMappedGroup(mappedDbKeys: string[], kind: FeeGroupKind): number {
  let highest = 1;
  mappedDbKeys.forEach(key => {
    if (groupKindOf(key) === kind) highest = Math.max(highest, groupIndex(key));
  });
  return highest;
}
