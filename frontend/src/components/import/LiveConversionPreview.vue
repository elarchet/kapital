<script setup lang="ts">
import { CheckCircle, AlertCircle } from '@lucide/vue';

defineProps<{
  liveConversion: {
    success: boolean;
    value?: string;
    error?: string;
  };
  shouldShake: boolean;
}>();
</script>

<template>
  <div 
    class="preview-box" 
    :class="{ 
      'preview-success': liveConversion.success, 
      'preview-error': !liveConversion.success,
      'shake-anim': shouldShake 
    }"
  >
    <div style="display: flex; align-items: flex-start; gap: 0.5rem;">
      <CheckCircle v-if="liveConversion.success" style="width: 18px; height: 18px; color: var(--color-success); flex-shrink: 0; margin-top: 0.1rem;" />
      <AlertCircle v-else style="width: 18px; height: 18px; color: var(--color-danger); flex-shrink: 0; margin-top: 0.1rem;" />
      <div>
        <div class="preview-heading">Live Conversion Preview</div>
        <div class="preview-result">
          <span v-if="liveConversion.success" style="font-weight: 600; color: var(--text-primary);">
            {{ liveConversion.value }}
          </span>
          <span v-else style="color: var(--color-danger); font-size: 0.8rem;">
            {{ liveConversion.error }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.preview-box {
  margin-top: 1.25rem;
  border-radius: var(--radius-sm);
  padding: 0.75rem 1rem;
  border: 1px solid transparent;
  transition: transform 0.15s ease;
}

.preview-success {
  background-color: var(--color-success-light);
  border-color: rgba(16, 185, 129, 0.2);
}

.preview-error {
  background-color: var(--color-danger-light);
  border-color: rgba(239, 68, 68, 0.2);
}

.preview-heading {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
}

.preview-result {
  font-size: 0.875rem;
  margin-top: 0.15rem;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-6px); }
  20%, 40%, 60%, 80% { transform: translateX(6px); }
}

.shake-anim {
  animation: shake 0.4s ease-in-out;
}
</style>
