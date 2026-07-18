import { onMounted, onUnmounted } from 'vue';

// While the wizard is open, horizontal trackpad swipes must never trigger the
// browser's back/forward navigation — only scroll the wizard's own
// horizontally scrollable containers.
export function useSwipeNavGuard() {
  const preventSwipeNav = (e: WheelEvent) => {
    // Only intercept if it's primarily a horizontal swipe
    if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
      let target = e.target as HTMLElement | null;

      // Find nearest horizontally scrollable container
      while (target && target !== document.body && target !== document.documentElement) {
        const style = window.getComputedStyle(target);
        if ((style.overflowX === 'auto' || style.overflowX === 'scroll') && target.scrollWidth > target.clientWidth) {
          break;
        }
        target = target.parentElement;
      }

      if (target && target !== document.body && target !== document.documentElement) {
        const isAtLeftEdge = target.scrollLeft <= 0;
        const isAtRightEdge = target.scrollWidth - target.clientWidth <= target.scrollLeft + 1;

        // If we're at the edge and trying to scroll past it, aggressively prevent default
        // to kill the Chrome swipe navigation.
        if ((e.deltaX < 0 && isAtLeftEdge) || (e.deltaX > 0 && isAtRightEdge)) {
          e.preventDefault();
        }
      } else {
        // If we aren't even over a horizontal scroll container, ANY horizontal swipe is
        // just going to trigger browser navigation. Block it.
        e.preventDefault();
      }
    }
  };

  onMounted(() => {
    document.documentElement.style.overscrollBehaviorX = 'none';
    document.body.style.overscrollBehaviorX = 'none';
    window.addEventListener('wheel', preventSwipeNav, { passive: false });
  });

  onUnmounted(() => {
    document.documentElement.style.overscrollBehaviorX = '';
    document.body.style.overscrollBehaviorX = '';
    window.removeEventListener('wheel', preventSwipeNav);
  });
}
