<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { api } from '../services/api';
import { Layers, Plus, Loader, ChevronLeft, ChevronRight, AlertTriangle } from '@lucide/vue';

const props = defineProps<{
  portfolio: {
    id: number;
    name: string;
  };
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'success'): void;
}>();

// UI States
const importFile = ref<File | null>(null);
const fileText = ref('');
const importFileHeaders = ref<string[]>([]);
const availableSchemas = ref<any[]>([]);
const selectedSchemaId = ref<number | null>(null);
const autodetectedSchemaId = ref<number | null>(null);
const isCustomMapping = ref(false);

const isImporting = ref(false);
const importError = ref('');
const importSuccessSummary = ref<{ positions_created: number; operations_imported: number; operations_skipped: number } | null>(null);

// Mappings configuration
const mappingTemplateName = ref('');
const saveMappingTemplate = ref(false);
const importDelimiter = ref(',');
const importDecimalSep = ref('.');

// Dynamic metadata & row parsing state
const importFields = ref<any[]>([]);
const allRawRows = ref<string[][]>([]);
const currentPage = ref(1);
const rowsPerPage = 10;

// Dynamic mappings
const columnMappings = ref<Record<number, string>>({}); // colIdx -> dbKey
const columnTransformations = ref<Record<string, { divisor?: number; multiplier?: number }>>({}); // dbKey -> { divisor, multiplier }
const enumValueMappings = ref<Record<string, Record<string, string>>>({}); // dbKey -> rawValue -> targetValue

// Dirty state check
const isDirty = computed(() => {
  return importFile.value !== null;
});

const requestClose = () => {
  if (isDirty.value && !importSuccessSummary.value) {
    if (confirm('You have uploaded a file and configured mappings. Discard import configuration?')) {
      emit('close');
    }
  } else {
    emit('close');
  }
};

const loadSchemas = async () => {
  try {
    availableSchemas.value = await api.getImportFileSchemas();
  } catch (err: any) {
    console.error('Failed to load schemas:', err);
  }
};

const onSchemaSelect = () => {
  if (selectedSchemaId.value === -1) {
    isCustomMapping.value = true;
    selectedSchemaId.value = null;
  } else {
    isCustomMapping.value = false;
    const schema = availableSchemas.value.find(s => s.id === selectedSchemaId.value);
    if (schema) {
      importDelimiter.value = schema.delimiter;
      importDecimalSep.value = schema.decimal_separator;
      try {
        const mappings = JSON.parse(schema.mappings);
        const cols = mappings.columns || {};
        
        columnMappings.value = {};
        columnTransformations.value = {};
        enumValueMappings.value = {};

        Object.entries(cols).forEach(([dbKey, csvHeaderName]) => {
          if (csvHeaderName) {
            const idx = importFileHeaders.value.indexOf(csvHeaderName as string);
            if (idx >= 0) {
              columnMappings.value[idx] = dbKey;
            }
          }
        });

        const transformations = mappings.transformations || {};
        Object.entries(transformations).forEach(([dbKey, trans]: [string, any]) => {
          columnTransformations.value[dbKey] = trans;
        });

        // Load operation type enum mapping (type_mappings)
        const type_mappings = mappings.type_mappings || {};
        enumValueMappings.value['operation_type'] = {};
        Object.entries(type_mappings).forEach(([targetEnum, rawVals]: [string, any]) => {
          if (Array.isArray(rawVals)) {
            rawVals.forEach(val => {
              enumValueMappings.value['operation_type'][val] = targetEnum;
            });
          }
        });

        // Load fee type enum mapping (enum_mappings)
        const enum_mappings = mappings.enum_mappings || {};
        Object.entries(enum_mappings).forEach(([dbKey, mappingsObj]: [string, any]) => {
          enumValueMappings.value[dbKey] = {};
          Object.entries(mappingsObj).forEach(([targetEnum, rawVals]: [string, any]) => {
            if (Array.isArray(rawVals)) {
              rawVals.forEach(val => {
                enumValueMappings.value[dbKey][val] = targetEnum;
              });
            }
          });
        });
      } catch (err) {
        console.error('Failed to parse schema mappings:', err);
      }
    }
  }
};

const handleFileChange = async (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    await processFile(target.files[0]);
  }
};

const processFile = async (file: File) => {
  importFile.value = file;
  importError.value = '';
  importSuccessSummary.value = null;

  const reader = new FileReader();
  reader.onload = async (e) => {
    const text = e.target?.result as string;
    fileText.value = text;
    const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    if (lines.length > 0) {
      let delim = ',';
      const firstLine = lines[0];
      if (firstLine.includes(';')) delim = ';';
      else if (firstLine.includes('\t')) delim = '\t';

      importDelimiter.value = delim;

      const headers = firstLine.split(delim).map(h => h.trim().replace(/^["']|["']$/g, ''));
      importFileHeaders.value = headers;

      // Parse raw rows (excluding header)
      allRawRows.value = lines.slice(1).map(line =>
        line.split(delim).map(cell => cell.trim().replace(/^["']|["']$/g, ''))
      ).filter(row => row.length > 0 && row.some(cell => cell.length > 0));

      currentPage.value = 1;

      // Auto-detect schema
      try {
        const detectRes = await api.detectImportFileSchema(headers);
        if (detectRes.schema_id) {
          autodetectedSchemaId.value = detectRes.schema_id;
          selectedSchemaId.value = detectRes.schema_id;
          isCustomMapping.value = false;
          onSchemaSelect();
        } else {
          autodetectedSchemaId.value = null;
          selectedSchemaId.value = null;
          isCustomMapping.value = true;
          prepopulateGuesses(headers);
        }
      } catch (err: any) {
        console.error('Failed to autodetect schema:', err);
      }
    }
  };
  reader.readAsText(file);
};

const prepopulateGuesses = (headers: string[]) => {
  columnMappings.value = {};
  columnTransformations.value = {};
  enumValueMappings.value = {};

  const findMatchIdx = (keys: string[]) => {
    return headers.findIndex(h => keys.some(k => h.toLowerCase().includes(k.toLowerCase())));
  };

  const matches: Record<string, string[]> = {
    ticker: ['ticker', 'symbol'],
    isin: ['isin'],
    name: ['name', 'description', 'company'],
    quantity: ['shares', 'qty', 'quantity', 'number of shares', 'no. of shares'],
    unit_price: ['price', 'unit price', 'price / share'],
    total_amount: ['total', 'amount'],
    currency: ['currency'],
    executed_at: ['time', 'date', 'timestamp'],
    operation_type: ['action', 'type', 'transaction type'],
    transaction_id: ['id', 'transaction id', 'reference'],
    fee_amount: ['fee', 'conversion fee'],
    fee_currency: ['fee currency'],
    fee_type: ['fee type'],
    tax_amount: ['tax', 'withholding tax'],
    tax_currency: ['tax currency'],
    merchant_name: ['merchant', 'merchant name'],
    merchant_category: ['category', 'merchant category']
  };

  Object.entries(matches).forEach(([dbKey, keys]) => {
    const idx = findMatchIdx(keys);
    if (idx >= 0) {
      columnMappings.value[idx] = dbKey;
    }
  });

  // Auto detect GBX currency for scaling divisor = 100
  const currencyIdx = headers.findIndex(h => h.toLowerCase().includes('currency'));
  if (currencyIdx >= 0) {
    const hasGBX = allRawRows.value.slice(0, 100).some(row => row[currencyIdx]?.toUpperCase() === 'GBX');
    if (hasGBX) {
      columnTransformations.value['unit_price'] = { divisor: 100 };
      columnTransformations.value['total_amount'] = { divisor: 100 };
    }
  }
};

const handleColumnMapChange = (colIdx: number, dbKey: string) => {
  if (dbKey) {
    // Unique check: clear mapping of any other column mapped to this dbKey
    Object.entries(columnMappings.value).forEach(([idxStr, mappedKey]) => {
      const idx = Number(idxStr);
      if (idx !== colIdx && mappedKey === dbKey) {
        columnMappings.value[idx] = '';
      }
    });
  }
  columnMappings.value[colIdx] = dbKey;
};

// Pagination Computeds
const totalRowsCount = computed(() => allRawRows.value.length);
const totalPages = computed(() => Math.ceil(totalRowsCount.value / rowsPerPage));
const paginatedRawRows = computed(() => {
  const start = (currentPage.value - 1) * rowsPerPage;
  return allRawRows.value.slice(start, start + rowsPerPage);
});

const prevPage = () => {
  if (currentPage.value > 1) currentPage.value--;
};
const nextPage = () => {
  if (currentPage.value < totalPages.value) currentPage.value++;
};

// Dynamic Enums Wizards detection
const mappedEnumFields = computed(() => {
  const result: Array<{ dbKey: string; label: string; values: string[]; csvColIdx: number; uniqueValues: string[] }> = [];

  Object.entries(columnMappings.value).forEach(([idxStr, dbKey]) => {
    const colIdx = Number(idxStr);
    const field = importFields.value.find(f => f.key === dbKey);
    if (field && field.type === 'enum') {
      const uniqueSet = new Set<string>();
      allRawRows.value.forEach(row => {
        const val = row[colIdx];
        if (val && val.trim()) {
          uniqueSet.add(val.trim());
        }
      });
      result.push({
        dbKey,
        label: field.label,
        values: field.enum_values || [],
        csvColIdx: colIdx,
        uniqueValues: Array.from(uniqueSet)
      });
    }
  });

  return result;
});

const getEnumValueMapping = (dbKey: string, rawVal: string) => {
  if (!enumValueMappings.value[dbKey]) return '';
  return enumValueMappings.value[dbKey][rawVal] || '';
};

const setEnumValueMapping = (dbKey: string, rawVal: string, targetVal: string) => {
  if (!enumValueMappings.value[dbKey]) {
    enumValueMappings.value[dbKey] = {};
  }
  if (targetVal) {
    enumValueMappings.value[dbKey][rawVal] = targetVal;
  } else {
    delete enumValueMappings.value[dbKey][rawVal];
  }
};

// Dynamic validation
const validationErrors = computed(() => {
  const errors: string[] = [];
  if (!importFile.value) return errors;

  // 1. Required fields check
  const mappedKeys = Object.values(columnMappings.value);
  importFields.value.forEach(f => {
    if (f.is_required && !mappedKeys.includes(f.key)) {
      errors.push(`Required field "${f.label}" is not mapped to any column.`);
    }
  });

  // 2. Enum values conversion check
  mappedEnumFields.value.forEach(enumField => {
    enumField.uniqueValues.forEach(val => {
      const target = getEnumValueMapping(enumField.dbKey, val);
      if (!target) {
        errors.push(`Value "${val}" in column "${enumField.label}" is not mapped to a database enum value.`);
      }
    });
  });

  return errors;
});

const isValidCustomMapping = computed(() => validationErrors.value.length === 0);

// Client-side parser for displaying mapped data in real-time
const parsedPreviewRows = computed(() => {
  if (!fileText.value || !importDelimiter.value) return [];

  const lines = fileText.value.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length <= 1) return [];

  const getIndex = (dbKey: string) => {
    const entry = Object.entries(columnMappings.value).find(([_, k]) => k === dbKey);
    return entry ? Number(entry[0]) : -1;
  };

  const idxAction = getIndex('operation_type');
  const idxTime = getIndex('executed_at');
  const idxTicker = getIndex('ticker');
  const idxIsin = getIndex('isin');
  const idxName = getIndex('name');
  const idxQuantity = getIndex('quantity');
  const idxPrice = getIndex('unit_price');
  const idxTotal = getIndex('total_amount');
  const idxCurrency = getIndex('currency');
  const idxFeeAmt = getIndex('fee_amount');
  const idxFeeCurr = getIndex('fee_currency');
  const idxFeeType = getIndex('fee_type');
  const idxTaxAmt = getIndex('tax_amount');
  const idxTaxCurr = getIndex('tax_currency');
  const idxMerchantName = getIndex('merchant_name');
  const idxMerchantCat = getIndex('merchant_category');

  const previewLines = lines.slice(1, 6);
  return previewLines.map(line => {
    const cells = line.split(importDelimiter.value).map(c => c.trim().replace(/^["']|["']$/g, ''));
    const getVal = (idx: number) => (idx >= 0 && idx < cells.length ? cells[idx] : '');

    const rawAction = getVal(idxAction);
    const opType = getEnumValueMapping('operation_type', rawAction) || 'unknown';

    const rawQty = getVal(idxQuantity);
    const rawPrice = getVal(idxPrice);
    const rawTotal = getVal(idxTotal);
    const rawCurrency = getVal(idxCurrency);

    const applyTrans = (dbKey: string, rawVal: string) => {
      let num = parseFloat(rawVal.replace(importDecimalSep.value === '.' ? ',' : '.', '').replace(importDecimalSep.value, '.'));
      if (isNaN(num)) return rawVal;
      const trans = columnTransformations.value[dbKey] || {};
      if (trans.divisor) num /= trans.divisor;
      if (trans.multiplier) num *= trans.multiplier;
      return num.toString();
    };

    let parsedPrice = rawPrice;
    if (idxPrice >= 0) parsedPrice = applyTrans('unit_price', rawPrice);
    let parsedTotal = rawTotal;
    if (idxTotal >= 0) parsedTotal = applyTrans('total_amount', rawTotal);

    let displayCurrency = rawCurrency || 'EUR';

    const feesList: string[] = [];
    const feeAmtVal = getVal(idxFeeAmt);
    if (feeAmtVal && parseFloat(feeAmtVal) > 0) {
      const parsedFee = applyTrans('fee_amount', feeAmtVal);
      const rawFeeType = getVal(idxFeeType);
      const resolvedFeeType = rawFeeType ? (getEnumValueMapping('fee_type', rawFeeType) || 'conversion') : 'conversion';
      feesList.push(`${parsedFee} ${getVal(idxFeeCurr) || displayCurrency} (${resolvedFeeType})`);
    }
    const taxAmtVal = getVal(idxTaxAmt);
    if (taxAmtVal && parseFloat(taxAmtVal) > 0) {
      const parsedTax = applyTrans('tax_amount', taxAmtVal);
      feesList.push(`${parsedTax} ${getVal(idxTaxCurr) || displayCurrency} (tax)`);
    }

    return {
      time: getVal(idxTime),
      action: rawAction,
      opType,
      ticker: getVal(idxTicker),
      name: getVal(idxName),
      isin: getVal(idxIsin),
      quantity: idxQuantity >= 0 ? applyTrans('quantity', rawQty) : rawQty,
      price: parsedPrice,
      total: parsedTotal,
      currency: displayCurrency,
      fees: feesList.join(', ') || 'None',
      merchant: getVal(idxMerchantName)
        ? `${getVal(idxMerchantName)} (${getVal(idxMerchantCat)})`
        : '—'
    };
  });
});

const buildCustomMappingPayload = () => {
  const cols: Record<string, string> = {};
  Object.entries(columnMappings.value).forEach(([idxStr, dbKey]) => {
    const colIdx = Number(idxStr);
    if (dbKey) {
      cols[dbKey] = importFileHeaders.value[colIdx];
    }
  });

  const type_mappings: Record<string, string[]> = {};
  const enum_mappings: Record<string, Record<string, string[]>> = {};

  // Initialize allowed operation types from metadata
  const opField = importFields.value.find(f => f.key === 'operation_type');
  if (opField && opField.enum_values) {
    opField.enum_values.forEach((v: string) => {
      type_mappings[v] = [];
    });
  }

  // Initialize other enums from metadata
  importFields.value.forEach(f => {
    if (f.type === 'enum' && f.key !== 'operation_type') {
      enum_mappings[f.key] = {};
      if (f.enum_values) {
        f.enum_values.forEach((v: string) => {
          enum_mappings[f.key][v] = [];
        });
      }
    }
  });

  // Populate enum value lists
  Object.entries(enumValueMappings.value).forEach(([dbKey, mappingObj]) => {
    Object.entries(mappingObj).forEach(([rawVal, targetVal]) => {
      if (targetVal) {
        if (dbKey === 'operation_type') {
          if (!type_mappings[targetVal]) type_mappings[targetVal] = [];
          type_mappings[targetVal].push(rawVal);
        } else {
          if (!enum_mappings[dbKey]) enum_mappings[dbKey] = {};
          if (!enum_mappings[dbKey][targetVal]) enum_mappings[dbKey][targetVal] = [];
          enum_mappings[dbKey][targetVal].push(rawVal);
        }
      }
    });
  });

  return {
    columns: cols,
    type_mappings,
    enum_mappings,
    transformations: columnTransformations.value
  };
};

const handleImport = async () => {
  if (!importFile.value || !props.portfolio.id) return;
  isImporting.value = true;
  importError.value = '';
  importSuccessSummary.value = null;

  try {
    let finalSchemaId = selectedSchemaId.value;

    if (isCustomMapping.value) {
      if (!isValidCustomMapping.value) {
        throw new Error('Please fix the validation errors before importing.');
      }
      const mappingConfig = buildCustomMappingPayload();

      if (saveMappingTemplate.value && mappingTemplateName.value.trim()) {
        const newSchema = await api.createImportFileSchema({
          name: mappingTemplateName.value.trim(),
          is_public: false,
          delimiter: importDelimiter.value,
          decimal_separator: importDecimalSep.value,
          mappings: JSON.stringify(mappingConfig),
        });
        finalSchemaId = newSchema.id;
      } else {
        const res = await api.importPositions(
          props.portfolio.id,
          importFile.value,
          null,
          {
            mappings: mappingConfig,
            delimiter: importDelimiter.value,
            decimal_separator: importDecimalSep.value,
          }
        );
        importSuccessSummary.value = res;
        emit('success');
        return;
      }
    }

    if (finalSchemaId) {
      const res = await api.importPositions(props.portfolio.id, importFile.value, finalSchemaId, null);
      importSuccessSummary.value = res;
      emit('success');
    }
  } catch (err: any) {
    importError.value = err.message || 'Import failed.';
  } finally {
    isImporting.value = false;
  }
};

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    requestClose();
  }
};

onMounted(async () => {
  try {
    const meta = await api.getImportMetadata();
    importFields.value = meta.fields || [];
  } catch (err) {
    console.error('Failed to load import metadata:', err);
  }
  loadSchemas();
  window.addEventListener('keydown', handleKeyDown);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown);
});
</script>

<template>
  <div class="modal-overlay" @click.self="requestClose">
    <div class="modal-card wide-modal">
      <div class="modal-header">
        <h3 class="table-title">Import Transactions to "{{ portfolio.name }}"</h3>
        <button @click="requestClose" class="modal-close-btn">&times;</button>
      </div>
      <div class="modal-body" style="overflow-y: auto; flex: 1;">
        <div v-if="importError" class="login-error" style="margin-bottom: 1rem;">
          {{ importError }}
        </div>

        <!-- Success State -->
        <div v-if="importSuccessSummary" style="background-color: var(--color-success-light); border: 1px solid rgba(16, 185, 129, 0.2); padding: 1.5rem; border-radius: var(--radius-md); text-align: center; margin-bottom: 1rem;">
          <h4 style="color: var(--color-success); font-size: 1.1rem; margin-bottom: 0.5rem;">Import Successful!</h4>
          <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 1rem;">
            Your transaction history has been successfully parsed and processed.
          </p>
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; background-color: var(--bg-secondary); padding: 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); max-width: 500px; margin: 0 auto;">
            <div>
              <div style="font-size: 0.75rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase;">Positions Created</div>
              <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">{{ importSuccessSummary.positions_created }}</div>
            </div>
            <div>
              <div style="font-size: 0.75rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase;">Operations Imported</div>
              <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">{{ importSuccessSummary.operations_imported }}</div>
            </div>
            <div>
              <div style="font-size: 0.75rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase;">Operations Skipped</div>
              <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">{{ importSuccessSummary.operations_skipped }}</div>
            </div>
          </div>
        </div>

        <template v-else>
          <!-- File upload area -->
          <div v-if="!importFile" class="form-group">
            <label>Select CSV File</label>
            <label class="upload-zone">
              <Plus style="width: 24px; height: 24px; color: var(--text-tertiary); margin: 0 auto 0.5rem auto;" />
              <p style="font-weight: 500; font-size: 0.9rem;">Click to upload or drag & drop CSV file</p>
              <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">Trading 212 format supported</p>
              <input type="file" accept=".csv" @change="handleFileChange" style="display: none;" />
            </label>
          </div>

          <div v-else>
            <div style="display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-tertiary); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); margin-bottom: 1.25rem;">
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <Layers style="width: 16px; height: 16px; color: var(--accent-color);" />
                <span style="font-weight: 600; font-size: 0.9rem;">{{ importFile.name }}</span>
                <span style="font-size: 0.75rem; color: var(--text-secondary);">({{ (importFile.size / 1024).toFixed(1) }} KB)</span>
              </div>
              <button @click="importFile = null" style="background: none; border: none; color: var(--color-danger); cursor: pointer; font-size: 0.8rem; font-weight: 600;">Remove</button>
            </div>

            <div style="display: flex; flex-direction: column; gap: 2rem; width: 100%;">
              <div>
                <!-- Template select -->
                <div class="form-group" style="max-width: 400px;">
                  <label for="templateSelect">Template Schema</label>
                  <select v-model="selectedSchemaId" id="templateSelect" @change="onSchemaSelect" class="form-control">
                    <option v-for="schema in availableSchemas" :key="schema.id" :value="schema.id">
                      {{ schema.name }} {{ schema.is_public ? '(Public)' : '(Saved)' }}
                    </option>
                    <option :value="-1">Custom Mapping Template...</option>
                  </select>
                  <p v-if="autodetectedSchemaId && selectedSchemaId === autodetectedSchemaId" style="font-size: 0.75rem; color: var(--color-success); margin-top: 0.25rem; font-weight: 500;">
                    ✓ Autodetected format matching this file
                  </p>
                </div>

                <!-- Custom mapping builder form -->
                <div v-if="isCustomMapping" style="border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1.5rem; margin-top: 1rem; background-color: var(--bg-primary);">
                  <h4 style="font-size: 0.95rem; margin-bottom: 1rem; font-weight: 600;">Custom Mapping Designer</h4>

                  <!-- CSV Structural setup -->
                  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; max-width: 500px;">
                    <div class="form-group" style="margin-bottom: 0;">
                      <label>Delimiter</label>
                      <select v-model="importDelimiter" class="form-control">
                        <option value=",">Comma (,)</option>
                        <option value=";">Semicolon (;)</option>
                        <option value="&#9;">Tab</option>
                      </select>
                    </div>
                    <div class="form-group" style="margin-bottom: 0;">
                      <label>Decimal Separator</label>
                      <select v-model="importDecimalSep" class="form-control">
                        <option value=".">Dot (.)</option>
                        <option value=",">Comma (,)</option>
                      </select>
                    </div>
                  </div>

                  <!-- Pagination and Interactive Table -->
                  <div style="margin-bottom: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                      <label style="font-size: 0.75rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">
                        CSV Headers & Data Mapping
                      </label>
                      
                      <!-- Pagination controls -->
                      <div class="pagination-controls" style="display: flex; align-items: center; gap: 0.75rem; font-size: 0.8rem; color: var(--text-secondary);">
                        <span>Row {{ (currentPage - 1) * rowsPerPage + 1 }} to {{ Math.min(currentPage * rowsPerPage, totalRowsCount) }} of {{ totalRowsCount }}</span>
                        <div style="display: flex; gap: 0.25rem;">
                          <button @click="prevPage" :disabled="currentPage === 1" class="btn btn-icon btn-sm-pagination" title="Previous Page">
                            <ChevronLeft style="width: 14px; height: 14px;" />
                          </button>
                          <button @click="nextPage" :disabled="currentPage === totalPages" class="btn btn-icon btn-sm-pagination" title="Next Page">
                            <ChevronRight style="width: 14px; height: 14px;" />
                          </button>
                        </div>
                      </div>
                    </div>

                    <div style="overflow-x: auto; max-width: 100%; border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
                      <table class="preview-table" style="margin-top: 0; min-width: 100%;">
                        <thead>
                          <tr>
                            <th v-for="(h, idx) in importFileHeaders" :key="idx" style="padding: 0.75rem; vertical-align: top; min-width: 180px;">
                              <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" :title="h">
                                {{ h }}
                              </div>
                              <!-- Target database field select dropdown -->
                              <select 
                                :value="columnMappings[idx] || ''" 
                                @change="handleColumnMapChange(idx, ($event.target as HTMLSelectElement).value)" 
                                class="form-control select-mapping-dropdown"
                              >
                                <option value="">-- Unmapped --</option>
                                <option v-for="field in importFields" :key="field.key" :value="field.key">
                                  {{ field.label }} {{ field.is_required ? '(Req)' : '' }}
                                </option>
                              </select>

                              <!-- Numeric scale factor selection -->
                              <div v-if="importFields.find(f => f.key === columnMappings[idx])?.type === 'numeric'" style="margin-top: 0.5rem;">
                                <select 
                                  :value="columnTransformations[columnMappings[idx]]?.divisor ? 'div-' + columnTransformations[columnMappings[idx]].divisor : (columnTransformations[columnMappings[idx]]?.multiplier ? 'mul-' + columnTransformations[columnMappings[idx]].multiplier : 'none')"
                                  @change="((e) => {
                                    const val = (e.target as HTMLSelectElement).value;
                                    const dbKey = columnMappings[idx];
                                    if (val.startsWith('div-')) {
                                      columnTransformations[dbKey] = { divisor: Number(val.replace('div-', '')) };
                                    } else if (val.startsWith('mul-')) {
                                      columnTransformations[dbKey] = { multiplier: Number(val.replace('mul-', '')) };
                                    } else {
                                      delete columnTransformations[dbKey];
                                    }
                                  })($event)"
                                  class="form-control select-mapping-dropdown"
                                  style="background-color: var(--accent-light); color: var(--accent-color); font-size: 0.65rem; font-weight: 600; padding: 0.15rem 0.35rem; height: auto;"
                                >
                                  <option value="none">Scale: /1 (None)</option>
                                  <option value="div-100">Scale: /100 (Cents/GBX)</option>
                                  <option value="div-1000">Scale: /1000</option>
                                  <option value="mul-100">Scale: *100</option>
                                </select>
                              </div>
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(row, rIdx) in paginatedRawRows" :key="rIdx">
                            <td v-for="(cell, cIdx) in row" :key="cIdx" style="color: var(--text-secondary); font-family: monospace; white-space: nowrap; max-width: 250px; overflow: hidden; text-overflow: ellipsis;">
                              {{ cell }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <!-- Dynamic Enum Value Mapping Wizards -->
                  <div v-if="mappedEnumFields.length > 0" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem;">
                    <div v-for="enumField in mappedEnumFields" :key="enumField.dbKey" style="border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 1.25rem; background-color: var(--bg-secondary);">
                      <h5 style="font-size: 0.9rem; font-weight: 600; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; color: var(--text-primary);">
                        Map Values for "{{ enumField.label }}"
                      </h5>
                      <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 1rem;">
                        Assign each unique raw value found in your file to the database enum type.
                      </p>
                      <div style="display: flex; flex-direction: column; gap: 0.75rem; max-height: 250px; overflow-y: auto; padding-right: 0.25rem;">
                        <div v-for="val in enumField.uniqueValues" :key="val" style="display: grid; grid-template-columns: 1fr 1.2fr; gap: 1rem; align-items: center;">
                          <span style="font-size: 0.75rem; font-family: monospace; background-color: var(--bg-tertiary); padding: 0.25rem 0.5rem; border-radius: var(--radius-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="val">
                            {{ val }}
                          </span>
                          <select 
                            :value="getEnumValueMapping(enumField.dbKey, val)" 
                            @change="setEnumValueMapping(enumField.dbKey, val, ($event.target as HTMLSelectElement).value)" 
                            class="form-control"
                            style="font-size: 0.75rem; padding: 0.25rem 0.5rem; height: auto;"
                          >
                            <option value="">-- Select DB Enum --</option>
                            <option v-for="target in enumField.values" :key="target" :value="target">
                              {{ target }}
                            </option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Validation Warning Banner -->
                  <div v-if="validationErrors.length > 0" class="validation-alert" style="margin-bottom: 1.5rem; display: flex; gap: 0.75rem; background-color: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); padding: 1rem; border-radius: var(--radius-sm);">
                    <AlertTriangle style="color: #ef4444; width: 20px; height: 20px; flex-shrink: 0; margin-top: 0.15rem;" />
                    <div>
                      <div style="font-weight: 600; font-size: 0.85rem; color: #ef4444; margin-bottom: 0.25rem;">Template Validation Errors</div>
                      <ul style="margin: 0; padding-left: 1.25rem; font-size: 0.75rem; color: var(--text-secondary); display: flex; flex-direction: column; gap: 0.15rem;">
                        <li v-for="err in validationErrors" :key="err">{{ err }}</li>
                      </ul>
                    </div>
                  </div>

                  <!-- Save template options -->
                  <div style="border-top: 1px solid var(--border-color); padding-top: 1rem; display: flex; flex-direction: column; gap: 0.5rem;">
                    <label style="display: flex; align-items: center; gap: 0.5rem; font-weight: 500; text-transform: none; font-size: 0.875rem;">
                      <input type="checkbox" v-model="saveMappingTemplate" style="width: 16px; height: 16px; cursor: pointer;" />
                      <span>Save this configuration mapping as a template</span>
                    </label>
                    <div v-if="saveMappingTemplate" class="form-group" style="margin-top: 0.5rem; margin-bottom: 0; max-width: 400px;">
                      <label>Template Name</label>
                      <input v-model="mappingTemplateName" type="text" class="form-control" placeholder="e.g. My Custom Broker CSV" required />
                    </div>
                  </div>
                </div>
              </div>

              <!-- REAL-TIME PARSED DATA PREVIEW (Only shown when not actively designing custom mappings) -->
              <div v-if="!isCustomMapping">
                <h4 style="font-size: 1rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                  <span>Mapped Output Preview</span>
                  <span style="font-size: 0.7rem; background-color: var(--accent-light); color: var(--accent-color); padding: 0.15rem 0.4rem; border-radius: 4px; font-weight: 600;">Real-time</span>
                </h4>
                <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 1rem;">
                  This shows exactly how the first few lines of your CSV will be parsed and loaded into the database according to your selected template.
                </p>

                <div v-if="parsedPreviewRows.length === 0" style="border: 1px dashed var(--border-color); border-radius: var(--radius-md); padding: 3rem 1.5rem; text-align: center; color: var(--text-tertiary); font-size: 0.85rem;">
                  Select a template to see the parsed transactions preview here.
                </div>

                <div v-else style="overflow-x: auto; border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
                  <table class="preview-table" style="margin-top: 0; font-size: 0.7rem; width: 100%;">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Type</th>
                        <th>Asset Name (Ticker/ISIN)</th>
                        <th>Qty</th>
                        <th>Price</th>
                        <th>Total</th>
                        <th>Fees/Taxes</th>
                        <th>Merchant</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, idx) in parsedPreviewRows" :key="idx">
                        <td>{{ row.time || '—' }}</td>
                        <td>
                          <span class="badge" :class="'badge-' + row.opType" style="padding: 0.15rem 0.35rem; font-size: 0.65rem; text-transform: uppercase;">
                            {{ row.opType }}
                          </span>
                        </td>
                        <td>
                          <div style="font-weight: 600; color: var(--text-primary);">{{ row.name || 'Asset' }}</div>
                          <span style="color: var(--text-secondary); font-size: 0.65rem;">
                            {{ row.ticker }}{{ row.ticker && row.isin ? '/' : '' }}{{ row.isin }}
                          </span>
                        </td>
                        <td style="font-family: monospace;">{{ row.quantity }}</td>
                        <td style="font-family: monospace;">{{ row.price }} {{ row.currency }}</td>
                        <td style="font-family: monospace; font-weight: 600;">{{ row.total }} {{ row.currency }}</td>
                        <td>
                          <span style="color: var(--text-secondary);">{{ row.fees }}</span>
                        </td>
                        <td>
                          <span style="color: var(--text-secondary);">{{ row.merchant }}</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
      <div class="modal-footer">
        <button @click="requestClose" class="btn btn-sm">Cancel</button>
        <button 
          v-if="!importSuccessSummary"
          @click="handleImport" 
          class="btn btn-sm btn-primary" 
          :disabled="isImporting || !importFile || (isCustomMapping && !isValidCustomMapping) || (isCustomMapping && saveMappingTemplate && !mappingTemplateName.trim())"
        >
          <Loader v-if="isImporting" style="animation: spin 1.5s linear infinite; width: 14px; height: 14px;" />
          <span v-if="isImporting">Importing data...</span>
          <span v-else>Import Transactions</span>
        </button>
        <button 
          v-else
          @click="requestClose" 
          class="btn btn-sm btn-primary"
        >
          Done
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-close-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.25rem;
  color: var(--text-secondary);
  transition: color var(--transition-fast);
}
.modal-close-btn:hover {
  color: var(--text-primary);
}

.wide-modal {
  max-width: 1400px !important;
  width: 95vw !important;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.upload-zone {
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-md);
  padding: 2.5rem 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  background-color: var(--bg-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.upload-zone:hover {
  border-color: var(--accent-color);
  background-color: var(--accent-light);
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
  margin-top: 0.5rem;
  border: 1px solid var(--border-color);
}
.preview-table th, .preview-table td {
  border: 1px solid var(--border-color);
  padding: 0.35rem 0.5rem;
  text-align: left;
}
.preview-table th {
  background-color: var(--bg-tertiary);
  font-weight: 600;
  color: var(--text-secondary);
}

.select-mapping-dropdown {
  padding: 0.25rem 0.5rem;
  height: auto;
  font-size: 0.75rem;
}

.btn-sm-pagination {
  padding: 0.25rem;
  border-radius: var(--radius-sm);
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.btn-sm-pagination:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn-sm-pagination:hover:not(:disabled) {
  background-color: var(--bg-tertiary);
}

/* polymorphic action badges */
.badge-buy { background-color: rgba(37, 99, 235, 0.15); color: #3b82f6; }
.badge-sell { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }
.badge-dividend { background-color: rgba(16, 185, 129, 0.15); color: #10b981; }
.badge-interest { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.badge-expense { background-color: rgba(236, 72, 153, 0.15); color: #ec4899; }
.badge-revenue { background-color: rgba(139, 92, 246, 0.15); color: #8b5cf6; }
.badge-fx_rate_change { background-color: rgba(6, 182, 212, 0.15); color: #06b6d4; }
.badge-unknown { background-color: var(--bg-tertiary); color: var(--text-secondary); }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
