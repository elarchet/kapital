<script setup lang="ts">
import DynamicComponent from '../../DynamicComponent.vue';

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
  <DynamicComponent
    componentKey="base-confirm-modal"
    :show="show"
    title="Delete Template?"
    :message="`Are you sure you want to delete the template '${templateName}'? This action will permanently erase this template configuration and cannot be undone.`"
    confirmText="Delete Template"
    cancelText="Cancel"
    variant="danger"
    defaultAction="cancel"
    @cancel="$emit('cancel')"
    @confirm="$emit('confirm')"
  />
</template>
