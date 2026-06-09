<script setup lang="ts">
import { watch, onBeforeUnmount } from 'vue';
import { X, CheckCircle, AlertCircle } from '@lucide/vue';

const props = defineProps<{
  show: boolean;
  dbOpType: string;
  stats?: {
    total: number;
    success: number;
    failed: number;
    errors: Array<{
      rowNum: number;
      fieldLabel: string;
      rawValue: string;
      errorMessage: string;
    }>;
  };
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const handleKeyDown = (e: KeyboardEvent) => {
  if (!props.show) return;
  if (e.key === 'Escape') {
    e.preventDefault();
    e.stopPropagation();
    emit('close');
  }
};

watch(() => props.show, (newVal) => {
  if (newVal) {
    window.addEventListener('keydown', handleKeyDown, true);
  } else {
    window.removeEventListener('keydown', handleKeyDown, true);
  }
}, { immediate: true });

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown, true);
});
</script>

<template>
  <div 
    v-if="show" 
    class="fixed inset-0 w-screen h-screen bg-slate-900/10 backdrop-blur-[1.5px] flex items-center justify-center z-[300] animate-[fadeIn_0.15s_ease-out_forwards]" 
    @click.self="emit('close')"
  >
    <div class="w-fit min-w-[420px] max-w-[90vw] md:max-w-[1000px] bg-bg-secondary border border-border-color rounded-md shadow-lg overflow-hidden flex flex-col max-h-[85vh] animate-[slideUp_0.15s_ease-out]">
      <!-- Header -->
      <div class="px-5 py-4 border-b border-border-color flex justify-between items-center bg-bg-primary">
        <div class="flex items-center gap-2">
          <span class="badge" :class="'badge-' + dbOpType" style="padding: 0.15rem 0.4rem; font-size: 0.7rem; text-transform: uppercase;">
            {{ dbOpType }}
          </span>
          <h4 class="text-base font-bold text-text-primary m-0" style="font-family: 'Outfit', sans-serif;">
            Simulation Verification Details
          </h4>
        </div>
        <button 
          @click="emit('close')" 
          type="button" 
          class="bg-transparent border-0 p-1 text-text-secondary hover:text-text-primary cursor-pointer flex items-center justify-center transition-colors"
          title="Close dialog"
        >
          <X style="width: 18px; height: 18px;" />
        </button>
      </div>

      <!-- Body -->
      <div class="p-5 flex-1 overflow-y-auto">
        <div v-if="stats" class="flex flex-col gap-4">
          <!-- Status Banner -->
          <div 
            class="flex items-center gap-3 p-3 rounded-md border"
            :class="stats.failed > 0 
              ? 'bg-red-50/10 border-red-500/20 text-rose-700 dark:text-rose-400' 
              : 'bg-emerald-50/10 border-emerald-500/20 text-emerald-700 dark:text-emerald-400'"
          >
            <component 
              :is="stats.failed > 0 ? AlertCircle : CheckCircle" 
              style="width: 20px; height: 20px; flex-shrink: 0;"
              :class="stats.failed > 0 ? 'text-red-500' : 'text-emerald-500'"
            />
            <div class="text-sm font-semibold">
              {{ stats.success }} / {{ stats.total }} rows successfully parsed & validated.
              <span v-if="stats.failed > 0" class="block text-xs font-normal mt-0.5 text-text-secondary">
                Found {{ stats.failed }} field validation errors that will block import.
              </span>
            </div>
          </div>

          <!-- Errors Table -->
          <div v-if="stats.failed > 0 && stats.errors.length > 0" class="flex flex-col gap-2">
            <div class="text-xs font-bold text-text-secondary uppercase tracking-wider">
              Validation Failures List
            </div>
            <div class="overflow-x-auto border border-border-color rounded-sm">
              <table class="preview-table m-0 min-w-full" style="font-size: 0.8rem;">
                <thead>
                  <tr class="bg-bg-tertiary">
                    <th class="text-center" style="width: 80px; padding: 0.5rem 0.75rem;">CSV Row</th>
                    <th style="width: 160px; max-width: 180px; padding: 0.5rem 0.75rem;">Database Field</th>
                    <th style="width: 130px; max-width: 150px; padding: 0.5rem 0.75rem;">Raw Value</th>
                    <th style="padding: 0.5rem 0.75rem;">Failure Reason</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(err, eIdx) in stats.errors" :key="eIdx">
                    <td class="font-bold text-center" style="padding: 0.5rem 0.75rem;">#{{ err.rowNum }}</td>
                    <td class="font-semibold text-text-primary truncate max-w-[160px]" style="padding: 0.5rem 0.75rem; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;" :title="err.fieldLabel">{{ err.fieldLabel }}</td>
                    <td class="font-mono bg-bg-secondary truncate max-w-[130px]" style="font-family: monospace; padding: 0.5rem 0.75rem; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;" :title="err.rawValue || '—'">
                      {{ err.rawValue || '—' }}
                    </td>
                    <td class="text-color-danger font-medium" style="color: var(--color-danger); padding: 0.5rem 0.75rem;">{{ err.errorMessage }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-6 text-sm text-text-secondary">
          No simulation verification stats available for "{{ dbOpType }}".
        </div>
      </div>

      <!-- Footer -->
      <div class="py-3 px-5 border-t border-border-color flex justify-end bg-bg-primary">
        <button @click="emit('close')" type="button" class="btn btn-sm">
          Close
        </button>
      </div>
    </div>
  </div>
</template>
