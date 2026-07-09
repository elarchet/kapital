<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { ChevronLeft, ChevronRight } from '@lucide/vue';

const props = withDefaults(defineProps<{
  show?: boolean;
  minWidth?: number;
  initialWidth?: number;
  bodyClass?: string;
}>(), {
  show: true,
  minWidth: 500,
  initialWidth: 800,
  bodyClass: '',
});

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const panelWidth = ref(props.initialWidth);
const isResizing = ref(false);
const isSnapped = ref(false);

const previousWidth = ref(props.initialWidth);

// Dynamic sizing adjustment when initialWidth prop changes
watch(() => props.initialWidth, (newWidth) => {
  if (!isResizing.value) {
    panelWidth.value = newWidth;
    previousWidth.value = newWidth;
    isSnapped.value = false;
  }
});

const startResize = (e: MouseEvent) => {
  e.preventDefault();
  isResizing.value = true;
  
  const handleMouseMove = (moveEvent: MouseEvent) => {
    if (!isResizing.value) return;
    const computedWidth = window.innerWidth - moveEvent.clientX;
    
    if (computedWidth < props.minWidth) {
      panelWidth.value = props.minWidth;
      isSnapped.value = false;
    } else if (computedWidth > window.innerWidth - 80) {
      panelWidth.value = window.innerWidth;
      isSnapped.value = true;
    } else {
      panelWidth.value = computedWidth;
      isSnapped.value = false;
      previousWidth.value = computedWidth; // remember last user-selected width
    }
  };
  
  const handleMouseUp = () => {
    isResizing.value = false;
    window.removeEventListener('mousemove', handleMouseMove);
    window.removeEventListener('mouseup', handleMouseUp);
  };
  
  window.addEventListener('mousemove', handleMouseMove);
  window.addEventListener('mouseup', handleMouseUp);
};

const restoreSize = () => {
  isSnapped.value = false;
  panelWidth.value = previousWidth.value > props.minWidth ? previousWidth.value : props.initialWidth;
};

const toggleFullScreen = () => {
  if (isSnapped.value) {
    restoreSize();
  } else {
    previousWidth.value = panelWidth.value;
    panelWidth.value = window.innerWidth;
    isSnapped.value = true;
  }
};

const handleClose = () => {
  if (isSnapped.value) {
    restoreSize();
  } else {
    emit('close');
  }
};

// Keyboard listener for Escape & F
const handleKeyDown = (e: KeyboardEvent) => {
  // Avoid capturing key events when the user is typing in form controls
  const target = e.target as HTMLElement;
  if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
    return;
  }

  if (e.key === 'Escape') {
    if (isSnapped.value) {
      restoreSize();
      e.stopImmediatePropagation();
      e.preventDefault();
    }
  } else if (e.key === 'f' || e.key === 'F') {
    toggleFullScreen();
    e.stopImmediatePropagation();
    e.preventDefault();
  }
};

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown);
});
</script>

<template>
  <div class="fixed inset-0 z-[100] flex justify-end bg-slate-900/10 backdrop-blur-[1px]" @click.self="handleClose">
    <div 
      class="relative h-full bg-bg-secondary border-l border-border-color shadow-2xl flex flex-col"
      :class="{ 'transition-[width] duration-300': !isResizing }"
      :style="{ width: isSnapped ? '100%' : `${panelWidth}px` }"
    >
      <!-- Resize Handle (left edge) -->
      <div 
        class="absolute top-0 left-0 bottom-0 w-2 cursor-ew-resize hover:bg-accent/20 active:bg-accent/40 z-[110] transition-colors duration-150"
        @mousedown="startResize"
      ></div>

      <!-- Full screen toggle button wrapper (Enlarged hit box) -->
      <button 
        @click="toggleFullScreen" 
        class="absolute top-[20px] -translate-y-1/2 w-8 h-12 bg-transparent z-[120] cursor-pointer group select-none border-0 p-0 outline-none focus:outline-none"
        :class="isSnapped ? 'left-0 translate-x-0' : 'left-0 -translate-x-full'"
        :title="isSnapped ? 'Exit full screen (Press F or Esc)' : 'Full screen (Press F)'"
      >
        <!-- Visible U-shaped chevron button -->
        <div 
          class="absolute top-1/2 -translate-y-1/2 flex items-center justify-center transition-all duration-300 ease-out active:scale-95"
          :class="isSnapped 
            ? 'left-0 w-6 h-9 rounded-r-full bg-slate-200/30 backdrop-blur-[6px] text-text-secondary group-hover:bg-slate-200/60 group-hover:text-text-primary group-hover:w-7' 
            : 'right-0 w-6 h-9 rounded-l-full bg-white/40 backdrop-blur-[6px] text-text-secondary group-hover:bg-white/70 group-hover:text-text-primary group-hover:w-7'
          "
        >
          <!-- Sliding Chevron icon inside -->
          <ChevronRight 
            v-if="isSnapped" 
            class="w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5" 
          />
          <ChevronLeft 
            v-else 
            class="w-4 h-4 transition-transform duration-300 group-hover:-translate-x-0.5" 
          />
        </div>
      </button>

      <!-- Header wrapper -->
      <div class="flex items-center justify-between py-2 px-3 border-b border-border-color bg-bg-secondary shrink-0">
        <div class="flex items-center gap-2 flex-1 min-w-0">
          <div 
            class="flex-1 min-w-0 transition-[padding] duration-300"
            :class="{ 'pl-11': isSnapped }"
          >
            <slot name="header"></slot>
          </div>
        </div>
      </div>

      <!-- Body wrapper -->
      <div 
        class="flex-1 overflow-y-auto p-5 bg-bg-primary min-h-0 flex flex-col"
        :class="bodyClass"
      >
        <slot name="body"></slot>
      </div>

      <!-- Footer wrapper -->
      <div class="py-3.5 px-5 border-t border-border-color flex justify-end gap-3 bg-bg-secondary shrink-0">
        <slot name="footer"></slot>
      </div>
    </div>
  </div>
</template>
