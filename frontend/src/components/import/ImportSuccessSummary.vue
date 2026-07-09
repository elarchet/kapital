<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  importSuccessSummary: {
    positions_created: number;
    raw_transactions_imported: number;
    allocations_created: number;
    skipped_duplicates: number;
    skipped_invalid: number;
    is_template_only?: boolean;
  };
  mappingTemplateName?: string;
}>();

const skippedTotal = computed(
  () => (props.importSuccessSummary.skipped_duplicates ?? 0) + (props.importSuccessSummary.skipped_invalid ?? 0),
);
</script>

<template>
  <div style="background-color: var(--color-success-light); border: 1px solid rgba(16, 185, 129, 0.2); padding: 1.5rem; border-radius: var(--radius-md); text-align: center; margin-bottom: 1rem;">
    <h4 style="color: var(--color-success); font-size: 1.1rem; margin-bottom: 0.5rem;">
      {{ importSuccessSummary.is_template_only ? 'Template Saved!' : 'Import Successful!' }}
    </h4>
    <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 1rem;">
      {{ importSuccessSummary.is_template_only ? `The configuration template "${mappingTemplateName}" has been successfully saved.` : 'Your transaction history has been successfully parsed and processed.' }}
    </p>
    <div v-if="!importSuccessSummary.is_template_only" style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1rem; background-color: var(--bg-secondary); padding: 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); max-width: 620px; margin: 0 auto;">
      <div>
        <div style="font-size: 0.75rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase;">Positions Created</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">{{ importSuccessSummary.positions_created }}</div>
      </div>
      <div>
        <div style="font-size: 0.75rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase;">Transactions Imported</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">{{ importSuccessSummary.raw_transactions_imported }}</div>
      </div>
      <div>
        <div style="font-size: 0.75rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase;">Allocations Created</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">{{ importSuccessSummary.allocations_created }}</div>
      </div>
      <div>
        <div style="font-size: 0.75rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase;">Skipped</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">{{ skippedTotal }}</div>
      </div>
    </div>
  </div>
</template>
