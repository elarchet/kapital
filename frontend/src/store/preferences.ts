import { defineStore } from 'pinia';
import { api } from '../services/api';

export function applyTheme(themeName: string) {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  // Clean prior theme- classes
  root.className = root.className.replace(/\btheme-\S+/g, '');
  root.classList.add(`theme-${themeName}`);
}

export const usePreferencesStore = defineStore('preferences', {
  state: () => ({
    theme: 'slate-light',
    loading: false,
    error: null as string | null,
  }),

  actions: {
    async fetchPreferences() {
      this.loading = true;
      this.error = null;
      try {
        const data = await api.getUserPreferences();
        this.theme = data.theme || 'slate-light';
        applyTheme(this.theme);
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch user preferences';
      } finally {
        this.loading = false;
      }
    },

    async updateTheme(newTheme: string) {
      this.loading = true;
      this.error = null;
      try {
        await api.updateUserTheme(newTheme);
        this.theme = newTheme;
        applyTheme(newTheme);
      } catch (err: any) {
        this.error = err.message || 'Failed to update theme';
        throw err;
      } finally {
        this.loading = false;
      }
    },
  },
});

