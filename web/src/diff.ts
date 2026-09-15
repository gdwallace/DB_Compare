export type DiffToken = { type: "same" | "del" | "add"; text: string };

export function tokenize(value: string): string[] {
  return value.split(/(\s+|[\\/,:;=])/).filter((part) => part.length > 0);
}

export function diffValues(left: string, right: string): DiffToken[] {
  if (left === right) return [{ type: "same", text: left }];
  const a = tokenize(left);
  const b = tokenize(right);
  const m = a.length;
  const n = b.length;
  const table: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i -= 1) {
    for (let j = n - 1; j >= 0; j -= 1) {
      table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
    }
  }
  const tokens: DiffToken[] = [];
  let i = 0;
  let j = 0;
  while (i < m && j < n) {
    if (a[i] === b[j]) {
      tokens.push({ type: "same", text: a[i] });
      i += 1;
      j += 1;
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      tokens.push({ type: "del", text: a[i] });
      i += 1;
    } else {
      tokens.push({ type: "add", text: b[j] });
      j += 1;
    }
  }
  while (i < m) {
    tokens.push({ type: "del", text: a[i] });
    i += 1;
  }
  while (j < n) {
    tokens.push({ type: "add", text: b[j] });
    j += 1;
  }
  return tokens;
}

export function displayValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "∅";
  return String(value);
}

export function csvEscape(value: string): string {
  if (/[",\n]/.test(value)) return `"${value.replaceAll('"', '""')}"`;
  return value;
}
