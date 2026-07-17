<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { FileClock, Loader, RotateCcw, Trash2 } from '@lucide/vue';
import { api, type ImportedFileInfo } from '../../services/api';
import DynamicComponent from '../DynamicComponent.vue';

const emit = defineEmits<{
  (e: 'select', file: ImportedFileInfo): void;
}>();

const files = ref<ImportedFileInfo[]>([]);
const isLoading = ref(true);
const loadError = ref('');
// Id of the file currently being downloaded for re-import, if any.
const downloadingId = ref<number | null>(null);

onMounted(async () => {
  try {
    files.value = await api.getImportedFiles();
  } catch (err: any) {
    loadError.value = err.message || 'Failed to load previously imported files.';
  } finally {
    isLoading.value = false;
  }
});

const selectFile = (file: ImportedFileInfo) => {
  if (downloadingId.value !== null) return;
  downloadingId.value = file.id;
  emit('select', file);
};

// Deleting removes only the stored copy; the imported transactions stay.
const fileToDelete = ref<ImportedFileInfo | null>(null);
const isDeleting = ref(false);
const actionError = ref('');

const confirmDelete = async () => {
  if (!fileToDelete.value) return;
  isDeleting.value = true;
  actionError.value = '';
  try {
    await api.deleteImportedFile(fileToDelete.value.id);
    files.value = files.value.filter(f => f.id !== fileToDelete.value!.id);
  } catch (err: any) {
    actionError.value = err.message || 'Failed to delete the stored file.';
  } finally {
    isDeleting.value = false;
    fileToDelete.value = null;
  }
};

defineExpose({
  // Lets the parent clear the per-row spinner when the download settles.
  clearDownloading: () => { downloadingId.value = null; },
});

const formatSize = (bytes: number) => `${(bytes / 1024).toFixed(1)} KB`;

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
</script>

<template>
  <div v-if="isLoading" class="flex items-center gap-2 text-sm text-text-secondary py-3">
    <Loader class="w-4 h-4 animate-spin" />
    Loading previously imported files...
  </div>

  <div v-else-if="loadError" class="text-sm text-danger-color py-2">{{ loadError }}</div>

  <div v-else-if="files.length" data-testid="previous-imports-list">
    <div class="flex items-center gap-2 mb-2">
      <FileClock class="w-4 h-4 text-accent" />
      <span class="text-sm font-semibold">Previously imported files</span>
      <span class="text-xs text-text-secondary">— re-import any of them; already imported rows are skipped automatically</span>
    </div>
    <div class="border border-border-color rounded-sm divide-y divide-border-color max-h-72 overflow-y-auto">
      <div
        v-for="file in files"
        :key="file.id"
        class="flex items-center justify-between gap-3 py-2 px-3 bg-bg-primary"
        :data-testid="`previous-import-row-${file.id}`"
      >
        <div class="min-w-0">
          <div class="text-[0.9rem] font-semibold truncate">{{ file.filename }}</div>
          <div class="text-xs text-text-secondary">
            {{ formatSize(file.size_bytes) }} · last imported {{ formatDate(file.last_imported_at) }}
            · {{ file.transaction_count }} transaction{{ file.transaction_count === 1 ? '' : 's' }}
          </div>
        </div>
        <div class="flex items-center gap-1.5 shrink-0">
          <button
            class="btn btn-sm"
            :disabled="downloadingId !== null || isDeleting"
            @click="selectFile(file)"
          >
            <Loader v-if="downloadingId === file.id" class="w-3.5 h-3.5 animate-spin" />
            <RotateCcw v-else class="w-3.5 h-3.5" />
            <span>Re-import</span>
          </button>
          <button
            class="bg-transparent border-none text-danger-color cursor-pointer p-1.5 rounded-sm hover:bg-bg-tertiary"
            title="Delete stored file"
            :disabled="downloadingId !== null || isDeleting"
            @click="fileToDelete = file"
          >
            <Trash2 class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
    <div v-if="actionError" class="text-sm text-danger-color pt-2">{{ actionError }}</div>
  </div>

  <div v-else class="text-xs text-text-secondary py-2">
    No previously imported files yet — every file you import is stored so you can re-import it later.
  </div>

  <DynamicComponent
    componentKey="base-confirm-modal"
    :show="fileToDelete !== null"
    title="Delete Stored File?"
    :message="`Delete the stored copy of '${fileToDelete?.filename}'? Transactions already imported from it are kept, but you won't be able to re-import this file or use it for future field re-mapping.`"
    confirmText="Delete File"
    cancelText="Cancel"
    variant="danger"
    defaultAction="cancel"
    @cancel="fileToDelete = null"
    @confirm="confirmDelete"
  />
</template>
