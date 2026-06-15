<script setup lang="ts">
import { ref, watch, onBeforeUnmount, computed } from 'vue';
import { AlertTriangle, AlertCircle, Info, CheckCircle } from '@lucide/vue';

const props = withDefaults(defineProps<{
  show: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info' | 'success';
  defaultAction?: 'confirm' | 'cancel';
}>(), {
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  variant: 'danger',
  defaultAction: 'cancel'
});

const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'confirm'): void;
}>();

const selectedOption = ref<'confirm' | 'cancel'>('cancel');

const handleKeyDown = (e: KeyboardEvent) => {
  if (!props.show) return;

  if (e.key === 'Escape') {
    e.preventDefault();
    e.stopPropagation();
    emit('cancel');
  } else if (e.key === 'Enter') {
    e.preventDefault();
    e.stopPropagation();
    if (selectedOption.value === 'confirm') {
      emit('confirm');
    } else {
      emit('cancel');
    }
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'Tab') {
    e.preventDefault();
    e.stopPropagation();
    selectedOption.value = selectedOption.value === 'confirm' ? 'cancel' : 'confirm';
  }
};

watch(() => props.show, (newVal) => {
  if (newVal) {
    selectedOption.value = props.defaultAction;
    window.addEventListener('keydown', handleKeyDown, true);
  } else {
    window.removeEventListener('keydown', handleKeyDown, true);
  }
}, { immediate: true });

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown, true);
});

// Icon class and config based on variant using existing CSS variables
const variantConfig = computed(() => {
  switch (props.variant) {
    case 'warning':
      return {
        icon: AlertTriangle,
        iconBgColor: 'var(--color-warning-light)',
        iconColor: 'var(--color-warning)',
        confirmBtnClass: 'btn-primary'
      };
    case 'info':
      return {
        icon: Info,
        iconBgColor: 'var(--accent-light)',
        iconColor: 'var(--accent-color)',
        confirmBtnClass: 'btn-primary'
      };
    case 'success':
      return {
        icon: CheckCircle,
        iconBgColor: 'var(--color-success-light)',
        iconColor: 'var(--color-success)',
        confirmBtnClass: 'btn-primary'
      };
    case 'danger':
    default:
      return {
        icon: AlertCircle,
        iconBgColor: 'var(--color-danger-light)',
        iconColor: 'var(--color-danger)',
        confirmBtnClass: 'btn-danger-solid'
      };
  }
});
</script>

<template>
  <div v-if="show" class="fixed inset-0 w-screen h-screen bg-slate-900/20 backdrop-blur-[4px] flex items-center justify-center z-[300] animate-[fadeIn_0.15s_ease-out_forwards]" @click.self="$emit('cancel')">
    <div class="w-full max-w-[440px] bg-bg-secondary border border-border-color rounded-md shadow-lg overflow-hidden flex flex-col animate-[slideUp_0.15s_ease-out]">
      <div class="p-6">
        <div style="display: flex; gap: 1rem; align-items: flex-start;">
          <div 
            :style="{ backgroundColor: variantConfig.iconBgColor }"
            class="p-2 rounded-full flex items-center justify-center flex-shrink-0"
          >
            <component :is="variantConfig.icon" :style="{ width: '24px', height: '24px', color: variantConfig.iconColor }" />
          </div>
          <div>
            <h5 style="color: var(--text-primary); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
              {{ title }}
            </h5>
            <p style="font-size: 0.875rem; color: var(--text-secondary); line-height: 1.4; margin: 0;">
              {{ message }}
            </p>
          </div>
        </div>
      </div>
      <div class="py-4 px-6 border-t border-border-color flex justify-end gap-3 bg-bg-primary">
        <button 
          @click="$emit('cancel')" 
          @mouseenter="selectedOption = 'cancel'"
          class="btn btn-sm"
          :class="{ 'outline-2 outline-accent outline-offset-2 shadow-[0_0_0_3px] shadow-accent-light': selectedOption === 'cancel' }"
        >
          {{ cancelText }}
        </button>
        <button 
          @click="$emit('confirm')" 
          @mouseenter="selectedOption = 'confirm'"
          class="btn btn-sm"
          :class="[
            variantConfig.confirmBtnClass,
            { 
              'outline-2 outline-accent outline-offset-2 shadow-[0_0_0_3px] shadow-accent-light': selectedOption === 'confirm' && variant !== 'danger',
              'outline-2 outline-danger-color outline-offset-2 shadow-[0_0_0_3px] shadow-danger-light': selectedOption === 'confirm' && variant === 'danger'
            }
          ]"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>
