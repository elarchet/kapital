export type FormulaToken =
  | { col: string }
  | { num: string }
  | { op: '+' | '-' | '*' | '/' }
  | { paren: '(' | ')' };

export type EnrichMode = 'never' | 'when_empty' | 'always';

export interface ColMapping {
  dbKey: string;
  divisor?: number;
  multiplier?: number;
  enumMappings?: Record<string, string>;
  dateFormat?: string;
  formula?: FormulaToken[];
  enrichAssetNames?: EnrichMode;
  enrichTransactionIds?: EnrichMode;
}

// Per column (by UI column id): mappings keyed by DB op type (or raw action string
// for split types / legacy templates). Each key holds a LIST so one CSV column can
// feed several DB fields. `{ dbKey: '' }` entries are explicit-clear sentinels.
export interface ColumnConfig {
  typeSpecific: Record<string, ColMapping[]>;
}

// Per-op-type settings that don't hang off a column mapping: some brokers have
// no transaction-id column at all, yet still need auto-generated IDs.
export interface OpTypeSettings {
  autoTransactionId?: EnrichMode;
  hashColumns?: string[];
}

export interface ImportField {
  key: string;
  label: string;
  is_required: boolean;
  type: 'string' | 'numeric' | 'datetime' | 'enum';
  enum_values?: string[];
  op_types?: string[];
  required_for?: string[];
}

export interface RowError {
  rowNum: number;
  rawRow: string[];
  fieldKey: string;
  fieldLabel: string;
  rawValue: string;
  errorMessage: string;
}
