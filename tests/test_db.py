from pathlib import Path

import pytest

from app.db import DatabaseError, load_table, validate_identifier
from app.demo import LEFT_SETTINGS, ensure_sample_databases
from app.models import SqlConnection


def test_validate_identifier_rejects_injection():
    with pytest.raises(DatabaseError):
        validate_identifier("TBLINISETTINGS; DROP TABLE x", "table name")


def test_load_sqlite_sample():
    left_path, _ = ensure_sample_databases()
    columns, rows, table, schema, total = load_table(
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
    assert [column.name for column in columns] == ["SECTION", "IDENT", "VALUE"]


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
