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

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # fill APPIAN_PASSWORD and APPIAN_STAGE_PASSWORD
cd web && npm install && cd ..
chmod +x scripts/dev.sh
./scripts/dev.sh
```

Then open [http://127.0.0.1:5173](http://127.0.0.1:5173).

1. Choose two server names from the dropdowns.
2. Enter the database name (and schema if not `dbo`).
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
