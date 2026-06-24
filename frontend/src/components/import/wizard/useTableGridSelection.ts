import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue';

export interface GridSelectionProps {
  exampleTransactions: Array<{
    opType: string;
    csvRow: string[];
    rowIdx: number;
    totalMatches: number;
    currentOffset: number;
  }>;
  uiColumns: Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }>;
  columnConfigMap: Record<string, {
    typeSpecific: Record<string, { dbKey: string; divisor?: number; multiplier?: number; enumMappings?: Record<string, string>; dateFormat?: string }>;
  }>;
  operationTypeMappings: Record<string, string>;
  importFields: any[];
}

export function useTableGridSelection(
  props: GridSelectionProps,
  emit: (event: any, ...args: any[]) => void
) {
  // Selected cells for keyboard selection & actions
  const selectedCells = ref<Set<string>>(new Set());
  const lastSelectedCell = ref<{ colId: string; opType: string } | null>(null);

  // Clipboard state for copy-pasting mappings
  const copiedMapping = ref<{
    colId: string;
    opType: string;
    dbKey: string;
    divisor?: number;
    multiplier?: number;
    enumMappings?: Record<string, string>;
    dateFormat?: string;
  } | null>(null);

  // Cell flashing state for visual shortcut feedback
  const recentlyFlashed = ref<Record<string, string>>({}); // cellKey -> CSS class

  const flashCell = (colId: string, opType: string, flashClass: string) => {
    const key = `${colId}:::${opType}`;
    recentlyFlashed.value[key] = flashClass;
    setTimeout(() => {
      delete recentlyFlashed.value[key];
    }, 1000);
  };

  const isSelected = (colId: string, opType: string): boolean => {
    const key = `${colId}:::${opType}`;
    return selectedCells.value.has(key);
  };

  const isCopiedSource = (colId: string, opType: string): boolean => {
    return copiedMapping.value !== null &&
      copiedMapping.value.colId === colId &&
      copiedMapping.value.opType === opType;
  };

  const getCellOutlineStyle = (colId: string, opType: string) => {
    if (isSelected(colId, opType)) {
      return '2px solid var(--accent-color)';
    }
    if (isCopiedSource(colId, opType)) {
      return '2px dashed var(--accent-color)';
    }
    return undefined;
  };

  const selectCell = (colId: string, opType: string, multiSelect: boolean) => {
    const key = `${colId}:::${opType}`;
    if (multiSelect) {
      if (selectedCells.value.has(key)) {
        selectedCells.value.delete(key);
        if (lastSelectedCell.value?.colId === colId && lastSelectedCell.value?.opType === opType) {
          const remaining = Array.from(selectedCells.value);
          if (remaining.length > 0) {
            const parts = remaining[remaining.length - 1].split(':::');
            lastSelectedCell.value = { colId: parts[0], opType: parts[1] };
          } else {
            lastSelectedCell.value = null;
          }
        }
      } else {
        selectedCells.value.add(key);
        lastSelectedCell.value = { colId, opType };
      }
    } else {
      selectedCells.value.clear();
      selectedCells.value.add(key);
      lastSelectedCell.value = { colId, opType };
    }
  };

  const selectColumn = (colId: string) => {
    selectedCells.value.clear();
    props.exampleTransactions.forEach(example => {
      selectedCells.value.add(`${colId}:::${example.opType}`);
    });
    if (props.exampleTransactions.length > 0) {
      const firstOpType = props.exampleTransactions[0].opType;
      lastSelectedCell.value = { colId, opType: firstOpType };
      nextTick(() => {
        const selector = `#cell-${sanitizeId(firstOpType)}-${colId}`;
        const el = document.querySelector(selector) as HTMLTableCellElement;
        if (el) el.focus();
      });
    }
  };

  const getFirstSelectedCell = (): { colId: string; opType: string } | null => {
    const firstKey = Array.from(selectedCells.value)[0];
    if (!firstKey) return null;
    const parts = firstKey.split(':::');
    return { colId: parts[0], opType: parts[1] };
  };

  const openWizardForSelected = () => {
    if (selectedCells.value.size === 0) return;

    const primary = lastSelectedCell.value || getFirstSelectedCell();
    if (!primary) return;

    // Build full list of targets preserving each cell's colId and rawAction opType.
    // Pass all selected cells as individual targets so the wizard applies to each one.
    const targets = Array.from(selectedCells.value).map(key => {
      const parts = key.split(':::');
      return { colId: parts[0], opType: parts[1] || null };
    });

    const primaryDbOpType = primary.opType ? props.operationTypeMappings[primary.opType] : null;

    emit('open-wizard', {
      colId: primary.colId,
      opType: primaryDbOpType,
      targets,
      rawAction: primary.opType
    });
  };

  const handleCellClick = (colId: string, opType: string, event: MouseEvent) => {
    const isCtrl = event.ctrlKey || event.metaKey;
    const isAlreadySelected = isSelected(colId, opType);

    if (!isCtrl && isAlreadySelected && selectedCells.value.size === 1) {
      openWizardForSelected();
    } else {
      selectCell(colId, opType, isCtrl);
      (event.currentTarget as HTMLTableCellElement).focus();
    }
  };

  const copyMapping = (colId: string, opType: string) => {
    const conf = props.columnConfigMap[colId];
    if (!conf) return;

    const mappingToCopy = conf.typeSpecific[opType] || (props.operationTypeMappings[opType] ? conf.typeSpecific[props.operationTypeMappings[opType]] : null);

    if (mappingToCopy && mappingToCopy.dbKey) {
      copiedMapping.value = {
        colId,
        opType,
        dbKey: mappingToCopy.dbKey,
        divisor: mappingToCopy.divisor,
        multiplier: mappingToCopy.multiplier,
        enumMappings: mappingToCopy.enumMappings ? { ...mappingToCopy.enumMappings } : undefined,
        dateFormat: mappingToCopy.dateFormat
      };
      flashCell(colId, opType, 'bg-indigo-100/50 dark:bg-indigo-950/30 transition-all duration-300');
    }
  };

  const canPaste = (colId: string, opType: string): boolean => {
    if (!copiedMapping.value) return false;
    if (copiedMapping.value.colId === colId && copiedMapping.value.opType === opType) return false;
    return true;
  };

  const pasteMappingToSelected = () => {
    if (!copiedMapping.value || selectedCells.value.size === 0) return;

    selectedCells.value.forEach(key => {
      const parts = key.split(':::');
      const targetColId = parts[0];
      const targetOpType = parts[1];

      if (canPaste(targetColId, targetOpType)) {
        emit('update-mapping', {
          colId: targetColId,
          opType: targetOpType,
          mapping: {
            dbKey: copiedMapping.value!.dbKey,
            divisor: copiedMapping.value!.divisor,
            multiplier: copiedMapping.value!.multiplier,
            enumMappings: copiedMapping.value!.enumMappings,
            dateFormat: copiedMapping.value!.dateFormat
          }
        });
        flashCell(targetColId, targetOpType, 'bg-emerald-100/50 dark:bg-emerald-950/30 transition-all duration-300');
      }
    });
  };

  const clearMappingForSelected = () => {
    if (selectedCells.value.size === 0) return;

    selectedCells.value.forEach(key => {
      const parts = key.split(':::');
      const targetColId = parts[0];
      const targetOpType = parts[1];

      emit('update-mapping', {
        colId: targetColId,
        opType: targetOpType || null,
        mapping: null
      });
      flashCell(targetColId, targetOpType, 'bg-rose-100/50 dark:bg-rose-950/30 transition-all duration-300');
    });
  };

  const navigateGrid = (key: string) => {
    const primary = lastSelectedCell.value || getFirstSelectedCell();
    if (!primary) return;

    const colId = primary.colId;
    const opType = primary.opType;

    const rowIdx = props.exampleTransactions.findIndex(e => e.opType === opType);
    if (rowIdx === -1) return;

    const numCols = props.uiColumns.length;
    const numRows = props.exampleTransactions.length;

    let currentColIdx = props.uiColumns.findIndex(c => c.id === colId);
    if (currentColIdx === -1) currentColIdx = 0;

    let nextColIdx = currentColIdx;
    let nextRowIdx = rowIdx;

    if (key === 'ArrowLeft') {
      nextColIdx = nextColIdx - 1;
      if (nextColIdx < 0) nextColIdx = numCols - 1;
    } else if (key === 'ArrowRight') {
      nextColIdx = nextColIdx + 1;
      if (nextColIdx >= numCols) nextColIdx = 0;
    } else if (key === 'ArrowUp') {
      nextRowIdx = rowIdx - 1;
      if (nextRowIdx < 0) nextRowIdx = numRows - 1;
    } else if (key === 'ArrowDown') {
      nextRowIdx = rowIdx + 1;
      if (nextRowIdx >= numRows) nextRowIdx = 0;
    }

    const nextColId = props.uiColumns[nextColIdx].id;
    const nextOpType = props.exampleTransactions[nextRowIdx].opType;

    selectedCells.value.clear();
    const nextKey = `${nextColId}:::${nextOpType}`;
    selectedCells.value.add(nextKey);
    lastSelectedCell.value = { colId: nextColId, opType: nextOpType };

    nextTick(() => {
      const selector = `#cell-${sanitizeId(nextOpType)}-${nextColId}`;
      const el = document.querySelector(selector) as HTMLTableCellElement;
      if (el) el.focus();
    });
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    const target = e.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
      return;
    }

    if (selectedCells.value.size === 0) return;

    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const isCopy = (isMac ? e.metaKey : e.ctrlKey) && e.key.toLowerCase() === 'c';
    const isPaste = (isMac ? e.metaKey : e.ctrlKey) && e.key.toLowerCase() === 'v';
    const isClear = e.key === 'Delete' || e.key === 'Backspace';
    const isEnter = e.key === 'Enter' || e.key === ' ';

    if (isCopy) {
      e.preventDefault();
      const primary = lastSelectedCell.value || getFirstSelectedCell();
      if (primary) {
        copyMapping(primary.colId, primary.opType);
      }
    } else if (isPaste) {
      e.preventDefault();
      pasteMappingToSelected();
    } else if (isClear) {
      e.preventDefault();
      clearMappingForSelected();
    } else if (isEnter) {
      e.preventDefault();
      openWizardForSelected();
    } else if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
      e.preventDefault();
      navigateGrid(e.key);
    }
  };

  const getResolvedKeyForCell = (colId: string, opType: string) => {
    const conf = props.columnConfigMap[colId];
    if (!conf) return '';

    if (conf.typeSpecific && conf.typeSpecific[opType] !== undefined) {
      return conf.typeSpecific[opType].dbKey || '';
    }

    const dbOpType = props.operationTypeMappings[opType];
    if (dbOpType && conf.typeSpecific && conf.typeSpecific[dbOpType] !== undefined) {
      return conf.typeSpecific[dbOpType].dbKey || '';
    }

    return '';
  };

  const sanitizeId = (val: string) => {
    return encodeURIComponent(val).replace(/%/g, '_');
  };

  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', handleKeyDown);
  });

  return {
    selectedCells,
    lastSelectedCell,
    copiedMapping,
    recentlyFlashed,
    isSelected,
    isCopiedSource,
    getCellOutlineStyle,
    handleCellClick,
    openWizardForSelected,
    selectColumn,
    getResolvedKeyForCell,
    sanitizeId,
  };
}
