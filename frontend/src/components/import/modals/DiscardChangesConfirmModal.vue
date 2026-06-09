<script setup lang="ts">
import BaseConfirmModal from '../../BaseConfirmModal.vue';

withDefaults(defineProps<{
  show: boolean;
  title?: string;
  message?: string;
}>(), {
  title: 'Discard Unsaved Changes?',
  message: 'You have unsaved mapping configuration changes. Leaving now will discard these changes.'
});

defineEmits<{
  (e: 'cancel'): void;
  (e: 'confirm'): void;
}>();
</script>

<template>
  <BaseConfirmModal
    :show="show"
    :title="title"
    :message="message"
    confirmText="Discard Changes"
    cancelText="Keep Editing"
    variant="danger"
    defaultAction="confirm"
    @cancel="$emit('cancel')"
    @confirm="$emit('confirm')"
  />
</template>
