import { ref, computed, watch } from 'vue';
import { parseDateTimeWithFormat, getMappedColIdxForField } from '../../../services/import/validation';
import { api } from '../../../services/api';

export function useColumnMappingWizard(props: any, emit: any) {
  // Form states
  const selectedDbKey = ref('');
  const transformationType = ref<'none' | 'divisor' | 'multiplier'>('none');
  const transformationValue = ref<number | null>(null);
  const enumMappings = ref<Record<string, string>>({});
  const dateFormat = ref('auto');

  // Local states
  const localEnrichAssetNames = ref<'never' | 'when_empty' | 'always'>('when_empty');
  const localEnrichTransactionIds = ref<'never' | 'when_empty' | 'always'>('when_empty');
  const shouldShake = ref(false);
  const showExitConfirm = ref(false);
  const scope = computed<'global' | 'type'>(() => props.activeOpType ? 'type' : 'global');

  // Detect unsaved changes (dirty state check)
  const isWizardDirty = computed(() => {
    const initial = props.initialMapping;
    const initialKey = initial?.dbKey || '';
    if (selectedDbKey.value !== initialKey) return true;

    // check transformations
    const initialDiv = initial?.divisor;
    const initialMul = initial?.multiplier;
    const currentDiv = transformationType.value === 'divisor' ? transformationValue.value : undefined;
    const currentMul = transformationType.value === 'multiplier' ? transformationValue.value : undefined;
    if (currentDiv !== initialDiv || currentMul !== initialMul) return true;

    // check enum mappings
    const initialEnums = initial?.enumMappings || {};
    const uniqueVals = props.uniqueCsvValues;
    for (const val of uniqueVals) {
      const initialVal = initialEnums[val] || '';
      const currentVal = enumMappings.value[val] || '';
      if (currentVal !== initialVal) return true;
    }

    // check date format
    const initialDateFormat = initial?.dateFormat || 'auto';
    if (dateFormat.value !== initialDateFormat) return true;

    // check local auto-enrich changes
    const initialEnrichAsset = initial?.enrichAssetNames || 'when_empty';
    const initialEnrichTx = initial?.enrichTransactionIds || 'when_empty';
    if (localEnrichAssetNames.value !== initialEnrichAsset) return true;
    if (localEnrichTransactionIds.value !== initialEnrichTx) return true;

    return false;
  });

  // Initialize form from props
  watch(() => props.show, (newVal) => {
    if (newVal) {
      if (props.initialMapping) {
        selectedDbKey.value = props.initialMapping.dbKey || '';
        if (props.initialMapping.divisor) {
          transformationType.value = 'divisor';
          transformationValue.value = props.initialMapping.divisor;
        } else if (props.initialMapping.multiplier) {
          transformationType.value = 'multiplier';
          transformationValue.value = props.initialMapping.multiplier;
        } else {
          transformationType.value = 'none';
          transformationValue.value = null;
        }
        enumMappings.value = { ...(props.initialMapping.enumMappings || {}) };
        dateFormat.value = props.initialMapping.dateFormat || 'auto';
      } else {
        selectedDbKey.value = '';
        transformationType.value = 'none';
        transformationValue.value = null;
        enumMappings.value = {};
        dateFormat.value = 'auto';
      }

      // Initialize local copy of auto-enrich configs
      localEnrichAssetNames.value = props.initialMapping?.enrichAssetNames || 'when_empty';
      localEnrichTransactionIds.value = props.initialMapping?.enrichTransactionIds || 'when_empty';

      // Coerce 'never' -> 'when_empty' since it can't be disabled in UI
      if (selectedDbKey.value === 'name' && localEnrichAssetNames.value === 'never') {
        localEnrichAssetNames.value = 'when_empty';
      }
      if (selectedDbKey.value === 'transaction_id' && localEnrichTransactionIds.value === 'never') {
        localEnrichTransactionIds.value = 'when_empty';
      }

      showExitConfirm.value = false;
    }
  }, { immediate: true });

  // Auto-initialize enum values when dbKey changes to an enum type
  watch(selectedDbKey, (newKey) => {
    if (newKey === 'name' && localEnrichAssetNames.value === 'never') {
      localEnrichAssetNames.value = 'when_empty';
    }
    if (newKey === 'transaction_id' && localEnrichTransactionIds.value === 'never') {
      localEnrichTransactionIds.value = 'when_empty';
    }

    const field = props.importFields.find((f: any) => f.key === newKey);
    if (field && field.type === 'enum') {
      // Retain any existing mappings, and initialize missing ones
      const newMappings: Record<string, string> = {};
      props.uniqueCsvValues.forEach((val: string) => {
        newMappings[val] = enumMappings.value[val] || '';
      });
      enumMappings.value = newMappings;
    }
  });

  const selectedField = computed(() => {
    return props.importFields.find((f: any) => f.key === selectedDbKey.value);
  });

  const selectedOpTypes = computed<string[]>(() =>
    props.activeOpTypes && props.activeOpTypes.length > 0 ? props.activeOpTypes : (props.activeOpType ? [props.activeOpType] : [])
  );

  const tickerMappingStatus = computed(() => {
    if (!props.uiColumns || !props.columnConfigMap) return [];
    return selectedOpTypes.value.map(opType => {
      let idx = getMappedColIdxForField('ticker', opType, opType, props.columnConfigMap, props.uiColumns);
      const rawActions = Object.keys(props.operationTypeMappings || {}).filter(r => props.operationTypeMappings[r] === opType);
      for (const r of rawActions) {
        if (idx !== -1) break;
        idx = getMappedColIdxForField('ticker', r, opType, props.columnConfigMap, props.uiColumns);
      }
      return { opType, mapped: idx !== -1, colIdx: idx };
    });
  });

  const isTickerMapped = computed(() => tickerMappingStatus.value.some(s => s.mapped));
  const hasPartialTickerMapping = computed(() => {
    const mapped = tickerMappingStatus.value.filter(s => s.mapped).length;
    return mapped > 0 && mapped < tickerMappingStatus.value.length;
  });

  const exampleTicker = computed(() => {
    const status = props.exampleRow && props.exampleRow.length > 0 ? tickerMappingStatus.value.find(s => s.mapped) : null;
    const idx = status ? status.colIdx : -1;
    return idx !== -1 && idx < props.exampleRow.length ? (props.exampleRow[idx] || '') : '';
  });

  // Lazy enrichment state
  const enrichedNameVal = ref('');
  const isEnriching = ref(false);
  const enrichedCache = ref<Record<string, string>>({});

  watch(
    [selectedDbKey, exampleTicker, localEnrichAssetNames],
    async ([dbKey, ticker, enrichOption]) => {
      const shouldEnrich =
        enrichOption === 'always' ||
        (enrichOption === 'when_empty' && !props.exampleValue);

      if (dbKey !== 'name' || !shouldEnrich || !ticker) {
        enrichedNameVal.value = '';
        return;
      }

      if (enrichedCache.value[ticker]) {
        enrichedNameVal.value = enrichedCache.value[ticker];
        return;
      }

      isEnriching.value = true;
      enrichedNameVal.value = 'loading...';
      try {
        const profile = await api.getTickerProfile(ticker);
        if (profile && profile.name) {
          enrichedCache.value[ticker] = profile.name;
          enrichedNameVal.value = profile.name;
        } else {
          enrichedNameVal.value = `${ticker} (Not Found)`;
        }
      } catch (err) {
        console.error('Failed to resolve ticker in wizard:', err);
        enrichedNameVal.value = `${ticker} (Not Found)`;
      } finally {
        isEnriching.value = false;
      }
    },
    { immediate: true }
  );

  // Live conversion engine
  const liveConversion = computed(() => {
    if (!selectedDbKey.value) {
      return { success: true, value: 'Unmapped (Column ignored)' };
    }

    const rawVal = props.exampleValue;

    if (selectedDbKey.value === 'name') {
      const shouldEnrich =
        localEnrichAssetNames.value === 'always' ||
        (localEnrichAssetNames.value === 'when_empty' && !rawVal);

      if (shouldEnrich && isTickerMapped.value && exampleTicker.value) {
        if (isEnriching.value || enrichedNameVal.value === 'loading...') {
          return { success: true, value: 'Resolving asset name...' };
        }
        if (enrichedNameVal.value) {
          if (enrichedNameVal.value.endsWith('(Not Found)')) {
            return { success: false, error: `Failed to resolve asset name for ticker "${exampleTicker.value}".` };
          }
          return { success: true, value: `${rawVal || '—'} → ${enrichedNameVal.value} (Auto-Enriched)` };
        }
      }
      return { success: true, value: rawVal || (exampleTicker.value || 'Asset') };
    }

    if (selectedDbKey.value === 'transaction_id') {
      const shouldGenerate =
        localEnrichTransactionIds.value === 'always' ||
        (localEnrichTransactionIds.value === 'when_empty' && !rawVal);

      if (shouldGenerate) {
        // Generate a longer mock hash (16 chars) based on cells/exampleRow content
        const serialized = props.exampleRow?.join(',') || '';
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
        return { success: true, value: `${rawVal || '—'} → auto-${mockHash} (Auto-Generated)` };
      }
      return { success: true, value: rawVal || '—' };
    }

    if (rawVal === undefined || rawVal === null || rawVal.trim() === '') {
      if (selectedField.value?.is_required) {
        return { success: false, error: 'Example cell is empty but this database field is required.' };
      }
      return { success: true, value: 'Empty value (Ignored)' };
    }

    const fieldType = selectedField.value?.type;

    if (fieldType === 'numeric') {
      // Clean string using selected decimal separator
      let cleaned = rawVal.trim();
      if (props.decimalSeparator !== '.') {
        cleaned = cleaned.replace(props.decimalSeparator, '.');
      }
      // Remove thousands separator
      if (props.decimalSeparator === '.') {
        cleaned = cleaned.replace(/,/g, '');
      } else {
        cleaned = cleaned.replace(/\./g, '').replace(/\s/g, '');
      }

      let num = parseFloat(cleaned);
      if (isNaN(num)) {
        return { success: false, error: `"${rawVal}" cannot be parsed as a valid numeric decimal.` };
      }

      // Apply transformation
      if (transformationType.value === 'divisor' && transformationValue.value) {
        num /= transformationValue.value;
      } else if (transformationType.value === 'multiplier' && transformationValue.value) {
        num *= transformationValue.value;
      }

      return { success: true, value: num.toString() };
    }

    if (fieldType === 'datetime') {
      const cleaned = rawVal.trim();
      const parsedDate = parseDateTimeWithFormat(cleaned, dateFormat.value);
      if (!parsedDate) {
        return { success: false, error: `"${rawVal}" cannot be parsed as a valid timestamp with format "${dateFormat.value}".` };
      }
      return { success: true, value: parsedDate.toISOString() };
    }

    if (fieldType === 'enum') {
      const mapped = enumMappings.value[rawVal];
      if (!mapped) {
        return { success: false, error: `Value "${rawVal}" must be mapped to a DB enum option.` };
      }
      return { success: true, value: mapped };
    }

    // default is string
    return { success: true, value: rawVal };
  });

  const isSaveDisabled = computed(() => {
    if (!selectedDbKey.value) return false;
    if (!liveConversion.value.success) return true;

    // If enum, check that the example value is mapped
    if (selectedField.value?.type === 'enum') {
      if (props.exampleValue && props.exampleValue.trim()) {
        if (!enumMappings.value[props.exampleValue]) return true;
      }
    }

    return false;
  });

  const handleSave = () => {
    if (isSaveDisabled.value) return;

    emit('save', {
      dbKey: selectedDbKey.value,
      scope: scope.value,
      divisor: transformationType.value === 'divisor' ? (transformationValue.value || undefined) : undefined,
      multiplier: transformationType.value === 'multiplier' ? (transformationValue.value || undefined) : undefined,
      enumMappings: selectedField.value?.type === 'enum' ? enumMappings.value : undefined,
      dateFormat: selectedField.value?.type === 'datetime' ? dateFormat.value : undefined,
      enrichAssetNames: selectedDbKey.value === 'name' ? localEnrichAssetNames.value : undefined,
      enrichTransactionIds: selectedDbKey.value === 'transaction_id' ? localEnrichTransactionIds.value : undefined
    });
  };

  const handleClear = () => {
    emit('clear');
  };

  const attemptClose = () => {
    if (isWizardDirty.value) {
      showExitConfirm.value = true;
    } else {
      emit('close');
    }
  };

  // Enter key press triggers mapping application (or shakes conversion card if blocked)
  const onEnterPress = () => {
    if (isSaveDisabled.value) {
      shouldShake.value = true;
      setTimeout(() => {
        shouldShake.value = false;
      }, 500);
    } else {
      handleSave();
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      e.stopPropagation();
      onEnterPress();
    } else if (e.key === 'Escape') {
      e.stopPropagation(); // Stop Escape from bubbling to parent modal
      if (showExitConfirm.value) {
        showExitConfirm.value = false;
      } else {
        attemptClose();
      }
    }
  };

  return {
    selectedDbKey,
    transformationType,
    transformationValue,
    enumMappings,
    dateFormat,
    shouldShake,
    showExitConfirm,
    scope,
    isWizardDirty,
    selectedField,
    isTickerMapped,
    hasPartialTickerMapping,
    exampleTicker,
    enrichedNameVal,
    isEnriching,
    liveConversion,
    isSaveDisabled,
    localEnrichAssetNames,
    localEnrichTransactionIds,
    handleSave,
    handleClear,
    attemptClose,
    onEnterPress,
    handleKeyDown,
  };
}
