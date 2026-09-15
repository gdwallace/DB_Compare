import type { Driver, SqlConnection } from "./types";

type Props = {
  side: "left" | "right";
  value: SqlConnection;
  onChange: (next: SqlConnection) => void;
  onTest: () => void;
  testing: boolean;
  message?: string;
  error?: string;
};

export default function ConnectionForm({
  side,
  value,
  onChange,
  onTest,
  testing,
  message,
  error,
}: Props) {
  const mssql = value.driver === "mssql";
  const update = (patch: Partial<SqlConnection>) => onChange({ ...value, ...patch });

  return (
    <section className={`panel panel-${side}`}>
      <header className="panel-head">
        <span className="instance-mark">{side === "left" ? "A" : "B"}</span>
        <input
          className="label-input"
          value={value.label}
          onChange={(event) => update({ label: event.target.value })}
          aria-label={`${side} instance name`}
        />
      </header>

      <div className="field-grid">
        <label>
          Driver
          <select
            value={value.driver}
            onChange={(event) => update({ driver: event.target.value as Driver })}
          >
            <option value="mssql">SQL Server</option>
            <option value="sqlite">SQLite (file)</option>
          </select>
        </label>
        {mssql ? (
          <>
            <label>
              Host
              <input
                value={value.host ?? ""}
                onChange={(event) => update({ host: event.target.value })}
                placeholder="sql-prod.internal"
              />
            </label>
            <label>
              Port
              <input
                type="number"
                value={value.port}
                onChange={(event) => update({ port: Number(event.target.value) })}
              />
            </label>
            <label>
              Database
              <input
                value={value.database}
                onChange={(event) => update({ database: event.target.value })}
              />
            </label>
            <label>
              Username
              <input
                value={value.username ?? ""}
                onChange={(event) => update({ username: event.target.value })}
                autoComplete="off"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={value.password ?? ""}
                onChange={(event) => update({ password: event.target.value })}
                autoComplete="new-password"
              />
            </label>
            <label>
              Schema
              <input
                value={value.schema_name ?? ""}
                onChange={(event) => update({ schema_name: event.target.value || null })}
              />
            </label>
          </>
        ) : (
          <label className="wide">
            SQLite path
            <input
              value={value.database}
              onChange={(event) => update({ database: event.target.value, schema_name: null })}
              placeholder="/path/to/instance.sqlite"
            />
          </label>
        )}
        <label className="wide">
          Table
          <input
            value={value.table}
            onChange={(event) => update({ table: event.target.value })}
          />
        </label>
      </div>

      <div className="panel-actions">
        <button type="button" className="ghost" onClick={onTest} disabled={testing}>
          {testing ? "Testing…" : "Test connection"}
        </button>
      </div>
      {message ? <p className="ok-msg">{message}</p> : null}
      {error ? <p className="err-msg">{error}</p> : null}
    </section>
  );
}
