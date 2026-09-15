from pathlib import Path

import pytest

from app.db import DatabaseError, load_table
from app.demo import LEFT_SETTINGS, ensure_sample_databases
from app.models import SqlConnection
from app.query import QUERY_COLUMNS, validate_identifier
from app.servers import load_server_catalog, resolve_server
from app.models import AppSettings


def test_validate_identifier_rejects_injection():
    with pytest.raises(ValueError):
        validate_identifier("TBLINISETTINGS; DROP TABLE x", "table name")


def test_load_sqlite_sample():
    left_path, _ = ensure_sample_databases()
    columns, rows, table, schema, total, query = load_table(
        SqlConnection(
            label="A",
            driver="sqlite",
            database=str(left_path),
            schema_name=None,
            table="TBLINISETTINGS",
        )
    )
    assert table == "TBLINISETTINGS"
    assert schema is None
    assert total == len(LEFT_SETTINGS)
    assert len(rows) == total
    assert [column.name for column in columns] == list(QUERY_COLUMNS)
    assert "SELECT SECTION, NAME, INIVALUE, DESCRIPTION, EXPOSED, DATATYPE, DATAFORMAT" in query
    assert rows[0]["NAME"]


def test_load_missing_file():
    with pytest.raises(DatabaseError):
        load_table(
            SqlConnection(
                label="A",
                driver="sqlite",
                database=str(Path("/tmp/does-not-exist-db-compare.sqlite")),
                schema_name=None,
                table="TBLINISETTINGS",
            )
        )


def test_engine_rejects_ip_address():
    with pytest.raises(DatabaseError, match="not an IP address"):
        load_table(
            SqlConnection(
                label="A",
                driver="mssql",
                host="10.1.2.3",
                database="AppDB",
                table="TBLINISETTINGS",
            )
        )


def test_resolve_server_uses_catalog_name():
    settings = AppSettings(sql_database="AppDB", sql_username="app")
    connection = resolve_server("SQL-PROD-01", settings)
    assert connection.host == "SQL-PROD-01"
    assert connection.label == "SQL-PROD-01"
    assert connection.database == "AppDB"


def test_catalog_includes_json_servers():
    names = [server.name for server in load_server_catalog(AppSettings())]
    assert "SQL-PROD-01" in names
    assert "SQL-UAT-01" in names
