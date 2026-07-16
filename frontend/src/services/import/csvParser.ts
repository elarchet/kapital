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

// Merge several parsed CSV files into one batch using the first file's column
// order. Broker exports drift over time, so later files may order the same
// columns differently — their rows are remapped by header name. Files whose
// delimiter or column set doesn't match the first file throw a user-readable
// error: silently misaligned rows would corrupt the import.
export function mergeParsedCsvFiles(
  files: ParsedCsvFile[]
): { delimiter: string; headers: string[]; rawRows: string[][] } {
  const ref = files[0];
  const rawRows: string[][] = [...ref.rawRows];

  files.slice(1).forEach(file => {
    if (file.delimiter !== ref.delimiter) {
      throw new Error(`"${file.name}" uses a different delimiter than "${ref.name}". Import these files separately.`);
    }
    const sameOrder = file.headers.length === ref.headers.length
      && file.headers.every((h, i) => h === ref.headers[i]);
    if (sameOrder) {
      rawRows.push(...file.rawRows);
      return;
    }
    // Same column set in a different order: remap by header name. Duplicate
    // header names make the remap ambiguous, so they must match positionally.
    const sameSet = file.headers.length === ref.headers.length
      && [...file.headers].sort().join('\x1f') === [...ref.headers].sort().join('\x1f');
    const hasDuplicates = new Set(ref.headers).size !== ref.headers.length;
    if (!sameSet || hasDuplicates) {
      throw new Error(`"${file.name}" has different columns than "${ref.name}". Import files with identical columns together.`);
    }
    const idxByHeader: Record<string, number> = {};
    file.headers.forEach((h, i) => { idxByHeader[h] = i; });
    file.rawRows.forEach(row => {
      rawRows.push(ref.headers.map(h => row[idxByHeader[h]] ?? ''));
    });
  });

  return { delimiter: ref.delimiter, headers: ref.headers, rawRows };
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
