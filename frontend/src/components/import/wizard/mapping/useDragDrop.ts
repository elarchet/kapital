import { ref } from 'vue';

// Native HTML5 drag-and-drop for column chips -> field slots, plus a
// click-to-arm fallback so mappings can be made without dragging.
// dataTransfer is unreadable during dragover, hence the shared ref.
export function useDragDrop() {
  const draggingColId = ref<string | null>(null);
  const armedColId = ref<string | null>(null);

  const onChipDragStart = (colId: string, e: DragEvent) => {
    if (e.dataTransfer) {
      e.dataTransfer.setData('text/plain', colId);
      e.dataTransfer.effectAllowed = 'copy';
    }
    draggingColId.value = colId;
    armedColId.value = null;
  };

  const onChipDragEnd = () => {
    draggingColId.value = null;
  };

  const toggleArmChip = (colId: string) => {
    armedColId.value = armedColId.value === colId ? null : colId;
  };

  const disarm = () => {
    armedColId.value = null;
  };

  // Returns the column to assign on a drop or an armed click, then resets.
  const resolveDrop = (e?: DragEvent): string | null => {
    const colId = draggingColId.value
      || (e?.dataTransfer?.getData('text/plain') ?? null)
      || armedColId.value;
    draggingColId.value = null;
    armedColId.value = null;
    return colId || null;
  };

  return { draggingColId, armedColId, onChipDragStart, onChipDragEnd, toggleArmChip, disarm, resolveDrop };
}
