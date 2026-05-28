<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue';
import { AlertTriangle } from '@lucide/vue';

const props = withDefaults(defineProps<{
  show: boolean;
  title?: string;
  message?: string;
}>(), {
  title: 'Discard Unsaved Changes?',
  message: 'You have unsaved mapping configuration changes. Leaving now will discard these changes.'
});

const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'confirm'): void;
}>();

const selectedOption = ref<'keep' | 'discard'>('discard');

const handleKeyDown = (e: KeyboardEvent) => {
  if (!props.show) return;

  if (e.key === 'Escape') {
    e.preventDefault();
    e.stopPropagation();
    emit('cancel');
  } else if (e.key === 'Enter') {
    e.preventDefault();
    e.stopPropagation();
    if (selectedOption.value === 'discard') {
      emit('confirm');
    } else {
      emit('cancel');
    }
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'Tab') {
    e.preventDefault();
    e.stopPropagation();
    selectedOption.value = selectedOption.value === 'keep' ? 'discard' : 'keep';
  }
};

watch(() => props.show, (newVal) => {
  if (newVal) {
    selectedOption.value = 'discard'; // default option is discard changes
    window.addEventListener('keydown', handleKeyDown, true);
  } else {
    window.removeEventListener('keydown', handleKeyDown, true);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown, true);
});
</script>

<template>
  <div v-if="show" class="fixed inset-0 w-screen h-screen bg-slate-900/60 backdrop-blur-[4px] flex items-center justify-center z-[300] animate-[fadeIn_0.15s_ease-out_forwards]" @click.self="$emit('cancel')">
    <div class="w-full max-w-[440px] bg-bg-secondary border border-border-color rounded-md shadow-lg overflow-hidden flex flex-col animate-[slideUp_0.15s_ease-out]">
      <div class="p-6">
        <div style="display: flex; gap: 1rem; align-items: flex-start;">
          <div class="bg-danger-light p-2 rounded-full flex items-center justify-center flex-shrink-0">
            <AlertTriangle style="width: 24px; height: 24px; color: var(--color-danger);" />
          </div>
          <div>
            <h5 style="color: var(--text-primary); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
              {{ title }}
            </h5>
            <p style="font-size: 0.875rem; color: var(--text-secondary); line-height: 1.4;">
              {{ message }}
            </p>
          </div>
        </div>
      </div>
      <div class="py-4 px-6 border-t border-border-color flex justify-end gap-3 bg-bg-primary">
        <button 
          @click="$emit('cancel')" 
          @mouseenter="selectedOption = 'keep'"
          class="btn btn-sm"
          :class="{ 'outline-2 outline-accent outline-offset-2 shadow-[0_0_0_3px] shadow-accent-light': selectedOption === 'keep' }"
        >
          Keep Editing
        </button>
        <button 
          @click="$emit('confirm')" 
          @mouseenter="selectedOption = 'discard'"
          class="btn btn-sm btn-danger-solid"
          :class="{ 'outline-2 outline-danger-color outline-offset-2 shadow-[0_0_0_3px] shadow-danger-light': selectedOption === 'discard' }"
        >
          Discard Changes
        </button>
      </div>
    </div>
  </div>
</template>
