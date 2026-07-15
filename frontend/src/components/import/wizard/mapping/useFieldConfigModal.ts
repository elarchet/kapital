import { computed, ref, watch, type Ref } from 'vue';
import { api } from '../../../../services/api';
import type { ColMapping, EnrichMode, FormulaToken, ImportField, OpTypeSettings } from '../../../../services/import/types';
import { computeLivePreview, isValidFormula } from '../../../../services/import';

export interface FieldConfigContext {
  field: ImportField;
  opType: string;
  mappedHeader: string | null;
  initialMapping: ColMapping | null;
  uniqueCsvValues: string[];
  exampleValue: string;
  exampleRowByHeader: Record<string, string>;
  tickerMapped: boolean;
  exampleTicker: string;
  opTypeSettings: OpTypeSettings | null;
  decimalSeparator: string;
}

// Form logic for the field configuration modal. The target dbKey is fixed by the
// slot that opened the modal (no destination-field selection anymore).
export function useFieldConfigModal(show: Ref<boolean>, ctx: Ref<FieldConfigContext | null>) {
  const sourceMode = ref<'simple' | 'formula'>('simple');
  const formula = ref<FormulaToken[]>([]);
  const transformationType = ref<'none' | 'divisor' | 'multiplier'>('none');
  const transformationValue = ref<number | null>(null);
  const enumMappings = ref<Record<string, string>>({});
  const dateFormat = ref('auto');
  // 'when_empty' matches the backend's enrichment default and the template
  // parser (config.ts), so the modal previews what an import would really do.
  const enrichAssetNames = ref<EnrichMode>('when_empty');
  const autoTransactionId = ref<EnrichMode>('when_empty');
  const hashColumns = ref<string[]>([]);
  const tickerColumnPick = ref('');

  // Serialized form state, captured when the modal opens, to detect unsaved edits.
  const initialSnapshot = ref('');
  const stateSnapshot = () => JSON.stringify({
    mode: sourceMode.value,
    formula: formula.value,
    transformationType: transformationType.value,
    transformationValue: transformationValue.value,
    enums: enumMappings.value,
    dateFormat: dateFormat.value,
    enrich: enrichAssetNames.value,
    autoId: autoTransactionId.value,
    hash: hashColumns.value,
    ticker: tickerColumnPick.value,
  });
  const isDirty = computed(() => initialSnapshot.value !== stateSnapshot());

  const field = computed(() => ctx.value?.field);
  const isName = computed(() => field.value?.key === 'name');
  const isTransactionId = computed(() => field.value?.key === 'transaction_id');

  watch(show, (open) => {
    if (!open || !ctx.value) return;
    const initial = ctx.value.initialMapping;
    formula.value = [...(initial?.formula || [])];
    sourceMode.value = formula.value.length ? 'formula' : 'simple';
    if (initial?.divisor) {
      transformationType.value = 'divisor';
      transformationValue.value = initial.divisor;
    } else if (initial?.multiplier) {
      transformationType.value = 'multiplier';
      transformationValue.value = initial.multiplier;
    } else {
      transformationType.value = 'none';
      transformationValue.value = null;
    }
    const initialEnums: Record<string, string> = {};
    ctx.value.uniqueCsvValues.forEach(v => { initialEnums[v] = initial?.enumMappings?.[v] || ''; });
    enumMappings.value = initialEnums;
    dateFormat.value = initial?.dateFormat || 'auto';
    enrichAssetNames.value = initial?.enrichAssetNames || 'when_empty';
    autoTransactionId.value = ctx.value.opTypeSettings?.autoTransactionId
      || initial?.enrichTransactionIds || 'when_empty';
    hashColumns.value = [...(ctx.value.opTypeSettings?.hashColumns || [])];
    tickerColumnPick.value = '';
    initialSnapshot.value = stateSnapshot();
  }, { immediate: true });

  // --- Asset-name enrichment (live lookup, mirrors the import-time behavior) ---
  const enrichedNameVal = ref('');
  const isEnriching = ref(false);
  const enrichedCache = ref<Record<string, string>>({});

  watch([enrichAssetNames, () => ctx.value?.exampleTicker, show], async ([mode, ticker]) => {
    const shouldEnrich = show.value && isName.value && mode !== 'never' && !!ticker;
    if (!shouldEnrich) {
      enrichedNameVal.value = '';
      return;
    }
    const key = ticker as string;
    if (enrichedCache.value[key]) {
      enrichedNameVal.value = enrichedCache.value[key];
      return;
    }
    isEnriching.value = true;
    enrichedNameVal.value = 'loading...';
    try {
      const profile = await api.getTickerProfile(key);
      enrichedNameVal.value = profile?.name || `${key} (Not Found)`;
      if (profile?.name) enrichedCache.value[key] = profile.name;
    } catch {
      enrichedNameVal.value = `${key} (Not Found)`;
    } finally {
      isEnriching.value = false;
    }
  }, { immediate: true });

  // --- Live preview through the shared engine ---
  const draftMapping = computed<ColMapping>(() => ({
    dbKey: field.value?.key || '',
    divisor: transformationType.value === 'divisor' ? (transformationValue.value || undefined) : undefined,
    multiplier: transformationType.value === 'multiplier' ? (transformationValue.value || undefined) : undefined,
    formula: sourceMode.value === 'formula' && formula.value.length ? formula.value : undefined,
    enumMappings: field.value?.type === 'enum' ? enumMappings.value : undefined,
    dateFormat: field.value?.type === 'datetime' ? dateFormat.value : undefined,
    enrichAssetNames: isName.value ? enrichAssetNames.value : undefined,
    enrichTransactionIds: isTransactionId.value ? autoTransactionId.value : undefined,
  }));

  const liveConversion = computed(() => {
    if (!ctx.value) return { success: true, value: '' };
    return computeLivePreview(field.value, ctx.value.exampleValue, draftMapping.value, {
      decimalSeparator: ctx.value.decimalSeparator || '.',
      rowByHeader: ctx.value.exampleRowByHeader,
      isRequired: false,
      enrichMode: enrichAssetNames.value,
      tickerMapped: ctx.value.tickerMapped || !!tickerColumnPick.value,
      exampleTicker: ctx.value.exampleTicker,
      enrichedName: enrichedNameVal.value,
      isEnriching: isEnriching.value,
      autoIdMode: autoTransactionId.value,
    });
  });

  const needsTickerPrompt = computed(() =>
    isName.value && enrichAssetNames.value !== 'never' && !ctx.value?.tickerMapped && !tickerColumnPick.value
  );

  const hashCountOk = computed(() => {
    if (!isTransactionId.value || autoTransactionId.value === 'never') return true;
    const total = Object.keys(ctx.value?.exampleRowByHeader || {}).length;
    const selected = hashColumns.value.length === 0 ? total : hashColumns.value.length;
    return selected >= 2;
  });

  const isSaveDisabled = computed(() => {
    if (sourceMode.value === 'formula' && !isValidFormula(formula.value)) return true;
    if (needsTickerPrompt.value) return true;
    if (!hashCountOk.value) return true;
    if (field.value?.type === 'enum' && ctx.value?.exampleValue?.trim() && !enumMappings.value[ctx.value.exampleValue]) {
      return true;
    }
    return !liveConversion.value.success;
  });

  return {
    sourceMode,
    formula,
    transformationType,
    transformationValue,
    enumMappings,
    dateFormat,
    enrichAssetNames,
    autoTransactionId,
    hashColumns,
    tickerColumnPick,
    field,
    isName,
    isTransactionId,
    enrichedNameVal,
    isEnriching,
    draftMapping,
    liveConversion,
    needsTickerPrompt,
    isSaveDisabled,
    isDirty,
  };
}
