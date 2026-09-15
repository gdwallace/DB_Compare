import { useEffect, useMemo, useState } from "react";
import ConnectionForm from "./ConnectionForm";
import { compareInstances, fetchConfig, inspectConnection, loadDemo } from "./api";
import { csvEscape, diffValues, displayValue } from "./diff";
import {
  CompareResponse,
  DiffRow,
  DiffStatus,
  STATUS_LABEL,
  SqlConnection,
  emptyConnection,
} from "./types";

type Filter = "all" | "differences" | DiffStatus;
type ViewMode = "table" | "ini";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "differences", label: "Differences" },
  { id: "changed", label: "Changed" },
  { id: "left_only", label: "Only A" },
  { id: "right_only", label: "Only B" },
  { id: "identical", label: "Matches" },
];

export default function App() {
  const [left, setLeft] = useState<SqlConnection>(emptyConnection("SQL Instance A"));
  const [right, setRight] = useState<SqlConnection>(emptyConnection("SQL Instance B"));
  const [testing, setTesting] = useState<"left" | "right" | null>(null);
  const [leftMsg, setLeftMsg] = useState<string>();
  const [rightMsg, setRightMsg] = useState<string>();
  const [leftErr, setLeftErr] = useState<string>();
  const [rightErr, setRightErr] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [filter, setFilter] = useState<Filter>("differences");
  const [query, setQuery] = useState("");
  const [view, setView] = useState<ViewMode>("table");
  const [section, setSection] = useState<string>("all");

  useEffect(() => {
    fetchConfig()
      .then((config) => {
        setLeft(stripPublic(config.left, "SQL Instance A"));
        setRight(stripPublic(config.right, "SQL Instance B"));
      })
      .catch(() => undefined);
  }, []);

  async function testSide(side: "left" | "right") {
    const connection = side === "left" ? left : right;
    setTesting(side);
    setError(undefined);
    if (side === "left") {
      setLeftErr(undefined);
      setLeftMsg(undefined);
    } else {
      setRightErr(undefined);
      setRightMsg(undefined);
    }
    try {
      const inspected = await inspectConnection(connection);
      const msg = `${inspected.snapshot.table}: ${inspected.snapshot.row_count} rows · keys ${inspected.suggested_key_columns.join(", ") || "—"}`;
      if (side === "left") setLeftMsg(msg);
      else setRightMsg(msg);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (side === "left") setLeftErr(message);
      else setRightErr(message);
    } finally {
      setTesting(null);
    }
  }

  async function runCompare() {
    setBusy(true);
    setError(undefined);
    try {
      const payload = await compareInstances(left, right, true);
      setResult(payload);
      setFilter("differences");
      setSection("all");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function runDemo() {
    setBusy(true);
    setError(undefined);
    try {
      const payload = await loadDemo(true);
      setResult(payload);
      setLeft({
        ...emptyConnection(payload.left.label),
        driver: "sqlite",
        database: payload.left.database,
        schema_name: null,
        table: payload.left.table,
      });
      setRight({
        ...emptyConnection(payload.right.label),
        driver: "sqlite",
        database: payload.right.database,
        schema_name: null,
        table: payload.right.table,
      });
      setLeftMsg(`${payload.left.table}: ${payload.left.row_count} rows`);
      setRightMsg(`${payload.right.table}: ${payload.right.row_count} rows`);
      setLeftErr(undefined);
      setRightErr(undefined);
      setFilter("differences");
      setSection("all");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const sectionColumn = result?.key_columns[0];
  const identColumn = result?.key_columns[1] ?? result?.key_columns[0];
  const sections = useMemo(() => {
    if (!result || !sectionColumn) return [];
    return Array.from(new Set(result.rows.map((row) => String(row.key[sectionColumn] ?? "")))).sort();
  }, [result, sectionColumn]);

  const visible = useMemo(() => {
    if (!result) return [];
    const needle = query.trim().toLowerCase();
    return result.rows.filter((row) => {
      if (filter === "differences" && row.status === "identical") return false;
      if (filter !== "all" && filter !== "differences" && row.status !== filter) return false;
      if (section !== "all" && sectionColumn && String(row.key[sectionColumn] ?? "") !== section) {
        return false;
      }
      if (!needle) return true;
      const haystack = [
        ...Object.values(row.key),
        ...Object.values(row.left ?? {}),
        ...Object.values(row.right ?? {}),
        row.status,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [filter, query, result, section, sectionColumn]);

  const grouped = useMemo(() => {
    if (!sectionColumn) return [{ name: "", rows: visible }];
    const map = new Map<string, DiffRow[]>();
    for (const row of visible) {
      const name = String(row.key[sectionColumn] ?? "(none)");
      const list = map.get(name) ?? [];
      list.push(row);
      map.set(name, list);
    }
    return Array.from(map.entries()).map(([name, rows]) => ({ name, rows }));
  }, [sectionColumn, visible]);

  function exportCsv() {
    if (!result) return;
    const valueColumns = result.value_columns;
    const headers = [
      "status",
      ...result.key_columns,
      ...valueColumns.map((column) => `A_${column}`),
      ...valueColumns.map((column) => `B_${column}`),
    ];
    const lines = [headers.join(",")];
    for (const row of visible) {
      const cells = [
        row.status,
        ...result.key_columns.map((column) => displayValue(row.key[column])),
        ...valueColumns.map((column) => displayValue(row.left?.[column])),
        ...valueColumns.map((column) => displayValue(row.right?.[column])),
      ];
      lines.push(cells.map((cell) => csvEscape(cell)).join(","));
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "tblinisettings-compare.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">DB Compare</p>
          <h1>TBLINISETTINGS</h1>
          <p className="lede">
            Read the INI-style settings table from two SQL instances you host and highlight what
            drifted: changed values, keys only on A, and keys only on B.
          </p>
        </div>
        <div className="hero-actions">
          <button type="button" className="ghost" onClick={runDemo} disabled={busy}>
            Load sample data
          </button>
          <button type="button" className="primary" onClick={runCompare} disabled={busy}>
            {busy ? "Comparing…" : "Compare instances"}
          </button>
        </div>
      </header>

      <div className="panels">
        <ConnectionForm
          side="left"
          value={left}
          onChange={setLeft}
          onTest={() => testSide("left")}
          testing={testing === "left"}
          message={leftMsg}
          error={leftErr}
        />
        <ConnectionForm
          side="right"
          value={right}
          onChange={setRight}
          onTest={() => testSide("right")}
          testing={testing === "right"}
          message={rightMsg}
          error={rightErr}
        />
      </div>

      {error ? <div className="banner error">{error}</div> : null}
      {result?.warnings.map((warning) => (
        <div className="banner warn" key={warning}>
          {warning}
        </div>
      ))}

      {result ? (
        <section className="results">
          <div className="summary">
            <Stat label={result.left.label} value={result.left.row_count} hint="rows" tone="left" />
            <Stat label={result.right.label} value={result.right.row_count} hint="rows" tone="right" />
            <Stat label="Changed" value={result.summary.changed} tone="changed" />
            <Stat label="Only A" value={result.summary.left_only} tone="left" />
            <Stat label="Only B" value={result.summary.right_only} tone="right" />
            <Stat label="Match" value={result.summary.identical} />
          </div>

          <div className="toolbar">
            <div className="filters" role="tablist" aria-label="Row filter">
              {FILTERS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={filter === item.id}
                  className={filter === item.id ? "chip active" : "chip"}
                  onClick={() => setFilter(item.id)}
                >
                  {item.label}
                  {item.id === "all" ? ` ${result.summary.total}` : ""}
                  {item.id === "differences"
                    ? ` ${result.summary.changed + result.summary.left_only + result.summary.right_only}`
                    : ""}
                </button>
              ))}
            </div>
            <div className="toolbar-right">
              <select value={section} onChange={(event) => setSection(event.target.value)}>
                <option value="all">All sections</option>
                {sections.map((name) => (
                  <option key={name} value={name}>
                    {name || "(blank)"}
                  </option>
                ))}
              </select>
              <input
                className="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search keys or values"
              />
              <div className="view-toggle">
                <button
                  type="button"
                  className={view === "table" ? "active" : ""}
                  onClick={() => setView("table")}
                >
                  Table
                </button>
                <button
                  type="button"
                  className={view === "ini" ? "active" : ""}
                  onClick={() => setView("ini")}
                >
                  INI
                </button>
              </div>
              <button type="button" className="ghost" onClick={exportCsv}>
                Export CSV
              </button>
            </div>
          </div>

          <p className="showing">
            Showing {visible.length} of {result.summary.total} keys · compared on{" "}
            {result.key_columns.join(" + ")} → {result.value_columns.join(", ")}
          </p>

          {view === "table" ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Status</th>
                    {result.key_columns.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                    {result.value_columns.map((column) => (
                      <th key={`a-${column}`}>{result.left.label} · {column}</th>
                    ))}
                    {result.value_columns.map((column) => (
                      <th key={`b-${column}`}>{result.right.label} · {column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visible.length === 0 ? (
                    <tr>
                      <td colSpan={3 + result.key_columns.length + result.value_columns.length * 2}>
                        No settings match this filter.
                      </td>
                    </tr>
                  ) : (
                    visible.map((row) => (
                      <tr key={rowKey(row)} className={row.status}>
                        <td>
                          <span className={`status ${row.status}`}>{STATUS_LABEL[row.status]}</span>
                        </td>
                        {result.key_columns.map((column) => (
                          <td key={column} className="key-cell">
                            {displayValue(row.key[column])}
                          </td>
                        ))}
                        {result.value_columns.map((column) => (
                          <td key={`a-${column}`} className="value-cell">
                            <ValueCell
                              status={row.status}
                              side="left"
                              left={displayValue(row.left?.[column])}
                              right={displayValue(row.right?.[column])}
                            />
                          </td>
                        ))}
                        {result.value_columns.map((column) => (
                          <td key={`b-${column}`} className="value-cell">
                            <ValueCell
                              status={row.status}
                              side="right"
                              left={displayValue(row.left?.[column])}
                              right={displayValue(row.right?.[column])}
                            />
                          </td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="ini-view">
              {grouped.map((group) => (
                <article key={group.name} className="ini-section">
                  <h2>[{group.name}]</h2>
                  {group.rows.map((row) => {
                    const ident = identColumn ? displayValue(row.key[identColumn]) : "value";
                    const leftValue = displayValue(row.left?.[result.value_columns[0]]);
                    const rightValue = displayValue(row.right?.[result.value_columns[0]]);
                    return (
                      <div key={rowKey(row)} className={`ini-line ${row.status}`}>
                        <span className={`status ${row.status}`}>{STATUS_LABEL[row.status]}</span>
                        <code>
                          {ident} ={" "}
                          {row.status === "changed" ? (
                            <>
                              <span className="del">{leftValue}</span>
                              <span className="sep"> → </span>
                              <span className="add">{rightValue}</span>
                            </>
                          ) : (
                            <span>{row.status === "right_only" ? rightValue : leftValue}</span>
                          )}
                        </code>
                      </div>
                    );
                  })}
                </article>
              ))}
            </div>
          )}
        </section>
      ) : (
        <p className="empty">
          Point A and B at the two SQL instances, test each connection, then compare. Use sample
          data first if you want to see the visualization without live servers.
        </p>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: number;
  hint?: string;
  tone?: string;
}) {
  return (
    <div className={`stat ${tone ?? ""}`}>
      <span className="stat-label">{label}</span>
      <strong>
        {value}
        {hint ? <em>{hint}</em> : null}
      </strong>
    </div>
  );
}

function ValueCell({
  status,
  side,
  left,
  right,
}: {
  status: DiffStatus;
  side: "left" | "right";
  left: string;
  right: string;
}) {
  if (status !== "changed") {
    const value = side === "left" ? left : right;
    return <code>{value === "∅" && status !== "identical" ? "—" : value}</code>;
  }
  const tokens = diffValues(left, right);
  return (
    <code>
      {tokens
        .filter((token) => (side === "left" ? token.type !== "add" : token.type !== "del"))
        .map((token, index) => (
          <span key={`${token.type}-${index}`} className={token.type === "same" ? undefined : token.type}>
            {token.text}
          </span>
        ))}
    </code>
  );
}

function rowKey(row: DiffRow): string {
  return `${row.status}:${Object.values(row.key).join("|")}`;
}

function stripPublic(connection: SqlConnection, fallbackLabel: string): SqlConnection {
  return {
    ...emptyConnection(fallbackLabel),
    ...connection,
    password: "",
    host: connection.host ?? "",
    username: connection.username ?? "",
    schema_name: connection.schema_name ?? (connection.driver === "sqlite" ? null : "dbo"),
  };
}
