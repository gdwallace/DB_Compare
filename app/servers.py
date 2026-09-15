from __future__ import annotations

import json
from pathlib import Path

from app.models import AppSettings, ServerInfo, SqlConnection

SERVERS_FILE = Path(__file__).resolve().parent.parent / "config" / "servers.json"


def load_server_catalog(settings: AppSettings | None = None) -> list[ServerInfo]:
    settings = settings or AppSettings()
    servers: list[ServerInfo] = []
    seen: set[str] = set()

    if SERVERS_FILE.exists():
        payload = json.loads(SERVERS_FILE.read_text(encoding="utf-8"))
        for item in payload.get("servers", []):
            server = ServerInfo.model_validate(item)
            key = server.name.casefold()
            if key in seen:
                continue
            seen.add(key)
            servers.append(server)

    for raw in settings.sql_server_names.split(","):
        name = raw.strip()
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        servers.append(ServerInfo(name=name, label=name))

    return servers


def find_server(name: str, settings: AppSettings | None = None) -> ServerInfo | None:
    needle = name.strip().casefold()
    for server in load_server_catalog(settings):
        if server.name.casefold() == needle:
            return server
    return None


def resolve_server(
    name: str,
    settings: AppSettings,
    *,
    database: str | None = None,
    username: str | None = None,
    password: str | None = None,
    schema_name: str | None = None,
) -> SqlConnection:
    server = find_server(name, settings)
    if server is None:
        known = ", ".join(item.name for item in load_server_catalog(settings)) or "(none configured)"
        raise ValueError(
            f"Unknown server '{name}'. Choose a name from the dropdown catalog: {known}."
        )

    db_name = database or server.database or settings.sql_database
    if not db_name:
        raise ValueError("Database name is required. Set SQL_DATABASE or enter it in the form.")

    return SqlConnection(
        label=server.label or server.name,
        driver="mssql",
        host=server.name,
        port=server.port or settings.sql_port,
        database=db_name,
        username=username or settings.sql_username or None,
        password=password or settings.sql_password or None,
        schema_name=schema_name or server.schema_name or settings.sql_schema or "dbo",
        table="TBLINISETTINGS",
    )
