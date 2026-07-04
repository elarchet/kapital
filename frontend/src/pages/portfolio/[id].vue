<script setup lang="ts">
import PortfolioView from '../../views/PortfolioView.vue';

definePage({
  name: 'portfolio',
  meta: { requiresAuth: true },
});
</script>

<template>
  <PortfolioView />
</template>
