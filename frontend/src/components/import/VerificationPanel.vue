<script setup lang="ts">
import { ref } from 'vue';

defineProps<{
  activeDbOpTypes: string[];
  liveValidationStats: Record<string, {
    total: number;
    success: number;
    failed: number;
    errors: Array<{
      rowNum: number;
      fieldLabel: string;
      rawValue: string;
      errorMessage: string;
    }>;
  }>;
}>();

const expandedErrors = ref<Record<string, boolean>>({});

const toggleErrorView = (opType: string) => {
  expandedErrors.value[opType] = !expandedErrors.value[opType];
};
</script>

<template>
  <div style="margin-bottom: 1.5rem;">
    <h5 style="font-size: 0.8rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.75rem; letter-spacing: 0.05em;">
      Simulation Verification Panel
    </h5>

    <div style="display: flex; flex-direction: column; gap: 0.75rem;">
      <div v-for="type in activeDbOpTypes" :key="type" style="border: 1px solid var(--border-color); border-radius: var(--radius-sm); background-color: var(--bg-secondary); overflow: hidden;">
        <div style="padding: 0.75rem 1rem; display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-primary); border-bottom: 1px solid var(--border-color);">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="badge" :class="'badge-' + type" style="padding: 0.15rem 0.35rem; font-size: 0.65rem; text-transform: uppercase;">
              {{ type }}
            </span>
            <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-primary);">
              {{ liveValidationStats[type]?.success }} / {{ liveValidationStats[type]?.total }} Rows Passed
            </span>
          </div>
          <button 
            v-if="liveValidationStats[type]?.failed > 0"
            @click="toggleErrorView(type)" 
            class="btn btn-sm btn-danger"
            style="font-size: 0.7rem; padding: 0.15rem 0.4rem;"
          >
            {{ expandedErrors[type] ? 'Hide Errors' : 'Show ' + liveValidationStats[type].failed + ' Failures' }}
          </button>
          <span v-else style="font-size: 0.75rem; color: var(--color-success); font-weight: 600;">
            ✓ Verification Perfect
          </span>
        </div>

        <div v-if="expandedErrors[type] && liveValidationStats[type]?.errors.length > 0" style="padding: 1rem; border-top: 1px solid var(--border-color); max-height: 250px; overflow-y: auto;">
          <table class="preview-table" style="margin-top: 0; font-size: 0.7rem; width: 100%;">
            <thead>
              <tr style="background-color: var(--bg-tertiary);">
                <th style="width: 80px;">CSV Row</th>
                <th style="width: 150px;">Database Field</th>
                <th style="width: 120px;">Raw Value</th>
                <th>Failure Reason</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(err, eIdx) in liveValidationStats[type].errors" :key="eIdx">
                <td style="font-weight: bold; text-align: center;">#{{ err.rowNum }}</td>
                <td style="font-weight: 600; color: var(--text-primary);">{{ err.fieldLabel }}</td>
                <td style="font-family: monospace; background-color: var(--bg-primary); padding: 0.15rem 0.35rem;">{{ err.rawValue || '—' }}</td>
                <td style="color: var(--color-danger); font-weight: 500;">{{ err.errorMessage }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

