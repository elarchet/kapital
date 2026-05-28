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
  <div v-if="show" class="confirm-modal-overlay" @click.self="$emit('cancel')">
    <div class="confirm-modal-card">
      <div class="confirm-modal-body">
        <div style="display: flex; gap: 1rem; align-items: flex-start;">
          <div class="alert-icon-container">
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
      <div class="confirm-modal-footer">
        <button 
          @click="$emit('cancel')" 
          @mouseenter="selectedOption = 'keep'"
          class="btn btn-sm"
          :class="{ 'active-selection': selectedOption === 'keep' }"
        >
          Keep Editing
        </button>
        <button 
          @click="$emit('confirm')" 
          @mouseenter="selectedOption = 'discard'"
          class="btn btn-sm btn-danger-action"
          :class="{ 'active-selection': selectedOption === 'discard' }"
        >
          Discard Changes
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.confirm-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300; /* Ensure overlay displays on top of everything */
  animation: fadeIn 0.15s ease-out forwards;
}

.confirm-modal-card {
  width: 100%;
  max-width: 440px;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: slideUp 0.15s ease-out;
}

.confirm-modal-body {
  padding: 1.5rem;
}

.alert-icon-container {
  background-color: var(--color-danger-light);
  padding: 0.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.confirm-modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  background-color: var(--bg-primary);
}

.btn-danger-action {
  background-color: var(--color-danger);
  color: white;
  border-color: var(--color-danger);
}
.btn-danger-action:hover {
  background-color: #dc2626;
  border-color: #dc2626;
}

.active-selection {
  outline: 2px solid var(--accent-color);
  outline-offset: 2px;
  box-shadow: 0 0 0 3px var(--accent-light);
}

.btn-danger-action.active-selection {
  outline: 2px solid var(--color-danger);
  outline-offset: 2px;
  box-shadow: 0 0 0 3px var(--color-danger-light);
  background-color: #dc2626;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(15px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
</style>
