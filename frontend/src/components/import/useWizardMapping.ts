import { ref, computed } from 'vue';
import {
  getWizardSetup,
  saveWizardConfig,
  clearWizardConfig,
  getExampleTransactions
} from '../../services/import';

export function useWizardMapping(
  uiColumns: any,
  columnConfigMap: any,
  importFileHeaders: any,
  matchingRowsByType: any,
  matchingRowsByRawAction: any,
  allRawRows: any,
  operationTypeMappings: any
) {
  const isWizardOpen = ref(false);
  const wizardCsvHeaderName = ref('');
  const wizardExampleValue = ref('');
  const wizardActiveOpType = ref('');
  const wizardColId = ref<string | null>(null);
  const wizardColIdx = ref<number | null>(null);
  const wizardUniqueValues = ref<string[]>([]);
  const wizardInitialMapping = ref<any>(null);
  const wizardTargetCells = ref<Array<{ colId: string; opType: string | null }>>([]);

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
      Object.keys(matchingRowsByRawAction.value),
      matchingRowsByRawAction.value,
      selectedExampleOffset.value
    );
  });

  const openWizard = (colId: string, opType: string | null, targets?: Array<{ colId: string; opType: string | null }>, rawAction?: string | null) => {
    const col = uiColumns.value.find((c: any) => c.id === colId);
    if (!col) return;
    const colIdx = col.colIdx;

    wizardColId.value = colId;
    wizardColIdx.value = colIdx;
    wizardActiveOpType.value = opType || '';
    wizardTargetCells.value = targets && targets.length > 0 ? targets : [{ colId, opType: rawAction || opType }];

    const setup = getWizardSetup({
      colId,
      colIdx,
      opType,
      rawAction: rawAction || null,
      importFileHeaders: importFileHeaders.value,
      exampleTransactions: exampleTransactions.value,
      allRawRows: allRawRows.value,
      columnConfigMap: columnConfigMap.value,
      matchingRowsByType: matchingRowsByType.value,
      matchingRowsByRawAction: matchingRowsByRawAction.value,
      targets: wizardTargetCells.value.map(t => ({ colId: t.colId, colIdx: uiColumns.value.find((c: any) => c.id === t.colId)?.colIdx || 0, opType: t.opType }))
    });

    wizardCsvHeaderName.value = targets && targets.length > 1 ? `${setup.csvHeaderName} (+ ${targets.length - 1} other columns)` : setup.csvHeaderName;
    wizardExampleValue.value = setup.exampleValue;
    wizardUniqueValues.value = setup.uniqueValues;
    wizardInitialMapping.value = setup.initialMapping;
    isWizardOpen.value = true;
  };

  const handleWizardSave = (payload: any) => {
    if (wizardTargetCells.value.length > 0) {
      wizardTargetCells.value.forEach(target => {
        saveWizardConfig(columnConfigMap.value, target.colId, target.opType, { ...payload, scope: target.opType ? 'type' : 'global' });
      });
      columnConfigMap.value = { ...columnConfigMap.value };
    }
    isWizardOpen.value = false;
  };

  const handleWizardClear = () => {
    if (wizardTargetCells.value.length > 0) {
      wizardTargetCells.value.forEach(target => {
        clearWizardConfig(columnConfigMap.value, target.colId, target.opType);
      });
      columnConfigMap.value = { ...columnConfigMap.value };
    }
    isWizardOpen.value = false;
  };

  const handleUpdateMapping = ({ colId, opType, mapping }: any) => {
    if (mapping === null) {
      clearWizardConfig(columnConfigMap.value, colId, opType);
    } else {
      saveWizardConfig(columnConfigMap.value, colId, opType, {
        dbKey: mapping.dbKey,
        scope: opType ? 'type' : 'global',
        divisor: mapping.divisor,
        multiplier: mapping.multiplier,
        enumMappings: mapping.enumMappings,
        dateFormat: mapping.dateFormat
      });
    }
    columnConfigMap.value = { ...columnConfigMap.value };
  };

  const handleDuplicateColumn = (colId: string) => {
    const baseCol = uiColumns.value.find((c: any) => c.id === colId);
    if (!baseCol) return;
    const dupCount = uiColumns.value.filter((c: any) => c.colIdx === baseCol.colIdx).length;
    const newId = `${colId}_dup_${dupCount}`;
    const newCol = {
      id: newId,
      colIdx: baseCol.colIdx,
      name: baseCol.name,
      label: `${baseCol.name} (Copy)`,
      isDuplicate: true
    };
    const lastIndex = uiColumns.value.map((c: any) => c.colIdx).lastIndexOf(baseCol.colIdx);
    uiColumns.value.splice(lastIndex + 1, 0, newCol);
    columnConfigMap.value[newId] = { global: { dbKey: '' }, typeSpecific: {} };
    columnConfigMap.value = { ...columnConfigMap.value };
  };

  const handleDeleteColumn = (colId: string) => {
    const index = uiColumns.value.findIndex((c: any) => c.id === colId);
    if (index !== -1 && uiColumns.value[index].isDuplicate) {
      uiColumns.value.splice(index, 1);
      delete columnConfigMap.value[colId];
      columnConfigMap.value = { ...columnConfigMap.value };
    }
  };

  const handleUpdateOpTypeMapping = ({ rawAction, dbOpType }: { rawAction: string; dbOpType: string }) => {
    if (dbOpType === '') {
      delete operationTypeMappings.value[rawAction];
    } else {
      operationTypeMappings.value[rawAction] = dbOpType;
    }
    operationTypeMappings.value = { ...operationTypeMappings.value };
  };

  return {
    isWizardOpen,
    wizardCsvHeaderName,
    wizardExampleValue,
    wizardActiveOpType,
    wizardColId,
    wizardColIdx,
    wizardUniqueValues,
    wizardInitialMapping,
    wizardTargetCells,
    exampleTransactions,
    nextExampleForType,
    prevExampleForType,
    openWizard,
    handleWizardSave,
    handleWizardClear,
    handleUpdateMapping,
    handleDuplicateColumn,
    handleDeleteColumn,
    handleUpdateOpTypeMapping,
  };
}
