<script setup lang="ts">
import { ref } from 'vue';
import { api } from '../../services/api';
import { Upload, X, File } from '@lucide/vue';

const props = defineProps<{
  isOpen: boolean;
  componentKey: string;
  componentName: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'uploaded', newVariant: any): void;
}>();

const newVariantName = ref('');
const newVariantDesc = ref('');
const newVariantAssetUrl = ref('');
const uploadMode = ref<'file' | 'url'>('file');
const selectedFile = ref<File | null>(null);
const isDragActive = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const isSubmitting = ref(false);
const errorMessage = ref('');

const onDragOver = () => { isDragActive.value = true; };
const onDragLeave = () => { isDragActive.value = false; };
const onDrop = (e: DragEvent) => {
  isDragActive.value = false;
  errorMessage.value = '';
  const file = e.dataTransfer?.files?.[0];
  if (file && file.name.endsWith('.js')) {
    selectedFile.value = file;
  } else if (file) {
    errorMessage.value = 'Only .js files (compiled ESM bundles) are allowed.';
  }
};
const triggerFileInput = () => {
  errorMessage.value = '';
  fileInput.value?.click();
};
const onFileChange = (e: Event) => {
  errorMessage.value = '';
  const file = (e.target as HTMLInputElement).files?.[0];
  if (file && file.name.endsWith('.js')) {
    selectedFile.value = file;
  } else if (file) {
    errorMessage.value = 'Only .js files (compiled ESM bundles) are allowed.';
  }
};
const removeSelectedFile = () => {
  selectedFile.value = null;
  errorMessage.value = '';
  if (fileInput.value) fileInput.value.value = '';
};
const formatBytes = (bytes: number) => {
  if (!bytes) return '0 Bytes';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${['Bytes', 'KB', 'MB', 'GB'][i]}`;
};

const registerVariant = async () => {
  if (!newVariantName.value.trim()) return;
  isSubmitting.value = true;
  errorMessage.value = '';
  try {
    let newVar;
    if (uploadMode.value === 'file') {
      if (!selectedFile.value) return;
      newVar = await api.uploadComponentVariant(
        props.componentKey,
        newVariantName.value.trim(),
        newVariantDesc.value.trim() || null,
        selectedFile.value
      );
    } else {
      if (!newVariantAssetUrl.value.trim()) return;
      newVar = await api.createComponentVariant({
        component_key: props.componentKey,
        name: newVariantName.value.trim(),
        description: newVariantDesc.value.trim(),
        asset_url: newVariantAssetUrl.value.trim()
      });
    }
    emit('uploaded', newVar);
    // Reset form
    newVariantName.value = '';
    newVariantDesc.value = '';
    newVariantAssetUrl.value = '';
    selectedFile.value = null;
    errorMessage.value = '';
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to register variant.';
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div v-if="isOpen" class="modal-overlay flex items-center justify-center z-[100]">
    <div class="modal-card w-full max-w-md mx-4">
      <div class="modal-header border-b border-border-color pb-4 flex justify-between items-center">
        <h3 class="text-lg font-semibold text-text-primary">Upload Custom Extension</h3>
        <button @click="$emit('close')" class="text-2xl text-text-secondary hover:text-text-primary">&times;</button>
      </div>

      <div class="modal-body flex flex-col gap-4">
        <!-- Error Alert -->
        <div v-if="errorMessage" class="login-error flex justify-between items-center" style="margin-bottom: 0.5rem;">
          <span>{{ errorMessage }}</span>
          <button @click="errorMessage = ''" class="bg-transparent border-0 font-bold text-danger-color cursor-pointer text-sm">&times;</button>
        </div>

        <!-- Toggle Tabs -->
        <div class="flex border-b border-border-color pb-1">
          <button
            @click="uploadMode = 'file'"
            class="pb-2 text-sm font-semibold border-b-2 px-4 transition-all -mb-px cursor-pointer"
            :class="[
              uploadMode === 'file'
                ? 'border-accent text-accent font-semibold'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            ]"
          >
            Upload ESM File
          </button>
          <button
            @click="uploadMode = 'url'"
            class="pb-2 text-sm font-semibold border-b-2 px-4 transition-all -mb-px cursor-pointer"
            :class="[
              uploadMode === 'url'
                ? 'border-accent text-accent font-semibold'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            ]"
          >
            Remote URL
          </button>
        </div>

        <div class="form-group flex flex-col gap-1">
          <label for="variantName" class="text-xs font-semibold text-text-secondary">Name</label>
          <input
            v-model="newVariantName"
            type="text"
            id="variantName"
            class="form-control"
            placeholder="e.g. Glassmorphic Sidebar Variant"
            required
          />
        </div>

        <div class="form-group flex flex-col gap-1">
          <label for="variantDesc" class="text-xs font-semibold text-text-secondary">Description</label>
          <textarea
            v-model="newVariantDesc"
            id="variantDesc"
            class="form-control"
            placeholder="Brief details about the extension design"
            rows="2"
          ></textarea>
        </div>

        <!-- Drag and Drop Zone for File Upload -->
        <div v-if="uploadMode === 'file'" class="flex flex-col gap-2">
          <label class="text-xs font-semibold text-text-secondary">ESM Bundle File</label>
          
          <div
            v-if="!selectedFile"
            @dragover.prevent="onDragOver"
            @dragenter.prevent="onDragOver"
            @dragleave.prevent="onDragLeave"
            @drop.prevent="onDrop"
            @click="triggerFileInput"
            class="group relative border border-dashed rounded-md p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200"
            :class="[
              isDragActive
                ? 'border-accent bg-accent-light text-accent scale-[0.99] shadow-sm'
                : 'border-border-color hover:border-accent hover:bg-bg-tertiary text-text-secondary'
            ]"
          >
            <input
              ref="fileInput"
              type="file"
              accept=".js"
              class="hidden"
              @change="onFileChange"
            />
            <Upload
              class="w-8 h-8 mb-2 transition-transform duration-200"
              :class="[isDragActive ? 'scale-110 text-accent' : 'text-text-tertiary group-hover:text-accent group-hover:scale-105']"
            />
            <p class="text-xs font-medium text-text-primary mb-1">
              Drag & drop compiled ESM bundle (.js) here, or <span class="text-accent underline">click to browse</span>
            </p>
            <p class="text-[10px] text-text-tertiary">
              Supports only compiled ES Modules (.js)
            </p>
          </div>

          <!-- Selected File Display -->
          <div
            v-else
            class="flex items-center justify-between p-3 border border-border-color rounded-md bg-bg-tertiary transition-all duration-150"
          >
            <div class="flex items-center gap-3 w-4/5">
              <File class="w-6 h-6 text-accent shrink-0" />
              <div class="flex flex-col min-w-0">
                <span class="text-xs font-semibold text-text-primary truncate" :title="selectedFile.name">
                  {{ selectedFile.name }}
                </span>
                <span class="text-[10px] text-text-tertiary">
                  {{ formatBytes(selectedFile.size) }}
                </span>
              </div>
            </div>
            <button
              type="button"
              @click="removeSelectedFile"
              class="p-1 text-text-secondary hover:text-danger-color hover:bg-danger-light rounded transition-colors cursor-pointer"
              title="Remove file"
            >
              <X class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Remote URL Input -->
        <div v-else class="form-group flex flex-col gap-1">
          <label for="variantAssetUrl" class="text-xs font-semibold text-text-secondary">Asset URL (HTTPS compiled ESM bundle)</label>
          <input
            v-model="newVariantAssetUrl"
            type="url"
            id="variantAssetUrl"
            class="form-control font-mono text-xs"
            placeholder="https://cdn.example.com/variants/sidebar.js"
            required
          />
        </div>
      </div>

      <div class="modal-footer border-t border-border-color pt-4 flex gap-2 justify-end">
        <button @click="$emit('close')" class="btn btn-sm border border-border-color">Cancel</button>
        <button
          @click="registerVariant"
          class="btn btn-sm btn-primary cursor-pointer"
          :disabled="isSubmitting || !newVariantName.trim() || (uploadMode === 'file' ? !selectedFile : !newVariantAssetUrl.trim())"
        >
          {{ isSubmitting ? 'Registering...' : 'Register Extension' }}
        </button>
      </div>
    </div>
  </div>
</template>
