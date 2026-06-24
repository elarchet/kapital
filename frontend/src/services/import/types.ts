export interface ColMapping {
  dbKey: string;
  divisor?: number;
  multiplier?: number;
  enumMappings?: Record<string, string>;
  dateFormat?: string;
  enrichAssetNames?: 'never' | 'when_empty' | 'always';
  enrichTransactionIds?: 'never' | 'when_empty' | 'always';
}

export interface RowError {
  rowNum: number;
  rawRow: string[];
  fieldKey: string;
  fieldLabel: string;
  rawValue: string;
  errorMessage: string;
}
