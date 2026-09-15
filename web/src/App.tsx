import { useEffect, useMemo, useState } from "react";
import { compareServers, fetchConfig, inspectServer, loadDemo } from "./api";
import { csvEscape, displayValue } from "./diff";
import ServerPicker from "./ServerPicker";
import {
  CompareResponse,
  DiffRow,
  DiffStatus,
  PublicConfig,
  STATUS_LABEL,
  ServerInfo,
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
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [servers, setServers] = useState<ServerInfo[]>([]);
  const [leftServer, setLeftServer] = useState("");
  const [rightServer, setRightServer] = useState("");
  const [database, setDatabase] = useState("");
  const [schemaName, setSchemaName] = useState("dbo");
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
      .then((payload) => {
        setConfig(payload);
        setServers(payload.servers);
        setDatabase(payload.database);
        setSchemaName(payload.schema_name || "dbo");
        const maps = payload.servers.filter((server) => (server.credential_group || "appian") === "appian");
        const staging = payload.servers.filter((server) => server.credential_group === "appian_stage");
        if (maps[0]) setLeftServer(maps[0].name);
        if (staging[0]) setRightServer(staging[0].name);
        else if (maps[1]) setRightServer(maps[1].name);
        else if (payload.servers[1]) setRightServer(payload.servers[1].name);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const extras = {
    database: database || undefined,
    schema_name: schemaName || undefined,
  };

  async function testSide(side: "left" | "right") {
    const server = side === "left" ? leftServer : rightServer;
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
      const inspected = await inspectServer(server, extras);
      const msg = `${server}: ${inspected.snapshot.row_count} rows`;
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
      const payload = await compareServers(leftServer, rightServer, {
        includeIdentical: true,
        ...extras,
      });
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
      setLeftServer(payload.left.label);
      setRightServer(payload.right.label);
      setLeftMsg(`${payload.left.label}: ${payload.left.row_count} rows`);
      setRightMsg(`${payload.right.label}: ${payload.right.row_count} rows`);
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
    const headers = [
      "status",
      ...result.key_columns,
      ...result.value_columns.map((column) => `A_${column}`),
      ...result.value_columns.map((column) => `B_${column}`),
    ];
    const lines = [headers.join(",")];
    for (const row of visible) {
      const cells = [
        row.status,
        ...result.key_columns.map((column) => displayValue(row.key[column])),
        ...result.value_columns.map((column) => displayValue(row.left?.[column])),
        ...result.value_columns.map((column) => displayValue(row.right?.[column])),
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
            Pick two SQL Server names and compare INI settings. The same query is run on both
            instances: <code>{config?.query ?? "SELECT SECTION, NAME, INIVALUE, DESCRIPTION, EXPOSED, DATATYPE, DATAFORMAT FROM TBLINISETTINGS"}</code>
          </p>
        </div>
        <div className="hero-actions">
          <button type="button" className="ghost" onClick={runDemo} disabled={busy}>
            Load sample data
          </button>
          <button type="button" className="primary" onClick={runCompare} disabled={busy || !leftServer || !rightServer}>
            {busy ? "Comparing…" : "Compare servers"}
          </button>
        </div>
      </header>

      <div className="panels">
        <ServerPicker
          side="left"
          servers={servers}
          value={leftServer}
          onChange={setLeftServer}
          onTest={() => testSide("left")}
          testing={testing === "left"}
          message={leftMsg}
          error={leftErr}
        />
        <ServerPicker
          side="right"
          servers={servers}
          value={rightServer}
          onChange={setRightServer}
          onTest={() => testSide("right")}
          testing={testing === "right"}
          message={rightMsg}
          error={rightErr}
        />
      </div>

      <section className="shared-creds">
        <label>
          Database
          <input value={database} onChange={(event) => setDatabase(event.target.value)} placeholder="Database name" />
        </label>
        <label>
          Schema
          <input value={schemaName} onChange={(event) => setSchemaName(event.target.value)} />
        </label>
      </section>
      <p className="hint">
        Trimble Maps servers use AppianAppUser2025. Staging servers use AppianAppStageUser2025. Passwords stay in{" "}
        <code>.env</code>, not in the browser.
      </p>

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
            Showing {visible.length} of {result.summary.total} keys · {result.left.label} vs{" "}
            {result.right.label}
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
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visible.length === 0 ? (
                    <tr>
                      <td colSpan={1 + result.key_columns.length + result.value_columns.length}>
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
                          <td key={column} className="value-cell">
                            <PairCell
                              status={row.status}
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
                    const leftValue = displayValue(row.left?.["INIVALUE"]);
                    const rightValue = displayValue(row.right?.["INIVALUE"]);
                    return (
                      <div key={rowKey(row)} className={`ini-line ${row.status}`}>
                        <span className={`status ${row.status}`}>{STATUS_LABEL[row.status]}</span>
                        <div>
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
                          {result.value_columns
                            .filter((column) => column !== "INIVALUE")
                            .map((column) => {
                              const leftExtra = displayValue(row.left?.[column]);
                              const rightExtra = displayValue(row.right?.[column]);
                              if (leftExtra === rightExtra && (leftExtra === "∅" || leftExtra === "—")) {
                                return null;
                              }
                              return (
                                <div key={column} className="ini-extra">
                                  {column}:{" "}
                                  {leftExtra === rightExtra ? (
                                    leftExtra
                                  ) : (
                                    <>
                                      <span className="del">{leftExtra}</span>
                                      <span className="sep"> → </span>
                                      <span className="add">{rightExtra}</span>
                                    </>
                                  )}
                                </div>
                              );
                            })}
                        </div>
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
          Choose two server names from the dropdowns, then compare. Use sample data to preview the
          visualization without connecting to live SQL.
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

function PairCell({
  status,
  left,
  right,
}: {
  status: DiffStatus;
  left: string;
  right: string;
}) {
  if (status === "left_only") return <code>{left === "∅" ? "—" : left}</code>;
  if (status === "right_only") return <code>{right === "∅" ? "—" : right}</code>;
  if (left === right) return <code>{left}</code>;
  return (
    <code>
      <span className="del">{left}</span>
      <span className="sep"> → </span>
      <span className="add">{right}</span>
    </code>
  );
}

function rowKey(row: DiffRow): string {
  return `${row.status}:${Object.values(row.key).join("|")}`;
}
