import { defineStore } from 'pinia';
import { api } from '../services/api';

export interface ComponentOverride {
  id: number;
  component_key: string;
  name: string;
  asset_url: string;
}

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
    overrides: {} as Record<string, ComponentOverride | null>,
    loading: false,
    error: null as string | null,
  }),

  getters: {
    getComponentOverride(state) {
      return (key: string) => state.overrides[key] || null;
    },
  },

  actions: {
    async fetchPreferences() {
      this.loading = true;
      this.error = null;
      try {
        const data = await api.getUserPreferences();
        this.theme = data.theme || 'slate-light';

        const overridesMap: Record<string, ComponentOverride | null> = {};
        if (data.overrides) {
          Object.entries(data.overrides).forEach(([key, val]) => {
            overridesMap[key] = val as ComponentOverride;
          });
        }
        this.overrides = overridesMap;
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

    async setComponentOverride(componentKey: string, variantId: number) {
      this.loading = true;
      this.error = null;
      try {
        const variant = await api.setComponentOverride(componentKey, variantId);
        this.overrides[componentKey] = variant;
      } catch (err: any) {
        this.error = err.message || `Failed to set override for ${componentKey}`;
        throw err;
      } finally {
        this.loading = false;
      }
    },

    async revertComponentToDefault(componentKey: string) {
      this.loading = true;
      this.error = null;
      try {
        await api.revertComponentOverride(componentKey);
        this.overrides[componentKey] = null;
      } catch (err: any) {
        this.error = err.message || `Failed to revert ${componentKey} to default`;
        throw err;
      } finally {
        this.loading = false;
      }
    },
  },
});
