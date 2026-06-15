<script setup lang="ts">
import { Trash2, Plus } from '@lucide/vue';

defineProps<{
  isOpen: boolean;
  componentName: string;
  componentKey: string;
  variants: any[];
  loading: boolean;
  activeVariantId?: number | null;
}>();

defineEmits<{
  (e: 'close'): void;
  (e: 'select', variantId: number): void;
  (e: 'delete', variantId: number): void;
  (e: 'open-upload'): void;
}>();
</script>

<template>
  <div v-if="isOpen" class="modal-overlay flex items-center justify-center">
    <div class="modal-card w-full max-w-lg mx-4">
      <div class="modal-header border-b border-border-color pb-4 flex justify-between items-center">
        <div>
          <h3 class="text-lg font-semibold text-text-primary">Extensions for: {{ componentName }}</h3>
          <p class="text-xs text-text-secondary">Select a custom variant or register your own extension URL</p>
        </div>
        <button @click="$emit('close')" class="text-2xl text-text-secondary hover:text-text-primary">&times;</button>
      </div>

      <div class="modal-body py-4 flex flex-col gap-4 max-h-[350px] overflow-y-auto">
        <div v-if="loading" class="text-center py-6 text-text-secondary">
          Loading extensions list...
        </div>
        <div v-else-if="!variants.length" class="text-center py-6 text-text-secondary text-sm italic">
          No marketplace extensions available for this component.
        </div>
        <div v-else class="flex flex-col gap-3">
          <div
            v-for="variant in variants"
            :key="variant.id"
            class="variant-option-card flex items-center justify-between p-4 border border-border-color rounded bg-bg-tertiary"
          >
            <div class="flex flex-col gap-1 w-2/3">
              <span class="font-medium text-text-primary text-sm flex items-center gap-2">
                {{ variant.name }}
                <span v-if="variant.is_public" class="px-1.5 py-0.5 text-[9px] bg-accent-light text-accent rounded border border-accent/20">Public</span>
                <span v-else class="px-1.5 py-0.5 text-[9px] bg-bg-primary text-text-secondary rounded border border-border-color">Private</span>
              </span>
              <span class="text-xs text-text-secondary truncate">{{ variant.description }}</span>
              <span class="text-[10px] text-text-tertiary truncate font-mono">{{ variant.asset_url }}</span>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click="$emit('select', variant.id)"
                class="btn btn-sm btn-primary cursor-pointer"
                :disabled="activeVariantId === variant.id"
              >
                <span v-if="activeVariantId === variant.id">Active</span>
                <span v-else>Apply</span>
              </button>
              <button
                v-if="variant.user_id !== null"
                @click="$emit('delete', variant.id)"
                class="p-2 text-color-danger hover:bg-color-danger-light rounded"
                title="Delete Custom Extension"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer border-t border-border-color pt-4 flex gap-2 justify-between">
        <button
          @click="$emit('open-upload')"
          class="btn btn-sm btn-primary flex items-center gap-1 cursor-pointer"
        >
          <Plus class="w-4 h-4" />
          <span>Upload Extension</span>
        </button>
        <button @click="$emit('close')" class="btn btn-sm border border-border-color">Close</button>
      </div>
    </div>
  </div>
</template>
