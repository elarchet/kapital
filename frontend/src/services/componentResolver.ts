import { shallowReactive, watch, markRaw, type Component } from 'vue';
import { usePreferencesStore } from '../store/preferences';

import DefaultSidebar from '../components/defaults/DefaultSidebar.vue';
import DefaultCustomDropdown from '../components/defaults/DefaultCustomDropdown.vue';
import DefaultBaseConfirmModal from '../components/defaults/DefaultBaseConfirmModal.vue';
import DefaultAddPositionButton from '../components/defaults/DefaultAddPositionButton.vue';
import DefaultCreatePositionModal from '../components/defaults/DefaultCreatePositionModal.vue';
import DefaultRightPanelDrawer from '../components/defaults/DefaultRightPanelDrawer.vue';

// Hardcoded map of local built-in fallback components from the defaults directory
const defaultComponents: Record<string, Component> = {
  'sidebar': DefaultSidebar,
  'custom-dropdown': DefaultCustomDropdown,
  'base-confirm-modal': DefaultBaseConfirmModal,
  'add-position-button': DefaultAddPositionButton,
  'create-position-modal': DefaultCreatePositionModal,
  'right-panel-drawer': DefaultRightPanelDrawer,
};

export const resolvedComponents = shallowReactive<Record<string, Component>>({
  'sidebar': markRaw(DefaultSidebar),
  'custom-dropdown': markRaw(DefaultCustomDropdown),
  'base-confirm-modal': markRaw(DefaultBaseConfirmModal),
  'add-position-button': markRaw(DefaultAddPositionButton),
  'create-position-modal': markRaw(DefaultCreatePositionModal),
  'right-panel-drawer': markRaw(DefaultRightPanelDrawer),
});

const loadedAssetUrls: Record<string, string | null> = {
  'sidebar': null,
  'custom-dropdown': null,
  'base-confirm-modal': null,
  'add-position-button': null,
  'create-position-modal': null,
  'right-panel-drawer': null,
};

/**
 * Loads a single component key (either its custom override or built-in default fallback).
 * Once successfully resolved, updates the reactive resolvedComponents registry.
 */
export async function loadComponent(key: string): Promise<void> {
  const preferencesStore = usePreferencesStore();
  const override = preferencesStore.getComponentOverride(key);
  const assetUrl = override?.asset_url || null;
  loadedAssetUrls[key] = assetUrl;

  let component: Component | null = null;
  if (assetUrl) {
    try {
      component = await loadSandboxedAsset(assetUrl);
    } catch (error) {
      console.error(`Error loading custom variant for "${key}". Reverting to default fallback.`, error);
    }
  }

  if (!component) {
    // Default fallback
    const defaultComp = defaultComponents[key];
    if (!defaultComp) {
      throw new Error(`Default component for key "${key}" is not registered.`);
    }
    component = defaultComp;
  }

  resolvedComponents[key] = markRaw(component);
}

let isWatching = false;

/**
 * Eagerly preloads both the default components and active custom overrides.
 * Also monitors preference overrides to dynamically hot-reload modified components.
 */
export async function preloadComponents(): Promise<void> {
  const preferencesStore = usePreferencesStore();
  
  // Only trigger loadComponent for components that actually have custom overrides configured
  const promises = Object.keys(defaultComponents).map(async (key) => {
    const override = preferencesStore.getComponentOverride(key);
    const assetUrl = override?.asset_url || null;
    
    // Set the initial asset URL in loadedAssetUrls to prevent unnecessary re-loading in watch
    loadedAssetUrls[key] = assetUrl;

    if (assetUrl) {
      try {
        await loadComponent(key);
      } catch (err) {
        console.error(`Failed to preload custom component "${key}":`, err);
      }
    }
  });

  await Promise.all(promises);

  // Set up deep watcher on preferencesStore.overrides to handle future updates dynamically
  if (!isWatching) {
    isWatching = true;
    watch(
      () => preferencesStore.overrides,
      async (newOverrides) => {
        for (const key of Object.keys(defaultComponents)) {
          const currentAssetUrl = newOverrides[key]?.asset_url || null;
          if (currentAssetUrl !== loadedAssetUrls[key]) {
            await loadComponent(key);
          }
        }
      },
      { deep: true }
    );
  }
}

// Configured whitelist of trusted hostnames for component bundle assets
const trustedHostnames = ['localhost', '127.0.0.1', 'cdn.kapital-platform.com', 'sandbox-assets.kapital.app'];
if (typeof window !== 'undefined') {
  trustedHostnames.push(window.location.hostname);
}

/**
 * Performs isolation checks and dynamically imports an ESM module.
 */
async function loadSandboxedAsset(url: string): Promise<Component> {
  const parsedUrl = new URL(url);

  // Restrict to secure https or localhost development
  if (parsedUrl.protocol !== 'https:' && parsedUrl.hostname !== 'localhost' && parsedUrl.hostname !== '127.0.0.1') {
    throw new Error('Insecure asset URL protocol');
  }

  // Validate host against trusted domain whitelist
  const isTrusted = trustedHostnames.some(domain =>
    parsedUrl.hostname === domain || parsedUrl.hostname.endsWith('.' + domain)
  );

  if (!isTrusted) {
    throw new Error(`Component asset domain "${parsedUrl.hostname}" is untrusted.`);
  }

  // Load compiled ESM Vue bundle dynamically
  const module = await import(/* @vite-ignore */ url);
  return module.default || module;
}
