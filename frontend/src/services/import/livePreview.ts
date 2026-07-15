import type { ColMapping, EnrichMode, ImportField } from './types';
import { evaluateFormulaTokens, formulaToDisplayString, parseNumericCell } from './formula';
import { parseDateTimeWithFormat } from './validation';

export interface LivePreviewResult {
  success: boolean;
  value?: string;
  error?: string;
}

export interface LivePreviewContext {
  decimalSeparator: string;
  // Example row keyed by CSV header name — needed for formula evaluation.
  rowByHeader?: Record<string, string>;
  isRequired?: boolean;
  // Asset-name enrichment display inputs
  enrichMode?: EnrichMode;
  tickerMapped?: boolean;
  exampleTicker?: string;
  enrichedName?: string;
  isEnriching?: boolean;
  // Transaction-id auto-generation display input
  autoIdMode?: EnrichMode;
}

function previewName(rawVal: string | undefined, ctx: LivePreviewContext): LivePreviewResult {
  const shouldEnrich =
    ctx.enrichMode === 'always' || (ctx.enrichMode === 'when_empty' && !rawVal);

  if (shouldEnrich && ctx.tickerMapped && ctx.exampleTicker) {
    if (ctx.isEnriching || ctx.enrichedName === 'loading...') {
      return { success: true, value: 'Resolving asset name...' };
    }
    if (ctx.enrichedName) {
      if (ctx.enrichedName.endsWith('(Not Found)')) {
        return { success: false, error: `Failed to resolve asset name for ticker "${ctx.exampleTicker}".` };
      }
      return { success: true, value: `${rawVal || '—'} → ${ctx.enrichedName} (Auto-Enriched)` };
    }
  }
  return { success: true, value: rawVal || ctx.exampleTicker || 'Asset' };
}

function previewTransactionId(rawVal: string | undefined, ctx: LivePreviewContext): LivePreviewResult {
  const shouldGenerate =
    ctx.autoIdMode === 'always' || (ctx.autoIdMode === 'when_empty' && !rawVal);

  if (shouldGenerate) {
    // Mock hash for display only — the backend computes the real sha256.
    const mockHash = Math.random().toString(16).slice(2, 10).padStart(8, '0');
    return { success: true, value: `${rawVal || '—'} → auto-${mockHash} (Auto-Generated)` };
  }
  return { success: true, value: rawVal || '—' };
}

function previewNumeric(
  rawVal: string | undefined,
  mapping: Partial<ColMapping>,
  ctx: LivePreviewContext
): LivePreviewResult {
  let num: number | null;
  if (mapping.formula?.length) {
    num = evaluateFormulaTokens(mapping.formula, ctx.rowByHeader || {}, ctx.decimalSeparator);
    if (num === null) {
      return { success: false, error: `Formula "${formulaToDisplayString(mapping.formula)}" cannot be evaluated on this row.` };
    }
  } else {
    num = parseNumericCell(rawVal, ctx.decimalSeparator);
    if (num === null) {
      return { success: false, error: `"${rawVal}" cannot be parsed as a valid numeric decimal.` };
    }
  }

  if (mapping.divisor) num /= mapping.divisor;
  if (mapping.multiplier) num *= mapping.multiplier;
  return { success: true, value: num.toString() };
}

// Pure preview of how one example value converts under a mapping. Shared by the
// field slots and the config modal; mirrors backend parsing (preview only).
export function computeLivePreview(
  field: ImportField | undefined,
  rawValue: string | undefined,
  mapping: Partial<ColMapping>,
  ctx: LivePreviewContext
): LivePreviewResult {
  if (!mapping.dbKey) {
    return { success: true, value: 'Unmapped (Column ignored)' };
  }

  if (mapping.dbKey === 'name') return previewName(rawValue, ctx);
  if (mapping.dbKey === 'transaction_id') return previewTransactionId(rawValue, ctx);

  const hasFormula = field?.type === 'numeric' && !!mapping.formula?.length;
  if (!hasFormula && (rawValue === undefined || rawValue === null || rawValue.trim() === '')) {
    if (ctx.isRequired ?? field?.is_required) {
      return { success: false, error: 'Example cell is empty but this database field is required.' };
    }
    return { success: true, value: 'Empty value (Ignored)' };
  }

  if (field?.type === 'numeric') return previewNumeric(rawValue, mapping, ctx);

  if (field?.type === 'datetime') {
    const parsedDate = parseDateTimeWithFormat(rawValue!.trim(), mapping.dateFormat || 'auto');
    if (!parsedDate) {
      return { success: false, error: `"${rawValue}" cannot be parsed as a valid timestamp with format "${mapping.dateFormat || 'auto'}".` };
    }
    return { success: true, value: parsedDate.toISOString() };
  }

  if (field?.type === 'enum') {
    const mapped = mapping.enumMappings?.[rawValue!];
    if (!mapped) {
      return { success: false, error: `Value "${rawValue}" must be mapped to a DB enum option.` };
    }
    return { success: true, value: mapped };
  }

  return { success: true, value: rawValue };
}
