import { computed } from 'vue';

// Splits items into row-major chunks for a horizontally scrolling multi-row
// tray. Unlike CSS column-flow (which aligns items into equal-width columns,
// reading like a table), each row lays its items out back-to-back at natural
// width. At least 2 rows, more when the viewport is tall enough, never more
// than half the item count so short lists still fill their rows.
export function useChunkedRows<T>(items: () => T[], rowRem: number, maxVhFraction: number) {
  return computed<T[][]>(() => {
    const list = items();
    if (!list.length) return [];
    const remPx = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    const fromScreen = Math.max(2, Math.floor((window.innerHeight * maxVhFraction) / (rowRem * remPx)));
    const rowCount = Math.max(1, Math.min(fromScreen, Math.ceil(list.length / 2)));
    const base = Math.floor(list.length / rowCount);
    const extra = list.length % rowCount;
    const rows: T[][] = [];
    let idx = 0;
    for (let r = 0; r < rowCount; r++) {
      const size = base + (r < extra ? 1 : 0);
      rows.push(list.slice(idx, idx + size));
      idx += size;
    }
    return rows;
  });
}
