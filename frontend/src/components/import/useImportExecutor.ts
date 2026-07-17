import { ref, type Ref } from 'vue';
import { api } from '../../services/api';
import { useNotifications } from '../../composables/useNotifications';

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
  const showOverwriteConfirm = ref(false);
  const hasConfirmedOverwrite = ref(false);
  const { notifySuccess, notifyInfo } = useNotifications();

  // Success feedback is a toast (the wizard closes right away), not a panel.
  const reportImportResult = (res: any) => {
    const imported = res.raw_transactions_imported ?? 0;
    const details: string[] = [];
    if (res.positions_created) {
      details.push(`${res.positions_created} position${res.positions_created === 1 ? '' : 's'} created`);
    }
    if (res.skipped_duplicates) {
      details.push(`${res.skipped_duplicates} duplicate${res.skipped_duplicates === 1 ? '' : 's'} skipped`);
    }
    if (res.skipped_invalid) {
      details.push(`${res.skipped_invalid} invalid row${res.skipped_invalid === 1 ? '' : 's'} skipped`);
    }
    const message = details.join(' · ') || undefined;
    if (imported > 0) {
      notifySuccess(`${imported} transaction${imported === 1 ? '' : 's'} imported`, { message });
    } else {
      notifyInfo('No new transactions imported', { message });
    }
  };

  const handleImport = async () => {
    if (!options.importFiles.value.length || !options.portfolio.id) return;
    isImporting.value = true;
    importError.value = '';

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

            notifySuccess('Template saved', {
              message: `The configuration template "${options.mappingTemplateName.value.trim()}" has been saved.`,
            });
            await options.loadSchemas();
            options.emit('success');
            options.emit('close');
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
          notifySuccess('Template saved', {
            message: `The configuration template "${options.mappingTemplateName.value.trim()}" has been saved.`,
          });
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
          reportImportResult(res);
          options.emit('success');
          options.emit('close');
          return;
        }
      }

      if (finalSchemaId) {
        const res = await api.importPositions(options.portfolio.id, options.importFiles.value, finalSchemaId, null);
        reportImportResult(res);
        options.emit('success');
        options.emit('close');
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
    showOverwriteConfirm,
    hasConfirmedOverwrite,
    handleImport,
    handleDeleteTemplateWrapper,
  };
}
