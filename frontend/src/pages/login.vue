<script setup lang="ts">
import LoginView from '../views/LoginView.vue';

definePage({
  name: 'login',
  meta: { requiresGuest: true },
});
</script>

<template>
  <LoginView />
</template>
