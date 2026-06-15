<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useKapitalStore } from '../store';
import { usePreferencesStore } from '../store/preferences';
import { api } from '../services/api';
import { preloadComponents } from '../services/componentResolver';

const router = useRouter();
const store = useKapitalStore();
const preferencesStore = usePreferencesStore();

const email = ref('test@example.com'); // Pre-populate for convenience
const password = ref('password123');
const loading = ref(false);
const error = ref('');

const handleLogin = async () => {
  if (!email.value || !password.value) {
    error.value = 'Please enter both fields.';
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    await api.login(email.value, password.value);
    store.setAuthenticated(true, email.value);
    // Boot stores data fetch
    await Promise.all([
      store.fetchAllData(),
      preferencesStore.fetchPreferences()
    ]);
    await preloadComponents();
    router.push('/');
  } catch (err: any) {
    error.value = err.message || 'Authentication failed. Please verify credentials.';
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <main class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="logo-icon" style="width: 48px; height: 48px; font-size: 1.5rem; border-radius: var(--radius-md);">K</div>
        <h2>Welcome to Kapital</h2>
        <p>A secure portal for asset optimization</p>
      </div>

      <form @submit.prevent="handleLogin" style="display: flex; flex-direction: column;">
        <div v-if="error" class="login-error" style="margin-bottom: 1.25rem;">
          {{ error }}
        </div>

        <div class="form-group">
          <label for="email">Institutional Email</label>
          <input 
            v-model="email" 
            type="email" 
            id="email" 
            class="form-control" 
            placeholder="name@institution.com" 
            required 
            autocomplete="email"
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input 
            v-model="password" 
            type="password" 
            id="password" 
            class="form-control" 
            placeholder="••••••••" 
            required
            autocomplete="current-password"
          />
        </div>

        <button 
          type="submit" 
          class="btn btn-primary" 
          style="width: 100%; padding: 0.75rem; margin-top: 1rem;"
          :disabled="loading"
        >
          <span v-if="loading">Verifying security keys...</span>
          <span v-else>Access Platform</span>
        </button>
      </form>
    </div>
  </main>
</template>
