<script setup lang="ts">
import { computed } from 'vue';
import { resolvedComponents } from '../services/componentResolver';

const props = defineProps<{
  componentKey: string;
}>();

const component = computed(() => resolvedComponents[props.componentKey]);
</script>

<template>
  <component :is="component" v-if="component" v-bind="$attrs">
    <template v-for="(_, slotName) in $slots" :key="slotName" #[slotName]="slotProps">
      <slot :name="slotName" v-bind="slotProps || {}" />
    </template>
  </component>
  <div v-else class="flex items-center justify-center p-2 text-sm text-text-muted">
    Loading...
  </div>
</template>
