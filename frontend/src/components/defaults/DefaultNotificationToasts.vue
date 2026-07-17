<script setup lang="ts">
import { AlertTriangle, AlertCircle, Info, CheckCircle, X } from '@lucide/vue';
import { useNotifications, type NotificationType } from '../../composables/useNotifications';

// Renders the shared toast stack (see useNotifications). Mounted once in
// App.vue; any code can push toasts via the composable.
const { notifications, dismiss } = useNotifications();

const variantConfig: Record<NotificationType, { icon: any; iconBgColor: string; iconColor: string; barColor: string }> = {
  success: {
    icon: CheckCircle,
    iconBgColor: 'var(--color-success-light)',
    iconColor: 'var(--color-success)',
    barColor: 'var(--color-success)',
  },
  info: {
    icon: Info,
    iconBgColor: 'var(--accent-light)',
    iconColor: 'var(--accent-color)',
    barColor: 'var(--accent-color)',
  },
  warning: {
    icon: AlertTriangle,
    iconBgColor: 'var(--color-warning-light)',
    iconColor: 'var(--color-warning)',
    barColor: 'var(--color-warning)',
  },
  error: {
    icon: AlertCircle,
    iconBgColor: 'var(--color-danger-light)',
    iconColor: 'var(--color-danger)',
    barColor: 'var(--color-danger)',
  },
};
</script>

<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[400] flex flex-col gap-2 w-[360px] max-w-[calc(100vw-2rem)] pointer-events-none">
      <TransitionGroup
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-x-4"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0 translate-x-4"
      >
        <div
          v-for="toast in notifications"
          :key="toast.id"
          class="pointer-events-auto flex items-start gap-3 bg-bg-secondary border border-border-color rounded-md shadow-lg py-3 pr-3 pl-0 overflow-hidden"
          data-testid="notification-toast"
          :data-type="toast.type"
          role="status"
        >
          <div class="self-stretch w-1 shrink-0 rounded-full" :style="{ backgroundColor: variantConfig[toast.type].barColor }" />
          <div
            :style="{ backgroundColor: variantConfig[toast.type].iconBgColor }"
            class="p-1.5 rounded-full flex items-center justify-center shrink-0"
          >
            <component
              :is="variantConfig[toast.type].icon"
              class="w-4.5 h-4.5"
              :style="{ color: variantConfig[toast.type].iconColor }"
            />
          </div>
          <div class="min-w-0 flex-1 pt-0.5">
            <div class="text-sm font-semibold text-text-primary">{{ toast.title }}</div>
            <div v-if="toast.message" class="text-xs text-text-secondary mt-0.5 leading-snug">{{ toast.message }}</div>
          </div>
          <button
            class="bg-transparent border-none cursor-pointer p-1 rounded-sm text-text-secondary hover:bg-bg-tertiary shrink-0"
            title="Dismiss"
            @click="dismiss(toast.id)"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
