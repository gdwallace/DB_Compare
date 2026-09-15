# DB Compare — TBLINISETTINGS

Visualize `TBLINISETTINGS` across two hosted SQL Server instances.

The same query is run on each selected server:

```sql
SELECT SECTION, NAME, INIVALUE, DESCRIPTION, EXPOSED, DATATYPE, DATAFORMAT
FROM TBLINISETTINGS
```

Rows are joined on `SECTION` + `NAME`. The viewer then shows:

- **Changed** — same setting, different `INIVALUE` / description / flags
- **Only A / Only B** — setting exists on one server
- **Match** — identical on both

Pick the two servers from dropdowns (SQL Server **names**, not IP addresses).

## Run locally

From the repo root:

```bash
./scripts/launch.sh
```

or:

```bash
python3 scripts/launch.py
```

or, on Windows from the repo root (a new Command Prompt after installing Node.js):

```bat
scripts\launch.bat
```

That creates `.venv`, installs Python and Node packages, copies `.env.example` to `.env` if needed, then starts the API and UI.

Windows needs **Node.js LTS** from https://nodejs.org (the official installer, not only the Microsoft Store). Installing Node does not update PATH in windows that were already open, and Python cannot launch a bare `npm` command. `launch.py` / `launch.bat` now:

- look for `C:\Program Files\nodejs` even when PATH is stale
- skip Microsoft Store `WindowsApps` stubs
- run npm as `node.exe …\npm-cli.js` (or `cmd.exe /c npm.cmd`) instead of `CreateProcess("npm")`

After installing Node, close every terminal, open a new Command Prompt in the repo, then:

```bat
where node
where npm
npm -v
scripts\launch.bat
```

If Node is missing but `web/dist` already exists, the launcher serves the built UI at http://127.0.0.1:8000 instead.

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Fill `APPIAN_PASSWORD` and `APPIAN_STAGE_PASSWORD` in `.env` before comparing live servers.

1. Choose two server names from the dropdowns.
2. Enter the **production** database name on A and the **staging** database name on B (they can differ). Schema defaults to `dbo`.
3. Click **Compare servers**.

Each server uses the login for its group. Passwords stay in `.env` and are not sent to the browser.

**Load sample data** compares bundled SQLite copies so you can use the UI without live servers.

## Servers

Configured in `config/servers.json`:

| Group | Login | Servers |
| --- | --- | --- |
| Trimble Maps | AppianAppUser2025 | sql-butterfly, sql-tadpole, sql-milkyway, sql-fireworks, law-sql01 (`.appian.trimblemaps.com`) |
| Staging | AppianAppStageUser2025 | sql01.staging, law-sql02.staging (`.staging.appiantesting.com`) |

Set `APPIAN_PASSWORD` and `APPIAN_STAGE_PASSWORD` in `.env`. Never commit that file.

## Production-style serve

```bash
cd web && npm run build && cd ..
python -m app
```

The API then serves the built UI on [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Tests

```bash
pytest
```
