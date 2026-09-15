# DB Compare — TBLINISETTINGS

Visualize `TBLINISETTINGS` across two SQL instances and see what drifted.

The app reads the table from instance A and instance B, treats INI-style columns (section + key → value) as the join, and shows:

- **Changed** — same setting, different value
- **Only A / Only B** — setting exists on one instance
- **Match** — identical on both

There is a table view and an INI-style view, plus CSV export of the current filter.

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

- **Load sample data** compares two bundled SQLite copies of `TBLINISETTINGS` so you can use the UI without live servers.
- For real instances, fill in host / database / credentials on A and B (SQL authentication), click **Test connection**, then **Compare instances**.

Optional defaults can live in `.env` (see `.env.example`). Passwords are never returned by the config API.

## What it expects

Default table name is `TBLINISETTINGS`. Column detection looks for INI-like names:

| Role | Typical columns |
| --- | --- |
| Key | `SECTION`, `IDENT` / `ENTRY` / `KEY` |
| Value | `VALUE` / `ENTRYVALUE` |

If your names differ, test the connection first — the inspect response includes the guessed key and value columns. Schema defaults to `dbo` on SQL Server.

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
