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


def test_resolve_server_uses_group_credentials():
    settings = AppSettings(
        sql_database="AppDB",
        appian_username="AppianAppUser2025",
        appian_password="prod-secret",
        appian_stage_username="AppianAppStageUser2025",
        appian_stage_password="stage-secret",
    )
    prod = resolve_server("sql-butterfly.appian.trimblemaps.com", settings)
    stage = resolve_server("sql01.staging.appiantesting.com", settings)
    assert prod.host == "sql-butterfly.appian.trimblemaps.com"
    assert prod.username == "AppianAppUser2025"
    assert prod.password == "prod-secret"
    assert stage.host == "sql01.staging.appiantesting.com"
    assert stage.username == "AppianAppStageUser2025"
    assert stage.password == "stage-secret"


def test_resolve_requires_group_password():
    settings = AppSettings(
        sql_database="AppDB",
        appian_password="",
        appian_stage_password="",
    )
    with pytest.raises(ValueError, match="APPIAN_PASSWORD"):
        resolve_server("sql-butterfly.appian.trimblemaps.com", settings)


def test_catalog_includes_json_servers():
    names = [server.name for server in load_server_catalog(AppSettings())]
    assert "sql-fireworks.appian.trimblemaps.com" in names
    assert "law-sql02.staging.appiantesting.com" in names
