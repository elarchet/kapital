import { ref, computed, type Ref } from 'vue';
import { getExampleTransactions } from '../../services/import';
import type { ColumnConfig } from '../../services/import/types';

// Example-row cycling per raw action (feeds the preview enrichment pipeline)
// plus rawAction -> DB op type mapping edits and split/merge mode per DB type.
export function useWizardMapping(
  matchingRowsByRawAction: Ref<Record<string, { csvRow: string[]; rowIdx: number }[]>>,
  operationTypeMappings: Ref<Record<string, string>>,
  uniqueOperationTypes: Ref<string[]>,
  columnConfigMap: Ref<Record<string, ColumnConfig>>,
  splitOpTypes: Ref<string[]>
) {
  const selectedExampleOffset = ref<Record<string, number>>({});

  const nextExampleForType = (opType: string) => {
    const matches = matchingRowsByRawAction.value[opType] || [];
    if (matches.length <= 1) return;
    selectedExampleOffset.value[opType] = ((selectedExampleOffset.value[opType] || 0) + 1) % matches.length;
  };

  const prevExampleForType = (opType: string) => {
    const matches = matchingRowsByRawAction.value[opType] || [];
    if (matches.length <= 1) return;
    selectedExampleOffset.value[opType] = ((selectedExampleOffset.value[opType] || 0) - 1 + matches.length) % matches.length;
  };

  const exampleTransactions = computed(() => {
    return getExampleTransactions(
      uniqueOperationTypes.value,
      matchingRowsByRawAction.value,
      selectedExampleOffset.value
    );
  });

  const rawsForType = (opType: string) =>
    Object.keys(operationTypeMappings.value).filter(r => operationTypeMappings.value[r] === opType);

  const touchConfig = () => {
    columnConfigMap.value = { ...columnConfigMap.value };
  };

  // Split mode: each raw action of the type gets its own column mappings, keyed by the
  // raw action string itself (the backend already resolves rawAction keys before opType
  // keys, so this needs no backend change). Merged mode keys mappings by the DB op type.
  const toggleSplitType = (opType: string, enabled: boolean) => {
    const raws = rawsForType(opType);
    if (enabled) {
      if (!splitOpTypes.value.includes(opType)) splitOpTypes.value = [...splitOpTypes.value, opType];
      Object.values(columnConfigMap.value).forEach(conf => {
        if (!conf?.typeSpecific) return;
        const base = conf.typeSpecific[opType];
        if (base?.length) {
          raws.forEach(raw => {
            // Don't clobber pre-existing rawAction-keyed mappings (legacy templates).
            if (!conf.typeSpecific[raw]?.some(m => m.dbKey)) {
              conf.typeSpecific[raw] = base.map(m => ({ ...m }));
            }
          });
        }
        delete conf.typeSpecific[opType];
      });
    } else {
      splitOpTypes.value = splitOpTypes.value.filter(t => t !== opType);
      // Keep the variant with the most real mappings as the merged mapping.
      let bestRaw: string | null = null;
      let bestCount = 0;
      raws.forEach(raw => {
        let count = 0;
        Object.values(columnConfigMap.value).forEach(conf => {
          count += (conf?.typeSpecific?.[raw] || []).filter(m => m.dbKey).length;
        });
        if (count > bestCount) { bestCount = count; bestRaw = raw; }
      });
      Object.values(columnConfigMap.value).forEach(conf => {
        if (!conf?.typeSpecific) return;
        if (bestRaw && conf.typeSpecific[bestRaw]?.some(m => m.dbKey)) {
          conf.typeSpecific[opType] = conf.typeSpecific[bestRaw].map(m => ({ ...m }));
        }
        raws.forEach(raw => { delete conf.typeSpecific[raw]; });
      });
    }
    touchConfig();
  };

  const handleUpdateOpTypeMapping = ({ rawAction, dbOpType }: { rawAction: string; dbOpType: string }) => {
    const previousType = operationTypeMappings.value[rawAction];
    if (dbOpType === '') {
      delete operationTypeMappings.value[rawAction];
    } else {
      operationTypeMappings.value[rawAction] = dbOpType;
    }
    operationTypeMappings.value = { ...operationTypeMappings.value };

    // Retargeted away from a split type: its per-value mappings are stale.
    if (previousType && previousType !== dbOpType && splitOpTypes.value.includes(previousType)) {
      Object.values(columnConfigMap.value).forEach(conf => {
        if (conf?.typeSpecific) delete conf.typeSpecific[rawAction];
      });
      // A split with fewer than 2 values is just a merged mapping again.
      if (rawsForType(previousType).length < 2) toggleSplitType(previousType, false);
      touchConfig();
    }
  };

  return {
    exampleTransactions,
    nextExampleForType,
    prevExampleForType,
    handleUpdateOpTypeMapping,
    toggleSplitType,
  };
}
