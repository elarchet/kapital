import { ref, readonly } from 'vue';

export type NotificationType = 'success' | 'info' | 'warning' | 'error';

export interface AppNotification {
  id: number;
  type: NotificationType;
  title: string;
  /** Optional detail line under the title. */
  message?: string;
}

export interface NotifyOptions {
  message?: string;
  /** Auto-dismiss delay in ms; 0 keeps the toast until it is closed manually. */
  duration?: number;
}

// Module-level state: every caller shares the one toast stack rendered by
// the notification-toasts component mounted in App.vue.
const notifications = ref<AppNotification[]>([]);
const timers = new Map<number, ReturnType<typeof setTimeout>>();
let nextId = 1;

const DEFAULT_DURATIONS: Record<NotificationType, number> = {
  success: 6000,
  info: 6000,
  warning: 8000,
  // Errors stay until dismissed: the user may need the detail to react.
  error: 0,
};

const dismiss = (id: number) => {
  const timer = timers.get(id);
  if (timer) {
    clearTimeout(timer);
    timers.delete(id);
  }
  notifications.value = notifications.value.filter(n => n.id !== id);
};

const notify = (type: NotificationType, title: string, options: NotifyOptions = {}): number => {
  const id = nextId++;
  notifications.value = [...notifications.value, { id, type, title, message: options.message }];
  const duration = options.duration ?? DEFAULT_DURATIONS[type];
  if (duration > 0) {
    timers.set(id, setTimeout(() => dismiss(id), duration));
  }
  return id;
};

export function useNotifications() {
  return {
    notifications: readonly(notifications),
    notify,
    dismiss,
    notifySuccess: (title: string, options?: NotifyOptions) => notify('success', title, options),
    notifyInfo: (title: string, options?: NotifyOptions) => notify('info', title, options),
    notifyWarning: (title: string, options?: NotifyOptions) => notify('warning', title, options),
    notifyError: (title: string, options?: NotifyOptions) => notify('error', title, options),
  };
}
