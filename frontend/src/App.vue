<script setup lang="ts">
import { onMounted } from 'vue';
import { api } from './services/api';
import { usePreferencesStore } from './store/preferences';
import { preloadComponents } from './services/componentResolver';

onMounted(async () => {
  if (api.isAuthenticated()) {
    const preferencesStore = usePreferencesStore();
    await preferencesStore.fetchPreferences();
    await preloadComponents();
  }
});
</script>

<template>
  <router-view />
</template>


