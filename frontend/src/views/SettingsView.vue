<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { usePreferencesStore } from '../store/preferences';
import { api } from '../services/api';
import DynamicComponent from '../components/DynamicComponent.vue';
import {
  Palette,
  Cpu,
  RotateCcw,
  Check,
  Layers
} from '@lucide/vue';
import BrowseVariantsModal from '../components/settings/BrowseVariantsModal.vue';
import UploadVariantModal from '../components/settings/UploadVariantModal.vue';

const preferencesStore = usePreferencesStore();

const themes = [
  { key: 'slate-light', name: 'Slate Light', desc: 'Clean institutional light styling', bg: 'bg-[#f8fafc]', border: 'border-slate-200' },
  { key: 'slate-dark', name: 'Slate Dark', desc: 'Deep modern dark styling', bg: 'bg-[#0f172a]', border: 'border-slate-800' },
  { key: 'forest-mint', name: 'Forest Mint', desc: 'Sleek eco-inspired green themes', bg: 'bg-[#f0fdf4]', border: 'border-emerald-200' }
];

const configurableComponents = [
  { key: 'sidebar', name: 'Sidebar Nav', desc: 'Primary application sidebar navigation' },
  { key: 'custom-dropdown', name: 'Custom Dropdown', desc: 'Granular searchable option picker selector' },
  { key: 'base-confirm-modal', name: 'Confirm Modal', desc: 'System-wide critical operation validation modals' },
  { key: 'add-position-button', name: 'Add Position Button', desc: 'Dropdown action launcher button' },
  { key: 'create-position-modal', name: 'Create Position Modal', desc: 'Interactive asset registration wizard' },
  { key: 'right-panel-drawer', name: 'Details Drawer', desc: 'Slide-out asset analytics sidebar' }
];

const selectedComponent = ref<typeof configurableComponents[0] | null>(null);
const componentVariants = ref<any[]>([]);
const loadingVariants = ref(false);
const showCreateVariantModal = ref(false);

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

const openVariantsModal = async (comp: typeof configurableComponents[0]) => {
  selectedComponent.value = comp;
  loadingVariants.value = true;
  componentVariants.value = [];
  try {
    componentVariants.value = await api.getComponentVariants(comp.key);
  } catch (err) {
    console.error('Failed to load variants', err);
  } finally {
    loadingVariants.value = false;
  }
};

const closeVariantsModal = () => {
  selectedComponent.value = null;
};

// Dialog and alert states for unified premium components popups
const popupState = ref<{
  show: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info' | 'success';
  hideCancel?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
}>({
  show: false,
  title: '',
  message: '',
});

const triggerPopup = (config: Partial<typeof popupState.value>) => {
  popupState.value = {
    show: true,
    title: '',
    message: '',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    variant: 'danger',
    hideCancel: false,
    ...config,
  };
};

const handlePopupConfirm = () => {
  popupState.value.show = false;
  if (popupState.value.onConfirm) popupState.value.onConfirm();
};

const handlePopupCancel = () => {
  popupState.value.show = false;
  if (popupState.value.onCancel) popupState.value.onCancel();
};

const selectVariant = async (variantId: number) => {
  if (!selectedComponent.value) return;
  try {
    await preferencesStore.setComponentOverride(selectedComponent.value.key, variantId);
    closeVariantsModal();
  } catch (err) {
    triggerPopup({
      title: 'Override Failed',
      message: 'Failed to apply the custom component override variant.',
      confirmText: 'OK',
      variant: 'danger',
      hideCancel: true,
    });
  }
};

const revertToDefault = async (compKey: string) => {
  try {
    await preferencesStore.revertComponentToDefault(compKey);
  } catch (err) {
    triggerPopup({
      title: 'Revert Failed',
      message: 'Failed to revert the component to its default fallback.',
      confirmText: 'OK',
      variant: 'danger',
      hideCancel: true,
    });
  }
};

const handleUploaded = (newVar: any) => {
  componentVariants.value.push(newVar);
  showCreateVariantModal.value = false;
};

const variantToDelete = ref<number | null>(null);

const deleteVariant = (id: number) => {
  variantToDelete.value = id;
  triggerPopup({
    title: 'Delete Variant?',
    message: 'Are you sure you want to permanently delete this custom component variant extension?',
    confirmText: 'Delete Variant',
    cancelText: 'Cancel',
    variant: 'danger',
    onConfirm: async () => {
      if (variantToDelete.value === null) return;
      try {
        await api.deleteComponentVariant(variantToDelete.value);
        componentVariants.value = componentVariants.value.filter(v => v.id !== variantToDelete.value);
        if (selectedComponent.value) {
          const active = preferencesStore.getComponentOverride(selectedComponent.value.key);
          if (active && active.id === variantToDelete.value) {
            preferencesStore.overrides[selectedComponent.value.key] = null;
          }
        }
      } catch (err: any) {
        triggerPopup({
          title: 'Error Deleting Variant',
          message: err.message || 'An unexpected failure occurred while trying to delete this variant.',
          confirmText: 'OK',
          variant: 'danger',
          hideCancel: true,
        });
      } finally {
        variantToDelete.value = null;
      }
    }
  });
};
</script>

<template>
  <div class="app-container">
    <DynamicComponent componentKey="sidebar" />

    <main class="main-content">
      <header class="page-header">
        <div class="page-title-group">
          <h1>System Settings</h1>
          <p>Manage application preferences, style themes, and custom component marketplace overrides</p>
        </div>
      </header>

      <div class="settings-grid grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
        <div class="card lg:col-span-1 p-6 flex flex-col gap-6">
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

        <div class="card lg:col-span-2 p-6 flex flex-col gap-6">
          <div class="flex items-center gap-3 border-b border-border-color pb-4">
            <Cpu class="w-5 h-5 text-accent" />
            <h2 class="text-lg font-semibold text-text-primary">Granular UI Component Overrides</h2>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="comp in configurableComponents"
              :key="comp.key"
              class="component-config-card p-5 border border-border-color rounded-md bg-bg-secondary flex flex-col justify-between gap-4"
            >
              <div class="flex flex-col gap-1">
                <h3 class="font-medium text-text-primary text-base">{{ comp.name }}</h3>
                <p class="text-xs text-text-secondary">{{ comp.desc }}</p>
                <div class="mt-2 inline-flex items-center gap-2 px-2.5 py-1 rounded bg-bg-tertiary text-xs text-text-secondary border border-border-color self-start">
                  <span class="font-medium">Active:</span>
                  <span class="truncate max-w-[150px] font-semibold text-accent">
                    {{ preferencesStore.getComponentOverride(comp.key)?.name || 'Default (Built-in)' }}
                  </span>
                </div>
              </div>

              <div class="flex gap-2">
                <button
                  @click="openVariantsModal(comp)"
                  class="btn btn-sm btn-primary flex-1 flex items-center justify-center gap-1 cursor-pointer"
                >
                  <Layers class="w-3.5 h-3.5" />
                  <span>Choose Extension</span>
                </button>
                <button
                  v-if="preferencesStore.getComponentOverride(comp.key)"
                  @click="revertToDefault(comp.key)"
                  class="btn btn-sm flex items-center justify-center gap-1 border border-border-color hover:bg-bg-tertiary text-text-secondary cursor-pointer"
                  title="Revert to Default"
                >
                  <RotateCcw class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <BrowseVariantsModal
      :isOpen="!!selectedComponent"
      :componentName="selectedComponent?.name || ''"
      :componentKey="selectedComponent?.key || ''"
      :variants="componentVariants"
      :loading="loadingVariants"
      :activeVariantId="selectedComponent ? preferencesStore.getComponentOverride(selectedComponent.key)?.id : null"
      @close="closeVariantsModal"
      @select="selectVariant"
      @delete="deleteVariant"
      @open-upload="showCreateVariantModal = true"
    />

    <UploadVariantModal
      :isOpen="showCreateVariantModal"
      :componentKey="selectedComponent?.key || ''"
      :componentName="selectedComponent?.name || ''"
      @close="showCreateVariantModal = false"
      @uploaded="handleUploaded"
    />

    <!-- Unified Premium Modal / Alert Popup -->
    <DynamicComponent
      componentKey="base-confirm-modal"
      :show="popupState.show"
      :title="popupState.title"
      :message="popupState.message"
      :confirmText="popupState.confirmText"
      :cancelText="popupState.cancelText"
      :variant="popupState.variant"
      :hideCancel="popupState.hideCancel"
      @confirm="handlePopupConfirm"
      @cancel="handlePopupCancel"
    />
  </div>
</template>
