<script setup lang="ts">
import { GripVertical, Check } from '@lucide/vue';

defineProps<{
  colId: string;
  name: string;
  exampleValue?: string;
  used: boolean;
  armed: boolean;
}>();

const emit = defineEmits<{
  (e: 'dragstart', payload: DragEvent): void;
  (e: 'dragend'): void;
  (e: 'arm'): void;
}>();
</script>

<template>
  <button
    type="button"
    draggable="true"
    :data-testid="`csv-chip-${name}`"
    class="group flex items-center gap-1.5 py-1 px-2 rounded-md border text-left cursor-grab active:cursor-grabbing select-none transition-colors max-w-[180px]"
    :class="[
      armed
        ? 'border-accent ring-2 ring-accent/30 bg-accent-light'
        : used
          ? 'border-border-color bg-bg-tertiary opacity-55 hover:opacity-80'
          : 'border-border-color bg-bg-primary hover:border-accent/60 hover:bg-accent-light/50'
    ]"
    :title="armed ? 'Click a field slot to place, Escape to cancel' : `Drag onto a field, or click to select “${name}”`"
    @dragstart="emit('dragstart', $event)"
    @dragend="emit('dragend')"
    @click="emit('arm')"
  >
    <GripVertical class="w-3 h-3 shrink-0 text-text-tertiary group-hover:text-accent" />
    <span class="min-w-0">
      <span class="block text-[0.72rem] font-semibold truncate">{{ name }}</span>
      <span class="block text-[0.65rem] text-text-secondary font-mono truncate">{{ exampleValue?.trim() || '—' }}</span>
    </span>
    <Check v-if="used" class="w-3 h-3 shrink-0 text-success-color" />
  </button>
</template>
