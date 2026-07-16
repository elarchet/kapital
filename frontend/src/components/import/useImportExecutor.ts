import { ref, type Ref } from 'vue';
import { api } from '../../services/api';

export interface UseImportExecutorOptions {
  portfolio: { id: number; name: string };
  importFiles: Ref<File[]>;
  selectedSchemaId: Ref<number | null>;
  availableSchemas: Ref<any[]>;
  loadSchemas: () => Promise<void>;
  isCustomMapping: Ref<boolean>;
  saveMappingTemplate: Ref<boolean>;
  mappingTemplateName: Ref<string>;
  isValidCustomMapping: Ref<boolean>;
  importDelimiter: Ref<string>;
  importDecimalSep: Ref<string>;
  institutionKey: Ref<string>;
  buildCustomMappingPayload: () => any;
  initializeConfigs: () => void;
  schemaDeleteTemplate: () => Promise<{ success: boolean; error?: string } | undefined>;
  emit: any;
}

export function useImportExecutor(options: UseImportExecutorOptions) {
  const isImporting = ref(false);
  const importError = ref('');
  const importSuccessSummary = ref<any>(null);
  const showOverwriteConfirm = ref(false);
  const hasConfirmedOverwrite = ref(false);

  const handleImport = async () => {
    if (!options.importFiles.value.length || !options.portfolio.id) return;
    isImporting.value = true;
    importError.value = '';
    importSuccessSummary.value = null;

    try {
      let finalSchemaId = options.selectedSchemaId.value;

      if (options.isCustomMapping.value && options.saveMappingTemplate.value && options.mappingTemplateName.value.trim()) {
        const existingSchema = options.availableSchemas.value.find(
          s => s.name.trim().toLowerCase() === options.mappingTemplateName.value.trim().toLowerCase()
        );

        if (existingSchema) {
          if (existingSchema.is_public || existingSchema.user_id === null) {
            throw new Error(`A public template named "${existingSchema.name}" already exists. Please choose a unique name.`);
          }
          if (!hasConfirmedOverwrite.value) {
            showOverwriteConfirm.value = true;
            isImporting.value = false;
            return;
          }
        }
      }

      const overwriteConfirmed = hasConfirmedOverwrite.value;
      hasConfirmedOverwrite.value = false;

      if (options.isCustomMapping.value) {
        if (!options.isValidCustomMapping.value) {
          if (options.saveMappingTemplate.value && options.mappingTemplateName.value.trim()) {
            const mappingConfig = options.buildCustomMappingPayload();
            const templateData = {
              name: options.mappingTemplateName.value.trim(),
              is_public: false,
              delimiter: options.importDelimiter.value,
              decimal_separator: options.importDecimalSep.value,
              mappings: JSON.stringify(mappingConfig),
              institution_key: options.institutionKey.value,
              is_incomplete: true,
            };

            if (overwriteConfirmed) {
              const existingSchema = options.availableSchemas.value.find(
                s => s.name.trim().toLowerCase() === options.mappingTemplateName.value.trim().toLowerCase()
              );
              if (existingSchema) {
                await api.updateImportFileSchema(existingSchema.id, templateData);
              }
            } else {
              await api.createImportFileSchema(templateData);
            }

            importSuccessSummary.value = {
              positions_created: 0,
              raw_transactions_imported: 0,
              allocations_created: 0,
              skipped_duplicates: 0,
              skipped_invalid: 0,
              is_template_only: true,
            };
            await options.loadSchemas();
            options.emit('success');
            return;
          } else {
            throw new Error('Please fix the validation errors before importing.');
          }
        }
        const mappingConfig = options.buildCustomMappingPayload();

        if (options.saveMappingTemplate.value && options.mappingTemplateName.value.trim()) {
          const templateData = {
            name: options.mappingTemplateName.value.trim(),
            is_public: false,
            delimiter: options.importDelimiter.value,
            decimal_separator: options.importDecimalSep.value,
            mappings: JSON.stringify(mappingConfig),
            institution_key: options.institutionKey.value,
            is_incomplete: false,
          };

          let savedSchema;
          if (overwriteConfirmed) {
            const existingSchema = options.availableSchemas.value.find(
              s => s.name.trim().toLowerCase() === options.mappingTemplateName.value.trim().toLowerCase()
            );
            if (existingSchema) {
              savedSchema = await api.updateImportFileSchema(existingSchema.id, templateData);
            } else {
              savedSchema = await api.createImportFileSchema(templateData);
            }
          } else {
            savedSchema = await api.createImportFileSchema(templateData);
          }
          await options.loadSchemas();
          finalSchemaId = savedSchema.id;
        } else {
          const res = await api.importPositions(
            options.portfolio.id,
            options.importFiles.value,
            null,
            {
              mappings: mappingConfig,
              delimiter: options.importDelimiter.value,
              decimal_separator: options.importDecimalSep.value,
              institution_key: options.institutionKey.value,
            }
          );
          importSuccessSummary.value = res;
          options.emit('success');
          return;
        }
      }

      if (finalSchemaId) {
        const res = await api.importPositions(options.portfolio.id, options.importFiles.value, finalSchemaId, null);
        importSuccessSummary.value = res;
        options.emit('success');
      }
    } catch (err: any) {
      importError.value = err.message || 'Import failed.';
    } finally {
      isImporting.value = false;
    }
  };

  const handleDeleteTemplateWrapper = async () => {
    const res = await options.schemaDeleteTemplate();
    if (res && !res.success) {
      importError.value = res.error || 'Failed to delete template.';
    } else if (res && res.success) {
      options.isCustomMapping.value = true;
      options.initializeConfigs();
    }
  };

  return {
    isImporting,
    importError,
    importSuccessSummary,
    showOverwriteConfirm,
    hasConfirmedOverwrite,
    handleImport,
    handleDeleteTemplateWrapper,
  };
}
