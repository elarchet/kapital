<script setup lang="ts">
import { onMounted } from 'vue';
import { usePreferencesStore } from '../store/preferences';
import DynamicComponent from '../components/DynamicComponent.vue';
import { Palette, Check } from '@lucide/vue';

const preferencesStore = usePreferencesStore();

const themes = [
  { key: 'slate-light', name: 'Slate Light', desc: 'Clean institutional light styling', bg: 'bg-[#f8fafc]', border: 'border-slate-200' },
  { key: 'slate-dark', name: 'Slate Dark', desc: 'Deep modern dark styling', bg: 'bg-[#0f172a]', border: 'border-slate-800' },
  { key: 'forest-mint', name: 'Forest Mint', desc: 'Sleek eco-inspired green themes', bg: 'bg-[#f0fdf4]', border: 'border-emerald-200' }
];

onMounted(async () => {
  await preferencesStore.fetchPreferences();
});

const handleThemeChange = async (themeKey: string) => {
  try {
    await preferencesStore.updateTheme(themeKey);
  } catch (err) {
    console.error('Failed to change theme', err);
  }
};
</script>

<template>
  <div class="app-container">
    <DynamicComponent componentKey="sidebar" />

    <main class="main-content">
      <header class="page-header">
        <div class="page-title-group">
          <h1>System Settings</h1>
          <p>Manage application preferences and style themes</p>
        </div>
      </header>

      <div class="p-6 max-w-2xl">
        <div class="card p-6 flex flex-col gap-6">
          <div class="flex items-center gap-3 border-b border-border-color pb-4">
            <Palette class="w-5 h-5 text-accent" />
            <h2 class="text-lg font-semibold text-text-primary">Appearance Theme</h2>
          </div>

          <div class="flex flex-col gap-4">
            <button
              v-for="t in themes"
              :key="t.key"
              @click="handleThemeChange(t.key)"
              class="theme-option-card flex items-center justify-between p-4 border rounded-md cursor-pointer transition-all text-left w-full"
              :class="[
                preferencesStore.theme === t.key
                  ? 'border-accent bg-accent-light shadow-sm'
                  : 'border-border-color hover:border-border-focus bg-bg-secondary'
              ]"
            >
              <div class="flex flex-col gap-1">
                <span class="font-medium text-text-primary">{{ t.name }}</span>
                <span class="text-xs text-text-secondary">{{ t.desc }}</span>
              </div>
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full border border-border-color" :class="t.bg"></div>
                <Check v-if="preferencesStore.theme === t.key" class="w-4 h-4 text-accent" />
              </div>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
