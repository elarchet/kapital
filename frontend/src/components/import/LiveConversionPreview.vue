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
    class="mt-5 rounded-sm py-3 px-4 border border-transparent transition-transform duration-150 ease-in-out" 
    :class="{ 
      'bg-success-light border-emerald-500/20': liveConversion.success, 
      'bg-danger-light border-red-500/20': !liveConversion.success,
      'shake-anim': shouldShake 
    }"
  >
    <div style="display: flex; align-items: flex-start; gap: 0.5rem;">
      <CheckCircle v-if="liveConversion.success" style="width: 18px; height: 18px; color: var(--color-success); flex-shrink: 0; margin-top: 0.1rem;" />
      <AlertCircle v-else style="width: 18px; height: 18px; color: var(--color-danger); flex-shrink: 0; margin-top: 0.1rem;" />
      <div>
        <div class="text-[0.7rem] font-bold uppercase text-text-secondary tracking-wider">Live Conversion Preview</div>
        <div class="text-[0.875rem] mt-0.5">
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
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-6px); }
  20%, 40%, 60%, 80% { transform: translateX(6px); }
}

.shake-anim {
  animation: shake 0.4s ease-in-out;
}
</style>
