import type { ServerInfo } from "./types";
import { serverLabel } from "./types";

type Props = {
  side: "left" | "right";
  servers: ServerInfo[];
  value: string;
  onChange: (serverName: string) => void;
  onTest: () => void;
  testing: boolean;
  message?: string;
  error?: string;
};

export default function ServerPicker({
  side,
  servers,
  value,
  onChange,
  onTest,
  testing,
  message,
  error,
}: Props) {
  return (
    <section className={`panel panel-${side}`}>
      <header className="panel-head">
        <span className="instance-mark">{side === "left" ? "A" : "B"}</span>
        <h2>{side === "left" ? "Compare from" : "Compare to"}</h2>
      </header>

      <label className="wide">
        SQL Server name
        <select value={value} onChange={(event) => onChange(event.target.value)} aria-label={`${side} server name`}>
          <option value="" disabled>
            {servers.length ? "Select a server…" : "No servers configured"}
          </option>
          {servers.map((server) => (
            <option key={server.name} value={server.name}>
              {serverLabel(server)}
            </option>
          ))}
        </select>
      </label>
      <p className="hint">Connected by server name, not IP address.</p>

      <div className="panel-actions">
        <button type="button" className="ghost" onClick={onTest} disabled={testing || !value}>
          {testing ? "Testing…" : "Test connection"}
        </button>
      </div>
      {message ? <p className="ok-msg">{message}</p> : null}
      {error ? <p className="err-msg">{error}</p> : null}
    </section>
  );
}
