const CANDIDATE_DELIMITERS = [',', ';', '\t'];

function countOutsideQuotes(line: string, delim: string): number {
  let count = 0;
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') inQuotes = !inQuotes;
    else if (ch === delim && !inQuotes) count++;
  }
  return count;
}

function sniffDelimiter(firstLine: string): string {
  let best = ',';
  let bestCount = 0;
  for (const delim of CANDIDATE_DELIMITERS) {
    const count = countOutsideQuotes(firstLine, delim);
    if (count > bestCount) {
      best = delim;
      bestCount = count;
    }
  }
  return best;
}

// RFC-4180 state machine: quoted fields may contain delimiters, newlines and "" escapes.
function tokenizeCsv(text: string, delim: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === delim) {
      row.push(field);
      field = '';
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      field = '';
      rows.push(row);
      row = [];
    } else {
      field += ch;
    }
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

export function parseCsvText(text: string): { delimiter: string; headers: string[]; rawRows: string[][] } {
  const firstNewline = text.indexOf('\n');
  const firstLine = firstNewline === -1 ? text : text.slice(0, firstNewline);
  if (!firstLine.trim()) {
    return { delimiter: ',', headers: [], rawRows: [] };
  }
  const delim = sniffDelimiter(firstLine);

  const allRows = tokenizeCsv(text, delim)
    .map(row => row.map(cell => cell.trim()))
    .filter(row => row.some(cell => cell.length > 0));
  if (allRows.length === 0) {
    return { delimiter: delim, headers: [], rawRows: [] };
  }

  return { delimiter: delim, headers: allRows[0], rawRows: allRows.slice(1) };
}

export interface ParsedCsvFile {
  name: string;
  delimiter: string;
  headers: string[];
  rawRows: string[][];
}

// Merge several parsed CSV files into one batch over the UNION of their
// columns. Broker exports only carry the columns used in the export period
// (e.g. Trading212 omits the withholding-tax columns when no dividend was
// paid), and may order shared columns differently — so rows are remapped by
// header name and a column missing from a file reads as empty for its rows,
// exactly like an empty cell would.
//
// Because column sets can legitimately differ, "same export format" is
// guarded heuristically: a file must share at least half of the smaller
// column set (minimum 2) with the batch, otherwise it's likely a different
// provider's export and the whole batch is rejected with a readable error —
// silently misaligned rows would corrupt the import.
export function mergeParsedCsvFiles(
  files: ParsedCsvFile[]
): { delimiter: string; headers: string[]; rawRows: string[][] } {
  const ref = files[0];
  const headers: string[] = [...ref.headers];
  const rawRows: string[][] = ref.rawRows.map(r => [...r]);
  const hasDuplicates = (arr: string[]) => new Set(arr).size !== arr.length;

  files.slice(1).forEach(file => {
    if (file.delimiter !== ref.delimiter) {
      throw new Error(`"${file.name}" uses a different delimiter than "${ref.name}". Import these files separately.`);
    }

    const known = new Set(headers);
    const shared = file.headers.filter(h => known.has(h)).length;
    const smaller = Math.min(file.headers.length, headers.length);
    if (shared < 2 || shared * 2 < smaller) {
      throw new Error(
        `"${file.name}" shares only ${shared} column${shared === 1 ? '' : 's'} with "${ref.name}" — `
        + `it doesn't look like the same export format. Import it separately.`
      );
    }

    const sameOrder = file.headers.length === headers.length
      && file.headers.every((h, i) => h === headers[i]);
    if (sameOrder) {
      file.rawRows.forEach(r => rawRows.push([...r]));
      return;
    }
    // Duplicate header names make a by-name remap ambiguous; they only work
    // when the files match positionally (handled above).
    if (hasDuplicates(headers) || hasDuplicates(file.headers)) {
      throw new Error(`"${file.name}" and "${ref.name}" use duplicate column names; such files must have identical columns.`);
    }

    file.headers.forEach(h => {
      if (!known.has(h)) {
        known.add(h);
        headers.push(h);
      }
    });
    const idxByHeader: Record<string, number> = {};
    file.headers.forEach((h, i) => { idxByHeader[h] = i; });
    file.rawRows.forEach(row => {
      rawRows.push(headers.map(h => (idxByHeader[h] !== undefined ? (row[idxByHeader[h]] ?? '') : '')));
    });
  });

  // Earlier files' rows may predate union columns added by later files.
  rawRows.forEach(row => {
    while (row.length < headers.length) row.push('');
  });

  return { delimiter: ref.delimiter, headers, rawRows };
}

// Broker exports are not always UTF-8 (e.g. Fortuneo ships Latin-1); retry when
// UTF-8 decoding produces replacement characters.
export async function readFileText(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const utf8 = new TextDecoder('utf-8').decode(buffer);
  if (utf8.includes('�')) {
    return new TextDecoder('iso-8859-1').decode(buffer);
  }
  return utf8;
}
