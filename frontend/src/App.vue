<script setup lang="ts">
import { onMounted } from 'vue';
import { api } from './services/api';
import { usePreferencesStore } from './store/preferences';

onMounted(async () => {
  if (api.isAuthenticated()) {
    const preferencesStore = usePreferencesStore();
    await preferencesStore.fetchPreferences();
  }
});
</script>

<template>
  <router-view />
</template>


