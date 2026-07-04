<script setup lang="ts">
import DashboardView from '../views/DashboardView.vue';

definePage({
  name: 'dashboard',
  meta: { requiresAuth: true },
});
</script>

<template>
  <DashboardView />
</template>
