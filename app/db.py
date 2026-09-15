from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.compare import jsonable_row
from app.models import ColumnInfo, SqlConnection
from app.query import (
    KEY_COLUMNS,
    QUERY_COLUMNS,
    TABLE_NAME,
    VALUE_COLUMNS,
    settings_count_sql,
    settings_select_sql,
    validate_identifier,
)


class DatabaseError(RuntimeError):
    pass


def create_sql_engine(connection: SqlConnection) -> Engine:
    if connection.driver == "sqlite":
        database = connection.database or ":memory:"
        if database == ":memory:":
            url = "sqlite://"
        else:
            url = f"sqlite:///{database}"
        return create_engine(url)

    server_name = (connection.host or "").strip()
    if not server_name:
        raise DatabaseError("SQL Server name is required.")
    if _looks_like_ip(server_name):
        raise DatabaseError("Connect by SQL Server name, not an IP address.")
    if not connection.database:
        raise DatabaseError("Database name is required.")

    try:
        import pymssql
    except ImportError as exc:
        raise DatabaseError(
            "pymssql is not installed. Run `pip install pymssql` to connect to SQL Server."
        ) from exc

    def _connect():
        kwargs: dict[str, Any] = {
            "server": server_name,
            "user": connection.username or "",
            "password": connection.password or "",
            "database": connection.database,
            "login_timeout": 8,
            "timeout": 30,
        }
        if "\\" not in server_name and connection.port:
            kwargs["port"] = str(connection.port)
        if connection.encrypt:
            kwargs["encryption"] = "request"
        try:
            return pymssql.connect(**kwargs)
        except TypeError:
            kwargs.pop("encryption", None)
            return pymssql.connect(**kwargs)

    return create_engine("mssql+pymssql://", creator=_connect, pool_pre_ping=True)


def load_table(
    connection: SqlConnection,
    max_rows: int = 50_000,
) -> tuple[list[ColumnInfo], list[dict[str, Any]], str, str | None, int, str]:
    if connection.table and connection.table.upper() != TABLE_NAME:
        try:
            validate_identifier(connection.table, "table name")
        except ValueError as exc:
            raise DatabaseError(str(exc)) from exc
    engine = create_sql_engine(connection)
    try:
        query = settings_select_sql(connection.driver, connection.schema_name, limit=max_rows)
        count_sql = settings_count_sql(connection.driver, connection.schema_name)
    except ValueError as exc:
        raise DatabaseError(str(exc)) from exc
    try:
        with engine.connect() as conn:
            total_count = int(conn.execute(text(count_sql)).scalar_one())
            result = conn.execute(text(query))
            rows = [jsonable_row(dict(row)) for row in result.mappings()]
        columns = [
            ColumnInfo(
                name=name,
                type="str",
                nullable=name not in KEY_COLUMNS,
                primary_key=name in KEY_COLUMNS,
            )
            for name in QUERY_COLUMNS
        ]
        schema_name = None if connection.driver == "sqlite" else connection.schema_name
        return columns, rows, TABLE_NAME, schema_name, total_count, query
    except DatabaseError:
        raise
    except Exception as exc:
        raise DatabaseError(_friendly_db_error(exc, connection)) from exc
    finally:
        engine.dispose()


def inspect_connection(connection: SqlConnection, max_preview_rows: int = 8) -> dict[str, Any]:
    columns, rows, actual_table, actual_schema, total_count, query = load_table(
        connection, max_rows=max_preview_rows
    )
    return {
        "columns": columns,
        "rows": rows,
        "actual_table": actual_table,
        "actual_schema": actual_schema,
        "key_columns": list(KEY_COLUMNS),
        "value_columns": list(VALUE_COLUMNS),
        "pk": list(KEY_COLUMNS),
        "total_count": total_count,
        "query": query,
    }


def _looks_like_ip(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def _friendly_db_error(exc: Exception, connection: SqlConnection) -> str:
    message = str(exc)
    lowered = message.lower()
    if "login failed" in lowered or "18456" in message:
        return f"Login failed for {connection.label} ({connection.host}). Check username and password."
    if "timed out" in lowered or "timeout" in lowered:
        return f"Timed out connecting to {connection.label} ({connection.host})."
    if "could not open a connection" in lowered or "20009" in message or "name or service not known" in lowered:
        return f"Could not reach SQL Server '{connection.host}' by name."
    if "cannot open database" in lowered:
        return f"Database '{connection.database}' was not found on {connection.label}."
    if "no such table" in lowered or "invalid object name" in lowered:
        return f"Table {TABLE_NAME} was not found on {connection.label}."
    return f"{connection.label}: {message}"
