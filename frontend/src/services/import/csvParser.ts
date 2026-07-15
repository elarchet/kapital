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
