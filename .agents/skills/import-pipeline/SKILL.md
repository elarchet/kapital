---
name: import-pipeline
description: CSV import architecture — template mappings contract, formula engine, hash/dedup keys, metadata-driven field rules, and the drag-and-drop wizard state model.
---

# Import Pipeline Architecture

Load this skill before touching anything under `backend/src/services/import_*`,
`frontend/src/services/import/`, or `frontend/src/components/import/`.

## 1. Data flow

`RawTransaction` (immutable import) → `Allocation` (split) → `Position` → `Portfolio`.
Imports are idempotent per **financial account** (not per portfolio): dedup keys from
`compute_dedup_key` are compared against every prior import into that account
(`import_service.py` → `load_existing_dedup_keys`).

## 2. The mappings contract (template JSON)

Templates (`ImportFileSchema.mappings`) are produced by `config.ts:buildCustomMappingPayload`
and parsed back by `parseSchemaMappings`; the backend consumes the same JSON. Key shapes:

- `columns`: `dbKey → {opType: csvHeader}` — **per-op-type objects, not flat strings**.
  Legacy flat-string values still parse. Any backend code iterating `columns.values()`
  must handle both shapes (`autodetect_schema` broke on this once).
- `type_mappings`: `dbOpType → [rawAction, ...]`.
- `formulas`: `dbKey → {opType: [token, ...]}` with tokens like
  `{"col": "Qty"}` / `{"op": "*"}` / `{"num": "100"}`.
- `hash_columns`: `opType → [csvHeader, ...]` — subset feeding both the auto
  transaction ID and the dedup key (empty/absent = all columns; ≥2 enforced).
- `enrich_asset_names` / `enrich_transaction_ids`: `opType → never|when_empty|always`.
- Cascade resolution for per-op-type values: rawAction → op_type → global
  (`resolve_config_value` backend, mirrored in frontend services).

**Single source of field rules**: `backend/src/services/import_metadata.py` — each field
declares `op_types` (where it appears) and `required_for`. Never hardcode
required/relevant maps in the frontend; it reads them from `/portfolios/import-metadata`.

## 3. Formula engine

- Backend `import_formula.py`: shunting-yard → RPN, Decimal-only, 64-token cap, no eval.
  Null semantics: blank column = 0 for `+`/`−`; null propagates through `×`/`÷`; ÷0 → null.
- `resolve_numeric_value()` is the single choke point for every numeric field, so any
  numeric field is formula-mappable.
- Frontend `services/import/formula.ts` is a preview-only float mirror — backend Decimal
  is authoritative. A formula is anchored to its first `col` token's column when
  round-tripping through a template.

## 4. Wizard state model (frontend)

- `useImportWizard` owns `columnConfigMap[colId].typeSpecific[opTypeOrRawAction] = ColMapping`
  plus `opTypeSettings[opType] = {autoTransactionId, hashColumns}` (auto-ID cannot hang
  off a column mapping — some brokers have no ID column).
- `useFieldSlots` projects that map into per-op-type slot views; `useDragDrop` implements
  three assignment paths: native HTML5 drag, click-to-arm chip → click slot (Escape
  disarms), per-slot dropdown.
- `FieldConfigModal` auto-opens on enum drops and datetime auto-parse failures; it has a
  dirty-check confirm on Cancel/Escape (`useFieldConfigModal.isDirty`).
- Enrichment default is **`when_empty` everywhere** (backend
  `resolve_enrich_option`, `config.ts` parse, modal). Don't reintroduce a `never` default
  on one side only: the live validator treats an unmapped-but-enrichable `name` without a
  mapped ticker as a row parse failure, so defaults must agree.
- On import success the modal stays open showing `ImportSuccessSummary`; the parent view
  must only refresh data on `@success` and close on `@close` (Done button).

## 5. Gotchas that already bit us

- `parse_decimal_safe`: strip thousands separators **before** swapping the decimal
  separator, or comma-decimal values scale ×10 per digit.
- File decode falls back to latin-1 (Fortuneo exports are not UTF-8).
- Changing `hash_columns` changes dedup keys: already-imported rows re-import. The UI
  warns; keep that warning.
- Real broker exports for regression tests live in gitignored `data/`
  (`test_import_real_files.py` auto-skips without it).
