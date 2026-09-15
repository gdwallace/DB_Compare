from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.compare import compare_tables
from app.db import DatabaseError, inspect_connection, load_table
from app.demo import LEFT_SETTINGS, RIGHT_SETTINGS, demo_connections, demo_snapshot
from app.models import (
    AppSettings,
    CompareRequest,
    CompareResponse,
    InspectRequest,
    InspectResponse,
    InstanceSnapshot,
    PublicConfig,
    SqlConnection,
)
from app.query import KEY_COLUMNS, SETTINGS_SELECT, TABLE_NAME, VALUE_COLUMNS
from app.servers import load_server_catalog, resolve_server

settings = AppSettings()
app = FastAPI(title="TBLINISETTINGS Compare", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config", response_model=PublicConfig)
def public_config() -> PublicConfig:
    return PublicConfig(
        servers=load_server_catalog(settings),
        database=settings.sql_database,
        username=settings.sql_username or None,
        schema_name=settings.sql_schema,
        table=TABLE_NAME,
        query=SETTINGS_SELECT,
    )


@app.get("/api/servers")
def list_servers():
    return {"servers": load_server_catalog(settings)}


@app.post("/api/inspect", response_model=InspectResponse)
def inspect_sql(request: InspectRequest) -> InspectResponse:
    try:
        connection = _connection_from_inspect(request)
        payload = inspect_connection(connection, request.max_preview_rows)
    except (DatabaseError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    snapshot = InstanceSnapshot(
        label=connection.label,
        driver=connection.driver,
        database=connection.database,
        table=payload["actual_table"],
        schema_name=payload["actual_schema"],
        row_count=payload["total_count"],
        columns=payload["columns"],
        server_name=connection.host,
    )
    return InspectResponse(
        snapshot=snapshot,
        suggested_key_columns=payload["key_columns"],
        suggested_value_columns=payload["value_columns"],
        preview=payload["rows"],
        query=payload["query"],
    )


@app.post("/api/compare", response_model=CompareResponse)
def compare(request: CompareRequest) -> CompareResponse:
    try:
        left, right = _connections_from_compare(request)
        return run_compare(left, right, request)
    except (DatabaseError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/demo", response_model=CompareResponse)
def demo(include_identical: bool = True) -> CompareResponse:
    left, right = demo_connections()
    return run_compare(
        left,
        right,
        CompareRequest(left=left, right=right, include_identical=include_identical),
        fallback_rows=(LEFT_SETTINGS, RIGHT_SETTINGS),
    )


def _connection_from_inspect(request: InspectRequest) -> SqlConnection:
    if request.connection is not None:
        return request.connection
    if not request.server:
        raise ValueError("Choose a server name to inspect.")
    return resolve_server(
        request.server,
        settings,
        database=request.database,
        username=request.username,
        password=request.password,
        schema_name=request.schema_name,
    )


def _connections_from_compare(request: CompareRequest) -> tuple[SqlConnection, SqlConnection]:
    if request.left is not None and request.right is not None:
        return request.left, request.right
    if not request.left_server or not request.right_server:
        raise ValueError("Choose two server names to compare.")
    left = resolve_server(
        request.left_server,
        settings,
        database=request.database,
        username=request.username,
        password=request.password,
        schema_name=request.schema_name,
    )
    right = resolve_server(
        request.right_server,
        settings,
        database=request.database,
        username=request.username,
        password=request.password,
        schema_name=request.schema_name,
    )
    return left, right


def run_compare(
    left: SqlConnection,
    right: SqlConnection,
    request: CompareRequest,
    fallback_rows: tuple[list[dict], list[dict]] | None = None,
) -> CompareResponse:
    used_query = SETTINGS_SELECT
    if fallback_rows is None:
        left_columns, left_rows, left_table, left_schema, left_total, used_query = load_table(
            left, request.max_rows
        )
        right_columns, right_rows, right_table, right_schema, right_total, _ = load_table(
            right, request.max_rows
        )
    else:
        left_columns = demo_snapshot(left.label, left.database, fallback_rows[0]).columns
        left_rows = fallback_rows[0]
        left_table, left_schema, left_total = TABLE_NAME, None, len(left_rows)
        right_columns = demo_snapshot(right.label, right.database, fallback_rows[1]).columns
        right_rows = fallback_rows[1]
        right_table, right_schema, right_total = TABLE_NAME, None, len(right_rows)
        try:
            left_columns, left_rows, left_table, left_schema, left_total, used_query = load_table(
                left, request.max_rows
            )
            right_columns, right_rows, right_table, right_schema, right_total, _ = load_table(
                right, request.max_rows
            )
        except DatabaseError:
            pass

    key_columns = list(KEY_COLUMNS)
    value_columns = list(VALUE_COLUMNS)
    left_names = {col.name for col in left_columns}
    missing = [name for name in key_columns + value_columns if name not in left_names]
    warnings = []
    if missing:
        warnings.append(f"Requested columns were not all present on the left instance: {', '.join(missing)}")

    rows, summary, compare_warnings = compare_tables(
        left_rows,
        right_rows,
        key_columns,
        value_columns,
        include_identical=request.include_identical,
    )
    warnings.extend(compare_warnings)

    if left_total > len(left_rows):
        warnings.append(
            f"Left instance has {left_total} rows; only the first {len(left_rows)} were compared."
        )
    if right_total > len(right_rows):
        warnings.append(
            f"Right instance has {right_total} rows; only the first {len(right_rows)} were compared."
        )

    return CompareResponse(
        left=InstanceSnapshot(
            label=left.label,
            driver=left.driver,
            database=left.database,
            table=left_table,
            schema_name=left_schema,
            row_count=left_total,
            columns=left_columns,
            server_name=left.host or left.label,
        ),
        right=InstanceSnapshot(
            label=right.label,
            driver=right.driver,
            database=right.database,
            table=right_table,
            schema_name=right_schema,
            row_count=right_total,
            columns=right_columns,
            server_name=right.host or right.label,
        ),
        key_columns=key_columns,
        value_columns=value_columns,
        summary=summary,
        rows=rows,
        warnings=warnings,
        query=used_query,
    )


if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        index = WEB_DIST / "index.html"
        file_path = WEB_DIST / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(index)
