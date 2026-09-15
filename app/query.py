from __future__ import annotations

import re

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TABLE_NAME = "TBLINISETTINGS"
QUERY_COLUMNS = (
    "SECTION",
    "NAME",
    "INIVALUE",
    "DESCRIPTION",
    "EXPOSED",
    "DATATYPE",
    "DATAFORMAT",
)
KEY_COLUMNS = ("SECTION", "NAME")
VALUE_COLUMNS = ("INIVALUE", "DESCRIPTION", "EXPOSED", "DATATYPE", "DATAFORMAT")
SETTINGS_SELECT = (
    "SELECT SECTION, NAME, INIVALUE, DESCRIPTION, EXPOSED, DATATYPE, DATAFORMAT "
    "FROM TBLINISETTINGS"
)


def validate_identifier(name: str, kind: str) -> str:
    if not name or not IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid {kind} '{name}'. Use letters, numbers, and underscore only.")
    return name


def qualified_table(driver: str, schema_name: str | None) -> str:
    table = validate_identifier(TABLE_NAME, "table name")
    if driver == "sqlite" or not schema_name:
        return table
    schema = validate_identifier(schema_name, "schema name")
    return f"{schema}.{table}"


def settings_select_sql(driver: str, schema_name: str | None, limit: int | None = None) -> str:
    columns = ", ".join(QUERY_COLUMNS)
    table = qualified_table(driver, schema_name)
    if driver == "mssql" and limit is not None:
        return f"SELECT TOP ({int(limit)}) {columns} FROM {table}"
    sql = f"SELECT {columns} FROM {table}"
    if limit is not None:
        return f"{sql} LIMIT {int(limit)}"
    return sql


def settings_count_sql(driver: str, schema_name: str | None) -> str:
    return f"SELECT COUNT(*) FROM {qualified_table(driver, schema_name)}"
