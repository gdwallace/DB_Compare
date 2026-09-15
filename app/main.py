from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.compare import compare_tables, guess_key_and_value_columns
from app.db import DatabaseError, inspect_connection, load_table
from app.demo import LEFT_SETTINGS, RIGHT_SETTINGS, demo_connections, demo_snapshot
from app.models import (
    AppSettings,
    CompareRequest,
    CompareResponse,
    InspectRequest,
    InspectResponse,
    InstanceSnapshot,
    SqlConnection,
)

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


@app.get("/api/config")
def public_config():
    return settings.public_config()


@app.post("/api/inspect", response_model=InspectResponse)
def inspect_sql(request: InspectRequest) -> InspectResponse:
    try:
        payload = inspect_connection(request.connection, request.max_preview_rows)
    except DatabaseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    connection = request.connection
    snapshot = InstanceSnapshot(
        label=connection.label,
        driver=connection.driver,
        database=connection.database,
        table=payload["actual_table"],
        schema_name=payload["actual_schema"],
        row_count=payload["total_count"],
        columns=payload["columns"],
    )
    return InspectResponse(
        snapshot=snapshot,
        suggested_key_columns=payload["key_columns"],
        suggested_value_columns=payload["value_columns"],
        preview=payload["rows"],
    )


@app.post("/api/compare", response_model=CompareResponse)
def compare(request: CompareRequest) -> CompareResponse:
    try:
        return run_compare(request.left, request.right, request)
    except DatabaseError as exc:
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


def run_compare(
    left: SqlConnection,
    right: SqlConnection,
    request: CompareRequest,
    fallback_rows: tuple[list[dict], list[dict]] | None = None,
) -> CompareResponse:
    if fallback_rows is None:
        left_columns, left_rows, left_table, left_schema, left_total = load_table(left, request.max_rows)
        right_columns, right_rows, right_table, right_schema, right_total = load_table(right, request.max_rows)
    else:
        left_columns = demo_snapshot(left.label, left.database, fallback_rows[0]).columns
        left_rows = fallback_rows[0]
        left_table, left_schema, left_total = "TBLINISETTINGS", None, len(left_rows)
        right_columns = demo_snapshot(right.label, right.database, fallback_rows[1]).columns
        right_rows = fallback_rows[1]
        right_table, right_schema, right_total = "TBLINISETTINGS", None, len(right_rows)
        # Prefer loading from sqlite files when they exist so the demo
        # exercises the same query path as a live comparison.
        try:
            left_columns, left_rows, left_table, left_schema, left_total = load_table(left, request.max_rows)
            right_columns, right_rows, right_table, right_schema, right_total = load_table(
                right, request.max_rows
            )
        except DatabaseError:
            pass

    pk = [column.name for column in left_columns if column.primary_key]
    guessed_keys, guessed_values = guess_key_and_value_columns(left_columns, pk)
    key_columns = request.key_columns or guessed_keys
    value_columns = request.value_columns or guessed_values

    missing = [name for name in key_columns + value_columns if name not in {col.name for col in left_columns}]
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
        ),
        right=InstanceSnapshot(
            label=right.label,
            driver=right.driver,
            database=right.database,
            table=right_table,
            schema_name=right_schema,
            row_count=right_total,
            columns=right_columns,
        ),
        key_columns=key_columns,
        value_columns=value_columns,
        summary=summary,
        rows=rows,
        warnings=warnings,
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
