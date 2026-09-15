import type { ServerInfo } from "./types";
import { groupedServers, serverLabel } from "./types";

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
  const selected = servers.find((server) => server.name === value);
  const groups = groupedServers(servers);

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
          {groups.map((group) => (
            <optgroup key={group.group} label={group.label}>
              {group.servers.map((server) => (
                <option key={server.name} value={server.name}>
                  {serverLabel(server)}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
      <p className="hint">
        {selected?.username
          ? `Connects as ${selected.username}${selected.password_configured ? "" : " (password missing in .env)"}`
          : "Connected by server name, not IP address."}
      </p>

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
