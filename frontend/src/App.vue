<script setup lang="ts">
import { onMounted } from 'vue';
import { api } from './services/api';
import { usePreferencesStore } from './store/preferences';
import DynamicComponent from './components/DynamicComponent.vue';

onMounted(async () => {
  if (api.isAuthenticated()) {
    const preferencesStore = usePreferencesStore();
    await preferencesStore.fetchPreferences();
  }
});
</script>

<template>
  <router-view />
  <!-- Global toast stack; push toasts from anywhere via useNotifications(). -->
  <DynamicComponent componentKey="notification-toasts" />
</template>


