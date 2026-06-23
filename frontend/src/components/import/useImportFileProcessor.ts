import { type Ref } from 'vue';
import { api } from '../../services/api';
import { parseCsvText } from '../../services/import';

export interface UseImportFileProcessorOptions {
  importFile: Ref<File | null>;
  fileText: Ref<string>;
  importFileHeaders: Ref<string[]>;
  allRawRows: Ref<string[][]>;
  importDelimiter: Ref<string>;
  uiColumns: Ref<Array<{ id: string; colIdx: number; name: string; label: string; isDuplicate?: boolean }>>;
  currentStep: Ref<number>;
  autodetectedSchemaId: Ref<number | null>;
  selectedSchemaId: Ref<number | null>;
  isCustomMapping: Ref<boolean>;
  importError: Ref<string>;
  importSuccessSummary: Ref<any>;
  onSchemaSelect: () => void;
  initializeConfigs: () => void;
}

export function useImportFileProcessor(options: UseImportFileProcessorOptions) {
  const processFile = async (file: File) => {
    options.importFile.value = file;
    options.importError.value = '';
    options.importSuccessSummary.value = null;

    const reader = new FileReader();
    reader.onload = async (e) => {
      const text = e.target?.result as string;
      options.fileText.value = text;
      
      const parsed = parseCsvText(text);
      if (parsed.headers.length > 0) {
        options.importDelimiter.value = parsed.delimiter;
        options.importFileHeaders.value = parsed.headers;
        options.uiColumns.value = parsed.headers.map((h, idx) => ({ id: `col-${idx}`, colIdx: idx, name: h, label: h }));
        options.allRawRows.value = parsed.rawRows;
        options.currentStep.value = 1;

        try {
          const detectRes = await api.detectImportFileSchema(parsed.headers);
          if (detectRes.schema_id) {
            options.autodetectedSchemaId.value = detectRes.schema_id;
            options.selectedSchemaId.value = detectRes.schema_id;
            options.isCustomMapping.value = false;
            options.onSchemaSelect();
          } else {
            options.autodetectedSchemaId.value = null;
            options.selectedSchemaId.value = null;
            options.isCustomMapping.value = true;
            options.initializeConfigs();
          }
        } catch (err: any) {
          console.error('Failed to autodetect schema:', err);
          options.isCustomMapping.value = true;
          options.initializeConfigs();
        }
      }
    };
    reader.readAsText(file);
  };

  return {
    processFile
  };
}
