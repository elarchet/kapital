export function parseCsvText(text: string): { delimiter: string; headers: string[]; rawRows: string[][] } {
  const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length === 0) {
    return { delimiter: ',', headers: [], rawRows: [] };
  }
  let delim = ',';
  const firstLine = lines[0];
  if (firstLine.includes(';')) delim = ';';
  else if (firstLine.includes('\t')) delim = '\t';

  const headers = firstLine.split(delim).map(h => h.trim().replace(/^["']|["']$/g, ''));
  const rawRows = lines.slice(1).map(line =>
    line.split(delim).map(cell => cell.trim().replace(/^["']|["']$/g, ''))
  ).filter(row => row.length > 0 && row.some(cell => cell.length > 0));

  return { delimiter: delim, headers, rawRows };
}
