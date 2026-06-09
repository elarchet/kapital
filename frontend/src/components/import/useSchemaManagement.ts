import { ref, computed } from 'vue';
import { api } from '../../services/api';

export function useSchemaManagement() {
  const availableSchemas = ref<any[]>([]);
  const selectedSchemaId = ref<number | null>(null);
  const autodetectedSchemaId = ref<number | null>(null);
  const isDeletingSchema = ref(false);
  const showDeleteConfirm = ref(false);

  const selectedSchema = computed(() => {
    if (selectedSchemaId.value === null || selectedSchemaId.value === -1) return null;
    return availableSchemas.value.find(s => s.id === selectedSchemaId.value) || null;
  });

  const loadSchemas = async () => {
    try {
      availableSchemas.value = await api.getImportFileSchemas();
    } catch (err: any) {
      console.error('Failed to load schemas:', err);
    }
  };

  const isSchemaIncomplete = (schema: any) => {
    return schema ? !!schema.is_incomplete : false;
  };

  const selectedSchemaIdString = computed({
    get() {
      return selectedSchemaId.value !== null ? String(selectedSchemaId.value) : '';
    },
    set(val: string) {
      if (val === '') {
        selectedSchemaId.value = null;
      } else {
        selectedSchemaId.value = Number(val);
      }
    }
  });

  const handleDeleteTemplate = async () => {
    if (!selectedSchema.value || selectedSchema.value.is_public) return;
    isDeletingSchema.value = true;
    try {
      await api.deleteImportFileSchema(selectedSchema.value.id);
      selectedSchemaId.value = null;
      showDeleteConfirm.value = false;
      await loadSchemas();
      return { success: true };
    } catch (err: any) {
      return { success: false, error: err.message || 'Failed to delete template.' };
    } finally {
      isDeletingSchema.value = false;
    }
  };

  return {
    availableSchemas,
    selectedSchemaId,
    autodetectedSchemaId,
    isDeletingSchema,
    showDeleteConfirm,
    selectedSchema,
    isSchemaIncomplete,
    selectedSchemaIdString,
    loadSchemas,
    handleDeleteTemplate,
  };
}
