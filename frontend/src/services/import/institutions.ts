/**
 * Built-in institution parser profiles for the import wizard.
 *
 * Mirrors the backend ``INSTITUTION_PROFILES`` registry: an import template
 * targets a single institution (every row in an uploaded file is assumed to
 * originate from it). The selected ``institution_key`` is persisted on the
 * template and passed to the import pipeline.
 */

export interface InstitutionOption {
    value: string;
    label: string;
}

export const INSTITUTION_OPTIONS: InstitutionOption[] = [
    { value: 'trading212', label: 'Trading 212' },
    { value: 'custom', label: 'Custom / Other' },
];

export const DEFAULT_INSTITUTION_KEY = 'trading212';
