<script setup lang="ts">
import SettingsView from '../views/SettingsView.vue';

definePage({
  name: 'settings',
  meta: { requiresAuth: true },
});
</script>

<template>
  <SettingsView />
</template>
