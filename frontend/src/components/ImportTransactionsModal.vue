<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { api } from '../services/api';
import { Layers, Plus, Loader, AlertTriangle } from '@lucide/vue';
import ColumnMappingWizard from './ColumnMappingWizard.vue';
import DiscardChangesConfirmModal from './DiscardChangesConfirmModal.vue';

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
const importSuccessSummary = ref<{ positions_created: number; operations_imported: number; operations_skipped: number; is_template_only?: boolean } | null>(null);

// Mappings configuration
const mappingTemplateName = ref('');
const saveMappingTemplate = ref(false);
const importDelimiter = ref(',');
const importDecimalSep = ref('.');

// Dynamic metadata & row parsing state
const importFields = ref<any[]>([]);
const allRawRows = ref<string[][]>([]);

// Wizard step: 1 = Delimiter & OpType mapping, 2 = Columns Mapping & Verification
const currentStep = ref(1);

// Step 1: Operation type column and value mapping
const operationTypeColumnIdx = ref<number | null>(null);
const operationTypeMappings = ref<Record<string, string>>({}); // raw CSV action -> DB opType

// Step 2: Column configs: colIdx -> { global: ColMapping, typeSpecific: Record<string, ColMapping> }
interface ColMapping {
  dbKey: string;
  divisor?: number;
  multiplier?: number;
  enumMappings?: Record<string, string>;
}
const columnConfigMap = ref<Record<number, {
  global: ColMapping;
  typeSpecific: Record<string, ColMapping>;
}>>({});

// Wizard modal popup states
const isWizardOpen = ref(false);
const wizardCsvHeaderName = ref('');
const wizardExampleValue = ref('');
const wizardActiveOpType = ref('');
const wizardColIdx = ref<number | null>(null);
const wizardUniqueValues = ref<string[]>([]);
const wizardInitialMapping = ref<any>(null);

// Errors expansion state for Step 2 Verification Panel
const expandedErrors = ref<Record<string, boolean>>({});

// Custom exit confirmation state
const showExitConfirm = ref<boolean>(false);

// Dirty state check
const isDirty = computed(() => {
  return importFile.value !== null;
});

const requestClose = () => {
  if (isDirty.value && !importSuccessSummary.value) {
    showExitConfirm.value = true;
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

const getEnumMappingsForField = (dbKey: string, mappings: any) => {
  const result: Record<string, string> = {};
  const enum_mappings = mappings.enum_mappings?.[dbKey] || {};
  Object.entries(enum_mappings).forEach(([targetEnum, rawVals]: [string, any]) => {
    if (Array.isArray(rawVals)) {
      rawVals.forEach(val => {
        result[val] = targetEnum;
      });
    }
  });
  return result;
};

const isSchemaIncomplete = (schema: any) => {
  return schema ? !!schema.is_incomplete : false;
};

const onSchemaSelect = () => {
  if (selectedSchemaId.value === -1) {
    isCustomMapping.value = true;
    selectedSchemaId.value = null;
    initializeConfigs();
    prepopulateGuesses(importFileHeaders.value);
  } else {
    const schema = availableSchemas.value.find(s => s.id === selectedSchemaId.value);
    if (schema) {
      const isIncomplete = isSchemaIncomplete(schema);
      if (isIncomplete) {
        isCustomMapping.value = true;
        saveMappingTemplate.value = true;
        mappingTemplateName.value = schema.name;
      } else {
        isCustomMapping.value = false;
      }
      importDelimiter.value = schema.delimiter;
      importDecimalSep.value = schema.decimal_separator;
      try {
        const mappings = JSON.parse(schema.mappings);
        const cols = mappings.columns || {};
        
        initializeConfigs();

        // 1. Parse operation type column
        const opTypeHeader = cols.operation_type;
        if (opTypeHeader) {
          const idx = importFileHeaders.value.indexOf(opTypeHeader);
          if (idx >= 0) {
            operationTypeColumnIdx.value = idx;
          }
        }

        // 2. Parse operation type value mappings
        const op_mappings = mappings.enum_mappings?.operation_type || mappings.type_mappings || {};
        Object.entries(op_mappings).forEach(([targetEnum, rawVals]: [string, any]) => {
          if (Array.isArray(rawVals)) {
            rawVals.forEach(val => {
              operationTypeMappings.value[val] = targetEnum;
            });
          }
        });

        // 3. Parse other columns mappings
        Object.entries(cols).forEach(([dbKey, val]) => {
          if (dbKey === 'operation_type') return;

          if (typeof val === 'string') {
            const idx = importFileHeaders.value.indexOf(val);
            if (idx >= 0) {
              columnConfigMap.value[idx].global = {
                dbKey,
                divisor: mappings.transformations?.[dbKey]?.divisor,
                multiplier: mappings.transformations?.[dbKey]?.multiplier,
                enumMappings: getEnumMappingsForField(dbKey, mappings)
              };
            }
          } else if (val && typeof val === 'object') {
            const valObj = val as Record<string, string>;
            Object.entries(valObj).forEach(([opType, headerName]) => {
              const idx = importFileHeaders.value.indexOf(headerName);
              if (idx >= 0) {
                const mapEntry = {
                  dbKey,
                  divisor: mappings.transformations?.[dbKey]?.[opType]?.divisor || mappings.transformations?.[dbKey]?.divisor,
                  multiplier: mappings.transformations?.[dbKey]?.[opType]?.multiplier || mappings.transformations?.[dbKey]?.multiplier,
                  enumMappings: getEnumMappingsForField(dbKey, mappings)
                };

                if (opType === 'global') {
                  columnConfigMap.value[idx].global = mapEntry;
                } else {
                  columnConfigMap.value[idx].typeSpecific[opType] = mapEntry;
                }
              }
            });
          }
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

      currentStep.value = 1;

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
        isCustomMapping.value = true;
        prepopulateGuesses(headers);
      }
    }
  };
  reader.readAsText(file);
};

const initializeConfigs = () => {
  columnConfigMap.value = {};
  importFileHeaders.value.forEach((_, idx) => {
    columnConfigMap.value[idx] = {
      global: { dbKey: '' },
      typeSpecific: {}
    };
  });
  operationTypeMappings.value = {};
  operationTypeColumnIdx.value = null;
  currentStep.value = 1;
};

const prepopulateGuesses = (headers: string[]) => {
  initializeConfigs();

  const findMatchIdx = (keys: string[]) => {
    return headers.findIndex(h => keys.some(k => h.toLowerCase().includes(k.toLowerCase())));
  };

  // 1. Guess operation type column
  const opIdx = findMatchIdx(['action', 'type', 'transaction type']);
  if (opIdx >= 0) {
    operationTypeColumnIdx.value = opIdx;
    prepopulateOpTypeGuesses();
  }

  // 2. Guess other fields as global mappings
  const matches: Record<string, string[]> = {
    ticker: ['ticker', 'symbol'],
    isin: ['isin'],
    name: ['name', 'description', 'company'],
    quantity: ['shares', 'qty', 'quantity', 'number of shares', 'no. of shares'],
    unit_price: ['price', 'unit price', 'price / share'],
    total_amount: ['total', 'amount'],
    currency: ['currency'],
    executed_at: ['time', 'date', 'timestamp'],
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
    if (dbKey === 'operation_type') return;
    const idx = findMatchIdx(keys);
    if (idx >= 0 && idx !== opIdx) {
      columnConfigMap.value[idx].global = { dbKey };
    }
  });

  // Auto detect GBX currency for scaling divisor = 100
  const currencyIdx = headers.findIndex(h => h.toLowerCase().includes('currency'));
  if (currencyIdx >= 0) {
    const hasGBX = allRawRows.value.slice(0, 100).some(row => row[currencyIdx]?.toUpperCase() === 'GBX');
    if (hasGBX) {
      const priceIdx = findMatchIdx(['price', 'unit price', 'price / share']);
      if (priceIdx >= 0 && columnConfigMap.value[priceIdx]) {
        columnConfigMap.value[priceIdx].global.divisor = 100;
      }
      const totalIdx = findMatchIdx(['total', 'amount']);
      if (totalIdx >= 0 && columnConfigMap.value[totalIdx]) {
        columnConfigMap.value[totalIdx].global.divisor = 100;
      }
    }
  }
};

const uniqueOperationTypes = computed(() => {
  if (operationTypeColumnIdx.value === null) return [];
  const uniqueSet = new Set<string>();
  allRawRows.value.forEach(row => {
    const val = row[operationTypeColumnIdx.value!];
    if (val && val.trim()) {
      uniqueSet.add(val.trim());
    }
  });
  return Array.from(uniqueSet);
});

const prepopulateOpTypeGuesses = () => {
  operationTypeMappings.value = {};
  uniqueOperationTypes.value.forEach(val => {
    const lower = val.toLowerCase();
    if (lower.includes('buy')) operationTypeMappings.value[val] = 'buy';
    else if (lower.includes('sell')) operationTypeMappings.value[val] = 'sell';
    else if (lower.includes('dividend')) operationTypeMappings.value[val] = 'dividend';
    else if (lower.includes('interest')) operationTypeMappings.value[val] = 'interest';
    else if (lower.includes('deposit')) operationTypeMappings.value[val] = 'transfer_in';
    else if (lower.includes('withdraw')) operationTypeMappings.value[val] = 'transfer_out';
    else if (lower.includes('debit') || lower.includes('expense')) operationTypeMappings.value[val] = 'expense';
    else if (lower.includes('credit') || lower.includes('revenue')) operationTypeMappings.value[val] = 'revenue';
    else if (lower.includes('conversion') || lower.includes('fx')) operationTypeMappings.value[val] = 'fx_rate_change';
    else if (lower.includes('split')) operationTypeMappings.value[val] = 'stock_split';
    else if (lower.includes('fee')) operationTypeMappings.value[val] = 'fee';
    else if (lower.includes('tax')) operationTypeMappings.value[val] = 'tax';
  });
};

const activeDbOpTypes = computed(() => {
  const types = new Set<string>();
  Object.values(operationTypeMappings.value).forEach(v => {
    if (v) types.add(v);
  });
  return Array.from(types);
});

const exampleTransactions = computed(() => {
  if (operationTypeColumnIdx.value === null) return [];
  
  const examples: Record<string, { opType: string; csvRow: string[]; rowIdx: number }> = {};
  
  allRawRows.value.forEach((row, idx) => {
    const rawAction = row[operationTypeColumnIdx.value!];
    if (rawAction) {
      const opType = operationTypeMappings.value[rawAction];
      if (opType && !examples[opType]) {
        examples[opType] = {
          opType,
          csvRow: row,
          rowIdx: idx
        };
      }
    }
  });
  
  return activeDbOpTypes.value.map(type => {
    return examples[type] || { opType: type, csvRow: [], rowIdx: -1 };
  }).filter(e => e.rowIdx !== -1);
});

const getMappedColIdxForField = (dbKey: string, opType: string) => {
  let mappedIdx = -1;
  Object.entries(columnConfigMap.value).forEach(([idxStr, conf]) => {
    const idx = Number(idxStr);
    if (conf.typeSpecific[opType]?.dbKey === dbKey) {
      mappedIdx = idx;
    } else if (conf.global.dbKey === dbKey && !conf.typeSpecific[opType]?.dbKey) {
      mappedIdx = idx;
    }
  });
  return mappedIdx;
};

const getColumnConfig = (colIdx: number, opType: string) => {
  const conf = columnConfigMap.value[colIdx];
  if (!conf) return null;
  if (conf.typeSpecific[opType]?.dbKey) {
    return conf.typeSpecific[opType];
  }
  return conf.global;
};


const getColumnMappingLabel = (colIdx: number) => {
  if (colIdx === operationTypeColumnIdx.value) {
    return 'Action / Type';
  }

  const conf = columnConfigMap.value[colIdx];
  if (!conf) return '-- Unmapped --';

  const resolvedKeys = new Set<string>();
  activeDbOpTypes.value.forEach(opType => {
    const key = conf.typeSpecific[opType]?.dbKey || conf.global.dbKey || '';
    resolvedKeys.add(key);
  });

  if (resolvedKeys.size > 1) {
    return '(Type-Specific)';
  }

  const singleKey = Array.from(resolvedKeys)[0];
  if (!singleKey) {
    return '-- Unmapped --';
  }

  const field = importFields.value.find(f => f.key === singleKey);
  return field ? field.label : '-- Unmapped --';
};

const getResolvedKeyForCell = (colIdx: number, opType: string) => {
  const conf = columnConfigMap.value[colIdx];
  if (!conf) return '';
  return conf.typeSpecific[opType]?.dbKey || conf.global.dbKey || '';
};

// LIVE STATS SIMULATION ENGINE
interface RowError {
  rowNum: number;
  rawRow: string[];
  fieldKey: string;
  fieldLabel: string;
  rawValue: string;
  errorMessage: string;
}

const liveValidationStats = computed(() => {
  const stats: Record<string, {
    total: number;
    success: number;
    failed: number;
    errors: RowError[];
  }> = {};

  activeDbOpTypes.value.forEach(type => {
    stats[type] = {
      total: 0,
      success: 0,
      failed: 0,
      errors: []
    };
  });

  if (operationTypeColumnIdx.value === null) return stats;

  allRawRows.value.forEach((row, rowIdx) => {
    const rawAction = row[operationTypeColumnIdx.value!];
    if (!rawAction) return;

    const opType = operationTypeMappings.value[rawAction];
    if (!opType || !stats[opType]) return;

    stats[opType].total++;

    const rowErrors: { fieldKey: string; fieldLabel: string; rawValue: string; errorMessage: string }[] = [];

    importFields.value.forEach(field => {
      const colIdx = getMappedColIdxForField(field.key, opType);
      const isMapped = colIdx !== -1;
      const rawValue = isMapped ? row[colIdx] : '';

      if (field.is_required && !isMapped) {
        rowErrors.push({
          fieldKey: field.key,
          fieldLabel: field.label,
          rawValue: '',
          errorMessage: 'Field is required but not mapped to any column.'
        });
        return;
      }

      if (isMapped && rawValue && rawValue.trim()) {
        const val = rawValue.trim();
        const mappingConf = getColumnConfig(colIdx, opType);

        if (field.type === 'numeric') {
          let cleaned = val;
          if (importDecimalSep.value !== '.') {
            cleaned = cleaned.replace(importDecimalSep.value, '.');
          }
          if (importDecimalSep.value === '.') {
            cleaned = cleaned.replace(/,/g, '');
          } else {
            cleaned = cleaned.replace(/\./g, '').replace(/\s/g, '');
          }

          const num = parseFloat(cleaned);
          if (isNaN(num)) {
            rowErrors.push({
              fieldKey: field.key,
              fieldLabel: field.label,
              rawValue: val,
              errorMessage: `"${val}" is not a valid decimal number.`
            });
          }
        } else if (field.type === 'datetime') {
          const parsedDate = new Date(val);
          if (isNaN(parsedDate.getTime())) {
            rowErrors.push({
              fieldKey: field.key,
              fieldLabel: field.label,
              rawValue: val,
              errorMessage: `"${val}" is not a valid date format.`
            });
          }
        } else if (field.type === 'enum') {
          const mappedEnum = mappingConf?.enumMappings?.[val];
          if (!mappedEnum) {
            rowErrors.push({
              fieldKey: field.key,
              fieldLabel: field.label,
              rawValue: val,
              errorMessage: `Value "${val}" is not mapped to a database enum option.`
            });
          }
        }
      } else if (field.is_required && (!rawValue || !rawValue.trim())) {
        rowErrors.push({
          fieldKey: field.key,
          fieldLabel: field.label,
          rawValue: '',
          errorMessage: 'Required field is empty.'
        });
      }
    });

    if (rowErrors.length > 0) {
      stats[opType].failed++;
      rowErrors.forEach(err => {
        stats[opType].errors.push({
          rowNum: rowIdx + 2, // 1-based index (row 1 is header)
          rawRow: row,
          ...err
        });
      });
    } else {
      stats[opType].success++;
    }
  });

  return stats;
});

const toggleErrorView = (opType: string) => {
  expandedErrors.value[opType] = !expandedErrors.value[opType];
};

const goToStep2 = () => {
  if (operationTypeColumnIdx.value !== null) {
    columnConfigMap.value[operationTypeColumnIdx.value].global = {
      dbKey: 'operation_type',
      enumMappings: { ...operationTypeMappings.value }
    };
  }
  currentStep.value = 2;
};

// Wizard modals events
const openWizard = (colIdx: number, opType: string | null) => {
  if (colIdx === operationTypeColumnIdx.value) return; // Already configured in Step 1
  wizardColIdx.value = colIdx;
  wizardCsvHeaderName.value = importFileHeaders.value[colIdx];
  
  let val = '';
  if (opType) {
    const example = exampleTransactions.value.find(e => e.opType === opType);
    if (example && example.csvRow) {
      val = example.csvRow[colIdx] || '';
    }
  } else {
    if (allRawRows.value.length > 0) {
      val = allRawRows.value[0][colIdx] || '';
    }
  }
  wizardExampleValue.value = val;
  wizardActiveOpType.value = opType || '';

  const uniqueSet = new Set<string>();
  allRawRows.value.forEach(row => {
    const v = row[colIdx];
    if (v && v.trim()) {
      uniqueSet.add(v.trim());
    }
  });
  wizardUniqueValues.value = Array.from(uniqueSet);

  const conf = columnConfigMap.value[colIdx];
  if (opType) {
    const specific = conf.typeSpecific[opType];
    if (specific?.dbKey) {
      wizardInitialMapping.value = {
        dbKey: specific.dbKey,
        scope: 'type',
        divisor: specific.divisor,
        multiplier: specific.multiplier,
        enumMappings: specific.enumMappings
      };
    } else {
      wizardInitialMapping.value = {
        dbKey: conf.global.dbKey,
        scope: 'global',
        divisor: conf.global.divisor,
        multiplier: conf.global.multiplier,
        enumMappings: conf.global.enumMappings
      };
    }
  } else {
    wizardInitialMapping.value = {
      dbKey: conf.global.dbKey,
      scope: 'global',
      divisor: conf.global.divisor,
      multiplier: conf.global.multiplier,
      enumMappings: conf.global.enumMappings
    };
  }

  isWizardOpen.value = true;
};

const handleWizardSave = (payload: {
  dbKey: string;
  scope: 'global' | 'type';
  divisor?: number;
  multiplier?: number;
  enumMappings?: Record<string, string>;
}) => {
  if (wizardColIdx.value === null) return;
  const colIdx = wizardColIdx.value;
  const conf = columnConfigMap.value[colIdx];

  const mapEntry = {
    dbKey: payload.dbKey,
    divisor: payload.divisor,
    multiplier: payload.multiplier,
    enumMappings: payload.enumMappings
  };

  if (payload.scope === 'global') {
    conf.global = mapEntry;
  } else {
    const opType = wizardActiveOpType.value;
    if (opType) {
      conf.typeSpecific[opType] = mapEntry;
    }
  }

  isWizardOpen.value = false;
};

const handleWizardClear = () => {
  if (wizardColIdx.value === null) return;
  const colIdx = wizardColIdx.value;
  const conf = columnConfigMap.value[colIdx];

  if (wizardActiveOpType.value) {
    delete conf.typeSpecific[wizardActiveOpType.value];
  } else {
    conf.global = { dbKey: '' };
  }

  isWizardOpen.value = false;
};

// Dynamic validation
const validationErrors = computed(() => {
  const errors: string[] = [];
  if (!importFile.value) return errors;

  if (operationTypeColumnIdx.value === null) {
    errors.push('Required: operation type CSV column is not selected.');
    return errors;
  }

  uniqueOperationTypes.value.forEach(val => {
    if (!operationTypeMappings.value[val]) {
      errors.push(`Action "${val}" from your file is not mapped to any database transaction type.`);
    }
  });

  activeDbOpTypes.value.forEach(opType => {
    importFields.value.forEach(f => {
      if (f.is_required) {
        const colIdx = getMappedColIdxForField(f.key, opType);
        if (colIdx === -1) {
          errors.push(`Required database field "${f.label}" is not mapped for "${opType}" transactions.`);
        }
      }
    });

    const stats = liveValidationStats.value[opType];
    if (stats && stats.failed > 0) {
      errors.push(`There are ${stats.failed} parsing failures in "${opType}" transactions. Expand the Verification Panel below to inspect.`);
    }
  });

  return errors;
});

const isValidCustomMapping = computed(() => validationErrors.value.length === 0);

// Client-side parser for displaying mapped data in real-time
const parsedPreviewRows = computed(() => {
  if (!fileText.value || !importDelimiter.value || operationTypeColumnIdx.value === null) return [];

  const lines = fileText.value.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length <= 1) return [];

  const previewLines = lines.slice(1, 6);
  return previewLines.map(line => {
    const cells = line.split(importDelimiter.value).map(c => c.trim().replace(/^["']|["']$/g, ''));
    const getVal = (idx: number) => (idx >= 0 && idx < cells.length ? cells[idx] : '');

    const rawAction = getVal(operationTypeColumnIdx.value!);
    const opType = operationTypeMappings.value[rawAction] || 'unknown';

    const getMappedVal = (dbKey: string) => {
      const idx = getMappedColIdxForField(dbKey, opType);
      return getVal(idx);
    };

    const applyTrans = (dbKey: string, rawVal: string) => {
      let num = parseFloat(rawVal.replace(importDecimalSep.value === '.' ? ',' : '.', '').replace(importDecimalSep.value, '.'));
      if (isNaN(num)) return rawVal;

      const idx = getMappedColIdxForField(dbKey, opType);
      if (idx !== -1) {
        const conf = getColumnConfig(idx, opType);
        if (conf?.divisor) num /= conf.divisor;
        if (conf?.multiplier) num *= conf.multiplier;
      }
      return num.toString();
    };

    const ticker = getMappedVal('ticker');
    const isin = getMappedVal('isin');
    const name = getMappedVal('name') || ticker || isin || 'Asset';

    const rawQty = getMappedVal('quantity');
    const rawPrice = getMappedVal('unit_price');
    const rawTotal = getMappedVal('total_amount');
    const rawCurrency = getMappedVal('currency');

    let parsedPrice = rawPrice;
    if (rawPrice) parsedPrice = applyTrans('unit_price', rawPrice);
    let parsedTotal = rawTotal;
    if (rawTotal) parsedTotal = applyTrans('total_amount', rawTotal);

    const displayCurrency = rawCurrency || 'EUR';

    // Fees
    const feesList: string[] = [];
    const feeAmtVal = getMappedVal('fee_amount');
    if (feeAmtVal && parseFloat(feeAmtVal) > 0) {
      const parsedFee = applyTrans('fee_amount', feeAmtVal);
      const rawFeeType = getMappedVal('fee_type');
      let resolvedFeeType = 'conversion';
      if (rawFeeType) {
        const idx = getMappedColIdxForField('fee_type', opType);
        if (idx !== -1) {
          const conf = getColumnConfig(idx, opType);
          resolvedFeeType = conf?.enumMappings?.[rawFeeType] || 'conversion';
        }
      }
      feesList.push(`${parsedFee} ${getMappedVal('fee_currency') || displayCurrency} (${resolvedFeeType})`);
    }

    const taxAmtVal = getMappedVal('tax_amount');
    if (taxAmtVal && parseFloat(taxAmtVal) > 0) {
      const parsedTax = applyTrans('tax_amount', taxAmtVal);
      feesList.push(`${parsedTax} ${getMappedVal('tax_currency') || displayCurrency} (tax)`);
    }

    return {
      time: getMappedVal('executed_at'),
      action: rawAction,
      opType,
      ticker,
      name,
      isin,
      quantity: rawQty ? applyTrans('quantity', rawQty) : '',
      price: parsedPrice,
      total: parsedTotal,
      currency: displayCurrency,
      fees: feesList.join(', ') || 'None',
      merchant: getMappedVal('merchant_name')
        ? `${getMappedVal('merchant_name')} (${getMappedVal('merchant_category')})`
        : '—'
    };
  });
});

const buildCustomMappingPayload = () => {
  const cols: Record<string, any> = {};
  const transformations: Record<string, any> = {};
  const enum_mappings: Record<string, Record<string, string[]>> = {};

  if (operationTypeColumnIdx.value !== null) {
    cols['operation_type'] = importFileHeaders.value[operationTypeColumnIdx.value];
  }

  const dbKeyToCol = new Map<string, { global?: string; typeSpecific?: Record<string, string> }>();

  importFields.value.forEach(f => {
    if (f.key !== 'operation_type') {
      dbKeyToCol.set(f.key, {});
    }
  });

  Object.entries(columnConfigMap.value).forEach(([colIdxStr, conf]) => {
    const colIdx = Number(colIdxStr);
    const headerName = importFileHeaders.value[colIdx];

    if (conf.global.dbKey) {
      const entry = dbKeyToCol.get(conf.global.dbKey) || {};
      entry.global = headerName;
      dbKeyToCol.set(conf.global.dbKey, entry);

      if (conf.global.divisor || conf.global.multiplier) {
        transformations[conf.global.dbKey] = {
          divisor: conf.global.divisor,
          multiplier: conf.global.multiplier
        };
      }

      if (conf.global.enumMappings) {
        const dbKey = conf.global.dbKey;
        if (!enum_mappings[dbKey]) enum_mappings[dbKey] = {};
        Object.entries(conf.global.enumMappings).forEach(([rawVal, targetVal]) => {
          if (targetVal) {
            if (!enum_mappings[dbKey][targetVal]) enum_mappings[dbKey][targetVal] = [];
            enum_mappings[dbKey][targetVal].push(rawVal);
          }
        });
      }
    }

    Object.entries(conf.typeSpecific).forEach(([opType, specificConf]) => {
      if (specificConf.dbKey) {
        const entry = dbKeyToCol.get(specificConf.dbKey) || {};
        if (!entry.typeSpecific) entry.typeSpecific = {};
        entry.typeSpecific[opType] = headerName;
        dbKeyToCol.set(specificConf.dbKey, entry);

        if (specificConf.divisor || specificConf.multiplier) {
          if (!transformations[specificConf.dbKey]) transformations[specificConf.dbKey] = {};
          transformations[specificConf.dbKey][opType] = {
            divisor: specificConf.divisor,
            multiplier: specificConf.multiplier
          };
        }

        if (specificConf.enumMappings) {
          const dbKey = specificConf.dbKey;
          if (!enum_mappings[dbKey]) enum_mappings[dbKey] = {};
          Object.entries(specificConf.enumMappings).forEach(([rawVal, targetVal]) => {
            if (targetVal) {
              if (!enum_mappings[dbKey][targetVal]) enum_mappings[dbKey][targetVal] = [];
              enum_mappings[dbKey][targetVal].push(rawVal);
            }
          });
        }
      }
    });
  });

  const finalColumns: Record<string, any> = {};
  if (operationTypeColumnIdx.value !== null) {
    finalColumns['operation_type'] = importFileHeaders.value[operationTypeColumnIdx.value];
  }

  dbKeyToCol.forEach((entry, dbKey) => {
    if (entry.typeSpecific && Object.keys(entry.typeSpecific).length > 0) {
      const typeMap: Record<string, string> = { ...entry.typeSpecific };
      if (entry.global) {
        typeMap['global'] = entry.global;
      }
      finalColumns[dbKey] = typeMap;
    } else if (entry.global) {
      finalColumns[dbKey] = entry.global;
    }
  });

  const type_mappings: Record<string, string[]> = {};
  const opField = importFields.value.find(f => f.key === 'operation_type');
  if (opField && opField.enum_values) {
    opField.enum_values.forEach((v: string) => {
      type_mappings[v] = [];
    });
  }

  Object.entries(operationTypeMappings.value).forEach(([rawVal, targetVal]) => {
    if (targetVal) {
      if (!type_mappings[targetVal]) type_mappings[targetVal] = [];
      type_mappings[targetVal].push(rawVal);
    }
  });

  return {
    columns: finalColumns,
    type_mappings,
    enum_mappings,
    transformations
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
        if (saveMappingTemplate.value && mappingTemplateName.value.trim()) {
          const mappingConfig = buildCustomMappingPayload();

          await api.createImportFileSchema({
            name: mappingTemplateName.value.trim(),
            is_public: false,
            delimiter: importDelimiter.value,
            decimal_separator: importDecimalSep.value,
            mappings: JSON.stringify(mappingConfig),
            is_incomplete: true,
          });
          
          importSuccessSummary.value = {
            positions_created: 0,
            operations_imported: 0,
            operations_skipped: 0,
            is_template_only: true,
          };
          loadSchemas();
          emit('success');
          return;
        } else {
          throw new Error('Please fix the validation errors before importing.');
        }
      }
      const mappingConfig = buildCustomMappingPayload();

      if (saveMappingTemplate.value && mappingTemplateName.value.trim()) {
        const newSchema = await api.createImportFileSchema({
          name: mappingTemplateName.value.trim(),
          is_public: false,
          delimiter: importDelimiter.value,
          decimal_separator: importDecimalSep.value,
          mappings: JSON.stringify(mappingConfig),
          is_incomplete: false,
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
  if (e.key === 'Escape' && !isWizardOpen.value) {
    if (showExitConfirm.value) {
      showExitConfirm.value = false;
    } else {
      requestClose();
    }
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
          <h4 style="color: var(--color-success); font-size: 1.1rem; margin-bottom: 0.5rem;">
            {{ importSuccessSummary.is_template_only ? 'Template Saved!' : 'Import Successful!' }}
          </h4>
          <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 1rem;">
            {{ importSuccessSummary.is_template_only ? `The configuration template "${mappingTemplateName}" has been successfully saved.` : 'Your transaction history has been successfully parsed and processed.' }}
          </p>
          <div v-if="!importSuccessSummary.is_template_only" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; background-color: var(--bg-secondary); padding: 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); max-width: 500px; margin: 0 auto;">
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
              <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">Standard CSV files supported</p>
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

            <div style="display: flex; flex-direction: column; gap: 1.5rem; width: 100%;">
              <div>
                <!-- Template select -->
                <div class="form-group" style="max-width: 400px;">
                  <label for="templateSelect">Template Schema</label>
                  <select v-model="selectedSchemaId" id="templateSelect" @change="onSchemaSelect" class="form-control">
                    <option v-for="schema in availableSchemas" :key="schema.id" :value="schema.id">
                      {{ schema.name }} {{ schema.is_public ? '(Public)' : '(Saved)' }} {{ isSchemaIncomplete(schema) ? '[Incomplete]' : '' }}
                    </option>
                    <option :value="-1">Custom Mapping Template...</option>
                  </select>
                  <p v-if="autodetectedSchemaId && selectedSchemaId === autodetectedSchemaId" style="font-size: 0.75rem; color: var(--color-success); margin-top: 0.25rem; font-weight: 500;">
                    ✓ Autodetected format matching this file
                  </p>
                </div>

                <!-- Custom mapping builder form -->
                <div v-if="isCustomMapping" style="border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1.5rem; margin-top: 1rem; background-color: var(--bg-primary);">
                  
                  <!-- STEP 1: Delimiter & OpType mapping -->
                  <div v-if="currentStep === 1">
                    <h4 style="font-size: 0.95rem; margin-bottom: 1.25rem; font-weight: 600;">Step 1: Identify Delimiters & Transaction Type Column</h4>
                    
                    <div style="display: flex; flex-wrap: wrap; gap: 2rem; align-items: start; width: 100%;">
                      <!-- Left Column: Delimiter details and Transaction Type column select -->
                      <div style="flex: 1 1 350px; min-width: 0;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
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

                        <div class="form-group" style="margin-bottom: 0;">
                          <label>Transaction Type Column</label>
                          <select v-model="operationTypeColumnIdx" class="form-control" @change="prepopulateOpTypeGuesses">
                            <option :value="null">-- Select Column --</option>
                            <option v-for="(h, idx) in importFileHeaders" :key="idx" :value="idx">{{ h }}</option>
                          </select>
                          <p style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">
                            Select the column in your CSV file that contains the transaction action type (e.g. "Buy", "Sell", "Dividend").
                          </p>
                        </div>
                      </div>

                      <!-- Right Column: Map File Actions to Database Transaction Types -->
                      <div style="flex: 1 1 350px; min-width: 0;">
                        <div v-if="operationTypeColumnIdx !== null && uniqueOperationTypes.length > 0">
                          <h5 style="font-size: 0.8rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.75rem;">
                            Map File Actions to Database Transaction Types
                          </h5>
                          <div style="display: flex; flex-direction: column; gap: 0.75rem; border: 1px solid var(--border-color); padding: 1rem; border-radius: var(--radius-sm); background-color: var(--bg-secondary); max-height: 250px; overflow-y: auto;">
                            <div v-for="val in uniqueOperationTypes" :key="val" style="display: grid; grid-template-columns: 1fr 1.2fr; gap: 1rem; align-items: center;">
                              <span style="font-size: 0.75rem; font-family: monospace; background-color: var(--bg-primary); padding: 0.25rem 0.5rem; border-radius: var(--radius-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="val">
                                {{ val }}
                              </span>
                              <select v-model="operationTypeMappings[val]" class="form-control" style="font-size: 0.75rem; padding: 0.25rem 0.5rem; height: auto;">
                                <option value="">-- Choose DB Operation --</option>
                                <option v-for="opt in importFields.find(f => f.key === 'operation_type')?.enum_values || []" :key="opt" :value="opt">
                                  {{ opt }}
                                </option>
                              </select>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div style="margin-top: 1.5rem; display: flex; justify-content: flex-end;">
                      <button 
                        @click="goToStep2" 
                        class="btn btn-primary" 
                        :disabled="operationTypeColumnIdx === null || activeDbOpTypes.length === 0"
                      >
                        Next: Configure Column Mappings &rarr;
                      </button>
                    </div>
                  </div>

                  <!-- STEP 2: Columns mapping & live stats verification -->
                  <div v-else-if="currentStep === 2">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                      <h4 style="font-size: 0.95rem; font-weight: 600; margin: 0;">Step 2: Configure Column Mappings</h4>
                      <button @click="currentStep = 1" class="btn btn-sm">&larr; Back to Step 1</button>
                    </div>

                    <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 1.25rem;">
                      Click on any cell in the table below to configure its database field mapping. You can configure mappings globally or specifically for each transaction type.
                    </p>

                    <!-- Interactive Example Table -->
                    <div style="overflow-x: auto; max-width: 100%; border: 1px solid var(--border-color); border-radius: var(--radius-sm); margin-bottom: 1.5rem;">
                      <table class="preview-table" style="margin-top: 0; min-width: 100%;">
                        <thead>
                          <tr>
                            <th style="min-width: 180px; background-color: var(--bg-tertiary); font-weight: 700; color: var(--text-secondary); text-align: center;">
                              Context & Stats
                            </th>
                            <th v-for="(h, idx) in importFileHeaders" :key="idx" style="min-width: 180px; padding: 0.75rem; vertical-align: top;">
                              <div style="font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" :title="h">
                                {{ h }}
                              </div>
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          <!-- Global Mapping row -->
                          <tr style="background-color: var(--accent-light);">
                            <td style="font-weight: 700; color: var(--accent-color); font-size: 0.75rem; text-align: center; vertical-align: middle;">
                              Global Mapping
                            </td>
                            <td v-for="(_, idx) in importFileHeaders" :key="idx" @click="idx !== operationTypeColumnIdx ? openWizard(idx, null) : null" :style="{ cursor: idx !== operationTypeColumnIdx ? 'pointer' : 'default' }" style="font-size: 0.75rem; font-weight: 600; text-align: center; vertical-align: middle;">
                              <div v-if="getColumnMappingLabel(idx) === '(Type-Specific)'" style="color: var(--text-secondary); font-style: italic; font-size: 0.7rem; font-weight: bold;">
                                (Type-Specific)
                              </div>
                              <div v-else-if="getColumnMappingLabel(idx) !== '-- Unmapped --'" style="display: inline-flex; align-items: center; gap: 0.25rem; background-color: var(--accent-color); color: white; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.75rem;">
                                {{ getColumnMappingLabel(idx) }}
                                <span v-if="columnConfigMap[idx]?.global?.divisor" style="font-size: 0.6rem; opacity: 0.9;">(/{{ columnConfigMap[idx].global.divisor }})</span>
                                <span v-if="columnConfigMap[idx]?.global?.multiplier" style="font-size: 0.6rem; opacity: 0.9;">(*{{ columnConfigMap[idx].global.multiplier }})</span>
                              </div>
                              <span v-else style="color: var(--text-tertiary); font-weight: normal;">-- Unmapped --</span>
                            </td>
                          </tr>

                          <!-- Example rows per type -->
                          <tr v-for="example in exampleTransactions" :key="example.opType">
                            <td style="vertical-align: middle; text-align: center;">
                              <div style="display: flex; flex-direction: column; align-items: center; gap: 0.25rem;">
                                <span class="badge" :class="'badge-' + example.opType" style="padding: 0.15rem 0.35rem; font-size: 0.65rem; text-transform: uppercase;">
                                  {{ example.opType }} Example
                                </span>
                                <span v-if="liveValidationStats[example.opType]" :style="{
                                  fontSize: '0.65rem',
                                  fontWeight: 600,
                                  color: liveValidationStats[example.opType].failed > 0 ? 'var(--color-danger)' : 'var(--color-success)'
                                }">
                                  {{ liveValidationStats[example.opType].success }} / {{ liveValidationStats[example.opType].total }} parsed
                                </span>
                              </div>
                            </td>
                            <td v-for="(cell, idx) in example.csvRow" :key="idx" @click="idx !== operationTypeColumnIdx ? openWizard(idx, example.opType) : null" :style="{ cursor: idx !== operationTypeColumnIdx ? 'pointer' : 'default' }" style="vertical-align: middle;">
                              <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                                <span style="font-family: monospace; font-size: 0.75rem; color: var(--text-secondary);">
                                  {{ cell || '—' }}
                                </span>
                                <div v-if="getColumnMappingLabel(idx) === '(Type-Specific)' && getResolvedKeyForCell(idx, example.opType)" style="font-size: 0.65rem; color: var(--accent-color); font-weight: 600;">
                                  → {{ importFields.find(f => f.key === getResolvedKeyForCell(idx, example.opType))?.label }}
                                </div>
                              </div>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <!-- Verification Panel -->
                    <div style="margin-bottom: 1.5rem;">
                      <h5 style="font-size: 0.8rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.75rem; letter-spacing: 0.05em;">
                        Simulation Verification Panel
                      </h5>

                      <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                        <div v-for="type in activeDbOpTypes" :key="type" style="border: 1px solid var(--border-color); border-radius: var(--radius-sm); background-color: var(--bg-secondary); overflow: hidden;">
                          <div style="padding: 0.75rem 1rem; display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-primary); border-bottom: 1px solid var(--border-color);">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                              <span class="badge" :class="'badge-' + type" style="padding: 0.15rem 0.35rem; font-size: 0.65rem; text-transform: uppercase;">
                                {{ type }}
                              </span>
                              <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-primary);">
                                {{ liveValidationStats[type]?.success }} / {{ liveValidationStats[type]?.total }} Rows Passed
                              </span>
                            </div>
                            <button 
                              v-if="liveValidationStats[type]?.failed > 0"
                              @click="toggleErrorView(type)" 
                              class="btn btn-sm btn-danger"
                              style="font-size: 0.7rem; padding: 0.15rem 0.4rem;"
                            >
                              {{ expandedErrors[type] ? 'Hide Errors' : 'Show ' + liveValidationStats[type].failed + ' Failures' }}
                            </button>
                            <span v-else style="font-size: 0.75rem; color: var(--color-success); font-weight: 600;">
                              ✓ Verification Perfect
                            </span>
                          </div>

                          <div v-if="expandedErrors[type] && liveValidationStats[type]?.errors.length > 0" style="padding: 1rem; border-top: 1px solid var(--border-color); max-height: 250px; overflow-y: auto;">
                            <table class="preview-table" style="margin-top: 0; font-size: 0.7rem; width: 100%;">
                              <thead>
                                <tr style="background-color: var(--bg-tertiary);">
                                  <th style="width: 80px;">CSV Row</th>
                                  <th style="width: 150px;">Database Field</th>
                                  <th style="width: 120px;">Raw Value</th>
                                  <th>Failure Reason</th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr v-for="(err, eIdx) in liveValidationStats[type].errors" :key="eIdx">
                                  <td style="font-weight: bold; text-align: center;">#{{ err.rowNum }}</td>
                                  <td style="font-weight: 600; color: var(--text-primary);">{{ err.fieldLabel }}</td>
                                  <td style="font-family: monospace; background-color: var(--bg-primary); padding: 0.15rem 0.35rem;">{{ err.rawValue || '—' }}</td>
                                  <td style="color: var(--color-danger); font-weight: 500;">{{ err.errorMessage }}</td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Validation Warnings Banner -->
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
          v-if="!importSuccessSummary && isCustomMapping && saveMappingTemplate && !isValidCustomMapping"
          @click="handleImport"
          class="btn btn-sm btn-primary"
          :disabled="isImporting || !mappingTemplateName.trim()"
          style="background-color: var(--color-warning); border-color: var(--color-warning); color: white;"
        >
          <Loader v-if="isImporting" style="animation: spin 1.5s linear infinite; width: 14px; height: 14px;" />
          <span v-if="isImporting">Saving template...</span>
          <span v-else>Save Incomplete Template</span>
        </button>
        <button 
          v-else-if="!importSuccessSummary"
          @click="handleImport" 
          class="btn btn-sm btn-primary" 
          :disabled="isImporting || !importFile || (isCustomMapping && !isValidCustomMapping) || (isCustomMapping && saveMappingTemplate && !mappingTemplateName.trim())"
        >
          <Loader v-if="isImporting" style="animation: spin 1.5s linear infinite; width: 14px; height: 14px;" />
          <span v-if="isImporting">Importing data...</span>
          <span v-else-if="isCustomMapping && saveMappingTemplate">Save Template & Import</span>
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

  <!-- Custom exit confirmation dialog -->
  <DiscardChangesConfirmModal 
    :show="showExitConfirm"
    title="Discard Import Session?"
    message="You have uploaded a file and configured mappings. Leaving now will discard this configuration."
    @cancel="showExitConfirm = false" 
    @confirm="emit('close')" 
  />

  <!-- Wizard mapping popup modal -->
  <ColumnMappingWizard
    :show="isWizardOpen"
    :csvHeaderName="wizardCsvHeaderName"
    :exampleValue="wizardExampleValue"
    :importFields="importFields"
    :activeOpType="wizardActiveOpType"
    :delimiter="importDelimiter"
    :decimalSeparator="importDecimalSep"
    :uniqueCsvValues="wizardUniqueValues"
    :initialMapping="wizardInitialMapping"
    @close="isWizardOpen = false"
    @clear="handleWizardClear"
    @save="handleWizardSave"
  />
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
.badge-transfer_in { background-color: rgba(16, 185, 129, 0.15); color: #10b981; }
.badge-transfer_out { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }
.badge-stock_split { background-color: rgba(139, 92, 246, 0.15); color: #8b5cf6; }
.badge-fee { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.badge-tax { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }
.badge-limit_buy { background-color: rgba(37, 99, 235, 0.15); color: #3b82f6; }
.badge-limit_sell { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }
.badge-unknown { background-color: var(--bg-tertiary); color: var(--text-secondary); }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Sticky first column in Step 2 preview table */
.preview-table th:first-child,
.preview-table td:first-child {
  position: sticky;
  left: 0;
  z-index: 5;
  background-color: var(--bg-secondary);
  border-right: 2px solid var(--border-color);
  box-shadow: 2px 0 5px rgba(0, 0, 0, 0.05);
}
.preview-table th:first-child {
  z-index: 6;
  background-color: var(--bg-tertiary);
}
</style>
