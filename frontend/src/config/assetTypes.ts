/**
 * Shared asset-type presentation config: one fixed color per asset class.
 * Colors follow the entity (asset class), never a rank — charts, badges and
 * legends must all read from this single map.
 */

export type AssetTypeKey =
  | 'cash'
  | 'crypto'
  | 'etf'
  | 'stock'
  | 'bond'
  | 'commodity'
  | 'fund'
  | 'other';

export const ASSET_TYPE_COLORS: Record<AssetTypeKey, string> = {
  stock: '#2563eb', // Indigo
  crypto: '#7c3aed', // Purple
  etf: '#0891b2', // Cyan
  bond: '#0d9488', // Teal
  cash: '#16a34a', // Green
  commodity: '#d97706', // Amber
  fund: '#db2777', // Pink
  other: '#4b5563', // Cool Slate
};

export const ASSET_TYPE_LABELS: Record<AssetTypeKey, string> = {
  stock: 'Shares',
  crypto: 'Crypto',
  etf: 'ETF',
  bond: 'Bonds',
  cash: 'Cash',
  commodity: 'Commodities',
  fund: 'Funds',
  other: 'Other',
};

export const assetTypeColor = (type: string): string =>
  ASSET_TYPE_COLORS[type as AssetTypeKey] ?? '#64748b';

export const assetTypeLabel = (type: string): string =>
  ASSET_TYPE_LABELS[type as AssetTypeKey] ?? type;
