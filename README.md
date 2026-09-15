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
cd web && npm install && cd ..
chmod +x scripts/dev.sh
./scripts/dev.sh
```

Then open [http://127.0.0.1:5173](http://127.0.0.1:5173).

1. Put your SQL Server names in `config/servers.json` or `SQL_SERVER_NAMES` in `.env`.
2. Set `SQL_DATABASE` / username / password (or enter them in the form).
3. Choose two names from the dropdowns and click **Compare servers**.

**Load sample data** compares bundled SQLite copies so you can use the UI without live servers.

## Server names

`config/servers.json`:

```json
{
  "servers": [
    { "name": "SQL-PROD-01" },
    { "name": "SQL-UAT-01" }
  ]
}
```

Replace those names with the instances you host. Named instances are supported as `HOSTNAME\\INSTANCENAME`. Connections always use the server name, never an IP.

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
