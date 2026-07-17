<script lang="ts">
import type { ImportedFileInfo } from '../../services/api';

// What the parent needs to materialize a ticked file into the batch: files
// uploaded this session carry their bytes, history entries are downloaded by id.
export interface SelectedImportFile {
  filename: string;
  localFile: File | null;
  stored: ImportedFileInfo | null;
}
</script>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { FileClock, Loader, Trash2, Upload } from '@lucide/vue';
import { api } from '../../services/api';
import { useNotifications } from '../../composables/useNotifications';
import DynamicComponent from '../DynamicComponent.vue';

interface SelectorEntry extends SelectedImportFile {
  // Loaded during this wizard session (has bytes in memory) — shown as "New".
  isNew: boolean;
  checked: boolean;
}

const props = defineProps<{
  // Filenames already in the wizard batch: pre-ticked when the selector reopens.
  preselectedNames?: string[];
  // In-memory File objects of the current batch, so confirming them again
  // never re-downloads and files whose storage failed stay selectable.
  sessionFiles?: File[];
  // Parent is materializing a confirmed selection.
  busy?: boolean;
  showBack?: boolean;
}>();

const emit = defineEmits<{
  (e: 'confirm', selection: SelectedImportFile[]): void;
  (e: 'back'): void;
}>();

const { notifyWarning } = useNotifications();

const entries = ref<SelectorEntry[]>([]);
const isLoading = ref(true);
const loadError = ref('');
const isStoring = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

onMounted(async () => {
  const sessionByName = new Map((props.sessionFiles || []).map(f => [f.name, f]));
  const preselected = new Set(props.preselectedNames || []);
  let stored: ImportedFileInfo[] = [];
  try {
    stored = await api.getImportedFiles();
  } catch (err: any) {
    loadError.value = err.message || 'Failed to load previously imported files.';
  } finally {
    isLoading.value = false;
  }
  entries.value = stored.map(f => ({
    filename: f.filename,
    stored: f,
    localFile: sessionByName.get(f.filename) ?? null,
    isNew: sessionByName.has(f.filename),
    checked: preselected.has(f.filename),
  }));
  // Batch files missing from storage (e.g. the store call failed on load) are
  // still selectable through their in-memory bytes. Prepend in batch order:
  // list order is selection order, and batch order decides which file anchors
  // the merge and gets credited with cross-file duplicate rows.
  const known = new Set(entries.value.map(e => e.filename));
  const sessionOnly = (props.sessionFiles || [])
    .filter(file => !known.has(file.name))
    .map(file => ({
      filename: file.name,
      stored: null,
      localFile: file,
      isNew: true,
      checked: preselected.has(file.name),
    }));
  if (sessionOnly.length) entries.value = [...sessionOnly, ...entries.value];
});

// Uploading adds to the list (stored right away, server-side deduplicated),
// ticked and flagged as new — it doesn't start the wizard by itself.
const onFilesPicked = async (e: Event) => {
  const target = e.target as HTMLInputElement;
  const files = target.files ? Array.from(target.files) : [];
  target.value = '';
  if (!files.length) return;
  isStoring.value = true;
  let infos: ImportedFileInfo[] = [];
  try {
    infos = await api.storeImportedFiles(files);
  } catch (err: any) {
    console.warn('Failed to store loaded files:', err);
    notifyWarning('Files not stored for later re-import', {
      message: err.message || 'The loaded files could not be saved to storage. Importing them still works.',
    });
  } finally {
    isStoring.value = false;
  }
  // Prepend unknown files preserving the picked order (see the note above on
  // why list order matters); known filenames merge into their existing row.
  const added: SelectorEntry[] = [];
  files.forEach(file => {
    const stored = infos.find(i => i.filename === file.name) ?? null;
    const existing = entries.value.find(en => en.filename === file.name);
    if (existing) {
      existing.localFile = file;
      // Keep the listing record (it carries transaction_count); only adopt the
      // store response when the file wasn't known yet.
      existing.stored = existing.stored ?? stored;
      existing.isNew = true;
      existing.checked = true;
    } else {
      added.push({ filename: file.name, stored, localFile: file, isNew: true, checked: true });
    }
  });
  if (added.length) entries.value = [...added, ...entries.value];
};

const selectedEntries = computed(() => entries.value.filter(e => e.checked));

const confirmSelection = () => {
  emit('confirm', selectedEntries.value.map(({ filename, localFile, stored }) => ({ filename, localFile, stored })));
};

// Deleting removes only the stored copy; the imported transactions stay.
const fileToDelete = ref<SelectorEntry | null>(null);
const isDeleting = ref(false);
const actionError = ref('');

const confirmDelete = async () => {
  if (!fileToDelete.value?.stored) return;
  isDeleting.value = true;
  actionError.value = '';
  try {
    await api.deleteImportedFile(fileToDelete.value.stored.id);
    entries.value = entries.value.filter(e => e.filename !== fileToDelete.value!.filename);
  } catch (err: any) {
    actionError.value = err.message || 'Failed to delete the stored file.';
  } finally {
    isDeleting.value = false;
    fileToDelete.value = null;
  }
};

const formatSize = (bytes: number) => `${(bytes / 1024).toFixed(1)} KB`;

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
</script>

<template>
  <div class="flex flex-col gap-4" data-testid="import-file-selector">
    <div
      class="flex flex-col items-center gap-2 border border-dashed border-border-color rounded-sm py-6 px-4 cursor-pointer hover:bg-bg-tertiary"
      data-testid="import-file-dropzone"
      @click="fileInput?.click()"
    >
      <Loader v-if="isStoring" class="w-6 h-6 text-accent animate-spin" />
      <Upload v-else class="w-6 h-6 text-accent" />
      <span class="text-sm font-semibold">Choose CSV file(s) to load</span>
      <span class="text-xs text-text-secondary">Loaded files join the list below, ticked — tick any mix of new and previously loaded files to import them as one deduplicated batch</span>
      <input
        type="file"
        ref="fileInput"
        accept=".csv"
        multiple
        style="display: none;"
        @change="onFilesPicked"
      />
    </div>

    <div v-if="isLoading" class="flex items-center gap-2 text-sm text-text-secondary py-2">
      <Loader class="w-4 h-4 animate-spin" />
      Loading previously imported files...
    </div>
    <div v-else-if="loadError" class="text-sm text-danger-color py-1">{{ loadError }}</div>

    <div v-if="entries.length" data-testid="import-file-list">
      <div class="flex items-center gap-2 mb-2">
        <FileClock class="w-4 h-4 text-accent" />
        <span class="text-sm font-semibold">Loaded files</span>
        <span class="text-xs text-text-secondary">— every loaded file is kept here, imported or not; already imported rows are skipped automatically</span>
      </div>
      <div class="border border-border-color rounded-sm divide-y divide-border-color max-h-72 overflow-y-auto">
        <!-- Different stored files can share a filename (e.g. leftovers of the
             same export) — key by stored id so rows never collide. -->
        <div
          v-for="entry in entries"
          :key="entry.stored ? `stored-${entry.stored.id}` : `local-${entry.filename}`"
          class="flex items-center justify-between gap-3 py-2 px-3 bg-bg-primary cursor-pointer hover:bg-bg-tertiary"
          :data-testid="`import-file-row-${entry.filename}`"
          @click="entry.checked = !entry.checked"
        >
          <div class="flex items-center gap-2.5 min-w-0">
            <input
              type="checkbox"
              class="w-4 h-4 cursor-pointer shrink-0"
              :checked="entry.checked"
              :disabled="busy"
              @click.stop="entry.checked = !entry.checked"
            />
            <div class="min-w-0">
              <div class="flex items-center gap-2 min-w-0">
                <span class="text-[0.9rem] font-semibold truncate">{{ entry.filename }}</span>
                <span
                  v-if="entry.isNew"
                  class="text-[0.65rem] font-semibold uppercase px-1.5 py-0.5 rounded-sm bg-accent-light text-accent shrink-0"
                >New</span>
                <span
                  v-if="entry.stored?.last_imported_at"
                  class="text-[0.65rem] font-semibold uppercase px-1.5 py-0.5 rounded-sm bg-emerald-50 text-emerald-600 shrink-0"
                >Imported</span>
                <span
                  v-else
                  class="text-[0.65rem] font-semibold uppercase px-1.5 py-0.5 rounded-sm bg-amber-50 text-amber-600 shrink-0"
                >Not imported</span>
              </div>
              <div class="text-xs text-text-secondary">
                <template v-if="entry.stored?.last_imported_at">
                  {{ formatSize(entry.stored.size_bytes) }} · last imported {{ formatDate(entry.stored.last_imported_at) }}
                  · {{ entry.stored.transaction_count }} transaction{{ entry.stored.transaction_count === 1 ? '' : 's' }}
                </template>
                <template v-else-if="entry.stored">
                  {{ formatSize(entry.stored.size_bytes) }} · loaded {{ formatDate(entry.stored.created_at) }} · transactions not imported yet
                </template>
                <template v-else-if="entry.localFile">
                  {{ formatSize(entry.localFile.size) }} · loaded this session only (not stored)
                </template>
              </div>
            </div>
          </div>
          <button
            v-if="entry.stored"
            class="bg-transparent border-none text-danger-color cursor-pointer p-1.5 rounded-sm hover:bg-bg-tertiary shrink-0"
            title="Delete stored file"
            :disabled="busy || isDeleting"
            @click.stop="fileToDelete = entry"
          >
            <Trash2 class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      <div v-if="actionError" class="text-sm text-danger-color pt-2">{{ actionError }}</div>
    </div>

    <div v-else-if="!isLoading" class="text-xs text-text-secondary">
      No previously imported files yet — every file you load is stored so you can re-import it later.
    </div>

    <div class="flex items-center gap-2">
      <button
        class="btn btn-sm btn-primary"
        data-testid="continue-with-files"
        :disabled="busy || isStoring || !selectedEntries.length"
        @click="confirmSelection"
      >
        <Loader v-if="busy" class="w-3.5 h-3.5 animate-spin" />
        Continue with {{ selectedEntries.length }} file{{ selectedEntries.length === 1 ? '' : 's' }}
      </button>
      <button v-if="showBack" class="btn btn-sm" :disabled="busy" @click="emit('back')">Back to mapping</button>
    </div>
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
