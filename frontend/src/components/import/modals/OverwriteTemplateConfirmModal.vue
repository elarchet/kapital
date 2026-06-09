<script setup lang="ts">
import BaseConfirmModal from '../../BaseConfirmModal.vue';

defineProps<{
  show: boolean;
  templateName: string;
}>();

defineEmits<{
  (e: 'cancel'): void;
  (e: 'confirm'): void;
}>();
</script>

<template>
  <BaseConfirmModal
    :show="show"
    title="Overwrite Existing Template?"
    :message="`A template named '${templateName}' already exists. Saving this will overwrite and erase the previous template configuration. Do you want to proceed?`"
    confirmText="Overwrite Template"
    cancelText="Keep Editing"
    variant="warning"
    defaultAction="cancel"
    @cancel="$emit('cancel')"
    @confirm="$emit('confirm')"
  />
</template>
