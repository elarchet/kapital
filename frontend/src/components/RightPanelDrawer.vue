<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { X, ArrowLeft, ArrowRight } from '@lucide/vue';

const props = withDefaults(defineProps<{
  show?: boolean;
  minWidth?: number;
  initialWidth?: number;
}>(), {
  show: true,
  minWidth: 500,
  initialWidth: 800,
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

// Keyboard listener for Escape
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    emit('close');
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
  <div class="fixed inset-0 z-[100] flex justify-end bg-slate-900/10 backdrop-blur-[1px]" @click.self="emit('close')">
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

      <!-- Header wrapper -->
      <div class="flex items-center justify-between py-3.5 px-5 border-b border-border-color bg-bg-secondary shrink-0">
        <div class="flex items-center gap-3 flex-1 min-w-0">
          <!-- Toggle Full Screen arrow on the left -->
          <button 
            @click="toggleFullScreen" 
            class="flex items-center justify-center p-1.5 rounded-sm bg-transparent border-0 cursor-pointer text-text-secondary transition-colors duration-150 ease-in-out hover:bg-bg-tertiary hover:text-text-primary shrink-0"
            :title="isSnapped ? 'Exit full screen' : 'Full screen'"
          >
            <ArrowRight v-if="isSnapped" class="w-4 h-4" />
            <ArrowLeft v-else class="w-4 h-4" />
          </button>
          
          <div class="flex-1 min-w-0">
            <slot name="header"></slot>
          </div>
        </div>
        
        <div class="flex items-center gap-2 ml-4 shrink-0">
          <button 
            @click="emit('close')" 
            class="flex items-center justify-center p-1.5 rounded-sm bg-transparent border-0 cursor-pointer text-text-secondary transition-colors duration-150 ease-in-out hover:bg-bg-tertiary hover:text-text-primary"
            title="Close panel"
          >
            <X class="w-4.5 h-4.5" />
          </button>
        </div>
      </div>

      <!-- Body wrapper -->
      <div class="flex-1 overflow-y-auto p-5 bg-bg-primary min-h-0">
        <slot name="body"></slot>
      </div>

      <!-- Footer wrapper -->
      <div class="py-3.5 px-5 border-t border-border-color flex justify-end gap-3 bg-bg-secondary shrink-0">
        <slot name="footer"></slot>
      </div>
    </div>
  </div>
</template>
