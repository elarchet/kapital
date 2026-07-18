import type { Ref } from 'vue';
import { api } from '../../services/api';
import { useNotifications } from '../../composables/useNotifications';
import {
  parseCsvText,
  mergeParsedCsvFiles,
  readFileText,
  type ParsedCsvFile
} from '../../services/import';

interface FileLoadingDeps {
  importFiles: Ref<File[]>;
  importFileHeaders: Ref<string[]>;
  allRawRows: Ref<string[][]>;
  rawRowSources: Ref<string[]>;
  uiColumns: Ref<Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean; width?: number }>>;
  columnConfigMap: Ref<Record<string, any>>;
  importDelimiter: Ref<string>;
  currentStep: Ref<number>;
  isCustomMapping: Ref<boolean>;
  importError: Ref<string>;
  autodetectedSchemaId: Ref<number | null>;
  selectedSchemaId: Ref<number | null>;
  initializeConfigs: () => void;
}

// Loading files into the wizard: initial batch load with schema autodetection,
// and growing a live batch (uploads and stored files mix freely).
export function useImportFileLoading(deps: FileLoadingDeps) {
  const { notifyWarning } = useNotifications();

  // Extend the current batch with the re-merged union without resetting the
  // mapping work: merge order is deterministic, so the previous headers come
  // back as a prefix of the new union and existing col-<idx> ids stay valid.
  const appendMergedBatch = (merged: { headers: string[]; rawRows: string[][]; rowSources: string[] }) => {
    const oldHeaders = deps.importFileHeaders.value;
    deps.allRawRows.value = merged.rawRows;
    deps.rawRowSources.value = merged.rowSources;
    deps.importFileHeaders.value = merged.headers;
    if (!oldHeaders.every((h, idx) => merged.headers[idx] === h)) {
      // Shouldn't happen; if the prefix invariant ever breaks, remap from scratch
      // rather than leave mappings pointing at the wrong columns.
      deps.initializeConfigs();
      return;
    }
    for (let idx = oldHeaders.length; idx < merged.headers.length; idx++) {
      const id = `col-${idx}`;
      deps.uiColumns.value.push({ id, colIdx: idx, name: merged.headers[idx], label: merged.headers[idx], width: 180 });
      if (!deps.columnConfigMap.value[id]) deps.columnConfigMap.value[id] = { typeSpecific: {} };
    }
    deps.uiColumns.value = [...deps.uiColumns.value];
    deps.columnConfigMap.value = { ...deps.columnConfigMap.value };
  };

  const processFiles = async (files: File[], opts: { alreadyStored?: boolean; append?: boolean } = {}) => {
    const appending = !!opts.append && deps.importFiles.value.length > 0;
    // When appending, drop files already in the batch (the backend dedups rows
    // anyway, but a doubled file in the list would only confuse).
    const newFiles = appending
      ? files.filter(f => !deps.importFiles.value.some(existing => existing.name === f.name))
      : files;
    if (!newFiles.length) return;
    deps.importError.value = '';

    const combined = appending ? [...deps.importFiles.value, ...newFiles] : newFiles;

    let merged: { delimiter: string; headers: string[]; rawRows: string[][]; rowSources: string[] };
    try {
      const parsedFiles: ParsedCsvFile[] = [];
      for (const file of combined) {
        const text = await readFileText(file);
        parsedFiles.push({ name: file.name, ...parseCsvText(text) });
      }
      merged = mergeParsedCsvFiles(parsedFiles);
    } catch (err: any) {
      // Mismatched files would silently misalign rows — refuse the whole batch
      // on initial load, or just the added files when appending.
      if (!appending) deps.importFiles.value = [];
      deps.importError.value = err.message || 'Failed to read the selected files.';
      return;
    }

    deps.importFiles.value = combined;

    // Persist the loaded files right away (deduplicated server-side), so they
    // are kept for later re-import even if this import never completes — e.g.
    // when the mapping template is still incomplete. Non-fatal on failure.
    if (!opts.alreadyStored) {
      api.storeImportedFiles(newFiles).catch((err: any) => {
        console.warn('Failed to store loaded files:', err);
        notifyWarning('Files not stored for later re-import', {
          message: err.message || 'The loaded files could not be saved to storage. Importing them still works.',
        });
      });
    }

    if (merged.headers.length > 0) {
      if (appending) {
        appendMergedBatch(merged);
        return;
      }
      deps.importDelimiter.value = merged.delimiter;
      deps.importFileHeaders.value = merged.headers;
      deps.initializeConfigs();
      deps.allRawRows.value = merged.rawRows;
      deps.rawRowSources.value = merged.rowSources;
      deps.currentStep.value = 1;

      try {
        const detectRes = await api.detectImportFileSchema(merged.headers);
        if (detectRes.schema_id) {
          deps.autodetectedSchemaId.value = detectRes.schema_id;
          deps.selectedSchemaId.value = detectRes.schema_id;
          deps.isCustomMapping.value = false;
        } else {
          deps.autodetectedSchemaId.value = null;
          deps.selectedSchemaId.value = null;
          deps.isCustomMapping.value = true;
        }
      } catch (err: any) {
        console.error('Failed to autodetect schema:', err);
        deps.isCustomMapping.value = true;
      }
    }
  };

  return { processFiles };
}
