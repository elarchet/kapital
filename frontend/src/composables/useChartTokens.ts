import { computed, type ComputedRef } from 'vue';
import { usePreferencesStore } from '../store/preferences';

export interface ChartTokens {
  textPrimary: string;
  textSecondary: string;
  textTertiary: string;
  bgSecondary: string;
  bgTertiary: string;
  border: string;
  accent: string;
  success: string;
  danger: string;
}

const read = (name: string): string =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/**
 * Live CSS design tokens for chart styling. Recomputed whenever the runtime
 * theme class changes so charts re-color with the rest of the UI.
 */
export function useChartTokens(): ComputedRef<ChartTokens> {
  const preferences = usePreferencesStore();
  return computed<ChartTokens>(() => {
    // Touch the theme so the computed re-evaluates on runtime theme switches.
    void preferences.theme;
    return {
      textPrimary: read('--text-primary'),
      textSecondary: read('--text-secondary'),
      textTertiary: read('--text-tertiary'),
      bgSecondary: read('--bg-secondary'),
      bgTertiary: read('--bg-tertiary'),
      border: read('--border-color'),
      accent: read('--accent-color'),
      success: read('--color-success'),
      danger: read('--color-danger'),
    };
  });
}
