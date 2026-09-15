from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import MetaData, Table, func, inspect, select
from sqlalchemy.engine import Engine, create_engine

from app.compare import guess_key_and_value_columns, jsonable_row
from app.models import ColumnInfo, SqlConnection

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseError(RuntimeError):
    pass


def validate_identifier(name: str, kind: str) -> str:
    if not name or not IDENTIFIER_RE.match(name):
        raise DatabaseError(f"Invalid {kind} '{name}'. Use letters, numbers, and underscore only.")
    return name


def create_sql_engine(connection: SqlConnection) -> Engine:
    if connection.driver == "sqlite":
        database = connection.database or ":memory:"
        if database == ":memory:":
            url = "sqlite://"
        else:
            url = f"sqlite:///{database}"
        return create_engine(url)

    host = connection.host
    if not host:
        raise DatabaseError("SQL Server host is required.")
    database = connection.database
    if not database:
        raise DatabaseError("Database name is required.")

    try:
        import pymssql  # noqa: F401
        dialect = "mssql+pymssql"
    except ImportError as exc:
        raise DatabaseError(
            "pymssql is not installed. Run `pip install pymssql` to connect to SQL Server."
        ) from exc

    user = quote_plus(connection.username or "")
    password = quote_plus(connection.password or "")
    auth = f"{user}:{password}@" if connection.username else ""
    port = connection.port or 1433
    url = f"{dialect}://{auth}{host}:{port}/{quote_plus(database)}"
    connect_args: dict[str, Any] = {"login_timeout": 8, "timeout": 30}
    if connection.trusted_connection:
        connect_args["tds_version"] = "7.4"
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


def load_table(
    connection: SqlConnection,
    max_rows: int = 50_000,
) -> tuple[list[ColumnInfo], list[dict[str, Any]], str, str | None, int]:
    table_name = validate_identifier(connection.table, "table name")
    schema_name = connection.schema_name
    if schema_name:
        schema_name = validate_identifier(schema_name, "schema name")
    if connection.driver == "sqlite":
        schema_name = None

    engine = create_sql_engine(connection)
    try:
        inspector = inspect(engine)
        actual_table, actual_schema = _resolve_table(inspector, table_name, schema_name)
        column_meta = inspector.get_columns(actual_table, schema=actual_schema)
        pk_info = inspector.get_pk_constraint(actual_table, schema=actual_schema)
        pk_columns = set(pk_info.get("constrained_columns") or [])

        columns = [
            ColumnInfo(
                name=col["name"],
                type=str(col.get("type") or ""),
                nullable=bool(col.get("nullable", True)),
                primary_key=col["name"] in pk_columns,
            )
            for col in column_meta
        ]

        metadata = MetaData()
        table = Table(actual_table, metadata, autoload_with=engine, schema=actual_schema)
        with engine.connect() as conn:
            total_count = int(conn.execute(select(func.count()).select_from(table)).scalar_one())
            result = conn.execute(select(table).limit(max_rows))
            rows = [jsonable_row(dict(row)) for row in result.mappings()]
        return columns, rows, actual_table, actual_schema, total_count
    except DatabaseError:
        raise
    except Exception as exc:
        raise DatabaseError(_friendly_db_error(exc, connection)) from exc
    finally:
        engine.dispose()


def inspect_connection(connection: SqlConnection, max_preview_rows: int = 8) -> dict[str, Any]:
    columns, rows, actual_table, actual_schema, total_count = load_table(
        connection, max_rows=max_preview_rows
    )
    pk = [column.name for column in columns if column.primary_key]
    key_columns, value_columns = guess_key_and_value_columns(columns, pk)
    return {
        "columns": columns,
        "rows": rows,
        "actual_table": actual_table,
        "actual_schema": actual_schema,
        "key_columns": key_columns,
        "value_columns": value_columns,
        "pk": pk,
        "total_count": total_count,
    }


def _resolve_table(inspector: Any, table_name: str, schema_name: str | None) -> tuple[str, str | None]:
    schemas: list[str | None]
    if schema_name:
        schemas = [schema_name]
    else:
        schemas = [None]
        try:
            schemas.extend(inspector.get_schema_names())
        except Exception:
            pass

    seen: set[tuple[str | None, str]] = set()
    for schema in schemas:
        try:
            names = inspector.get_table_names(schema=schema)
        except Exception:
            continue
        for name in names:
            key = (schema, name.lower())
            if key in seen:
                continue
            seen.add(key)
            if name.lower() == table_name.lower():
                return name, schema
    where = f"{schema_name}." if schema_name else ""
    raise DatabaseError(f"Table {where}{table_name} was not found.")


def _friendly_db_error(exc: Exception, connection: SqlConnection) -> str:
    text = str(exc)
    lowered = text.lower()
    if "login failed" in lowered or "18456" in text:
        return f"Login failed for {connection.label} ({connection.host}). Check username and password."
    if "timed out" in lowered or "timeout" in lowered:
        return f"Timed out connecting to {connection.label} at {connection.host}:{connection.port}."
    if "could not open a connection" in lowered or "20009" in text or "name or service not known" in lowered:
        return f"Could not reach {connection.label} at {connection.host}:{connection.port}."
    if "cannot open database" in lowered:
        return f"Database '{connection.database}' was not found on {connection.label}."
    return f"{connection.label}: {text}"
