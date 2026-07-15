import { ref, computed, type Ref } from 'vue';
import { getExampleTransactions } from '../../services/import';

// Example-row cycling per raw action (feeds the preview enrichment pipeline)
// plus rawAction -> DB op type mapping edits.
export function useWizardMapping(
  matchingRowsByRawAction: Ref<Record<string, { csvRow: string[]; rowIdx: number }[]>>,
  operationTypeMappings: Ref<Record<string, string>>,
  uniqueOperationTypes: Ref<string[]>
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

  const handleUpdateOpTypeMapping = ({ rawAction, dbOpType }: { rawAction: string; dbOpType: string }) => {
    if (dbOpType === '') {
      delete operationTypeMappings.value[rawAction];
    } else {
      operationTypeMappings.value[rawAction] = dbOpType;
    }
    operationTypeMappings.value = { ...operationTypeMappings.value };
  };

  return {
    exampleTransactions,
    nextExampleForType,
    prevExampleForType,
    handleUpdateOpTypeMapping,
  };
}
