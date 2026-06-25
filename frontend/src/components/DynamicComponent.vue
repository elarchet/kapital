<script setup lang="ts">
import { computed } from 'vue';
import DefaultSidebar from './defaults/DefaultSidebar.vue';
import DefaultCustomDropdown from './defaults/DefaultCustomDropdown.vue';
import DefaultBaseConfirmModal from './defaults/DefaultBaseConfirmModal.vue';
import DefaultAddPositionButton from './defaults/DefaultAddPositionButton.vue';
import DefaultCreatePositionModal from './defaults/DefaultCreatePositionModal.vue';
import DefaultRightPanelDrawer from './defaults/DefaultRightPanelDrawer.vue';

const props = defineProps<{
  componentKey: string;
}>();

const componentMap: Record<string, any> = {
  'sidebar': DefaultSidebar,
  'custom-dropdown': DefaultCustomDropdown,
  'base-confirm-modal': DefaultBaseConfirmModal,
  'add-position-button': DefaultAddPositionButton,
  'create-position-modal': DefaultCreatePositionModal,
  'right-panel-drawer': DefaultRightPanelDrawer,
};

const component = computed(() => componentMap[props.componentKey]);
</script>

<template>
  <component :is="component" v-if="component" v-bind="$attrs">
    <template v-for="(_, slotName) in $slots" :key="slotName" #[slotName]="slotProps">
      <slot :name="slotName" v-bind="slotProps || {}" />
    </template>
  </component>
  <div v-else class="flex items-center justify-center p-2 text-sm text-text-muted">
    Component not found
  </div>
</template>

