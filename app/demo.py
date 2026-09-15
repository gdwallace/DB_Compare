from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import Column, MetaData, String, Table, create_engine, insert

from app.models import ColumnInfo, InstanceSnapshot, SqlConnection

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"

DEMO_COLUMNS = [
    ColumnInfo(name="SECTION", type="VARCHAR(100)", nullable=False, primary_key=True),
    ColumnInfo(name="IDENT", type="VARCHAR(100)", nullable=False, primary_key=True),
    ColumnInfo(name="VALUE", type="VARCHAR(4000)", nullable=True, primary_key=False),
]

# Realistic INI-style application settings. Left is the older/prod-like
# instance; right has drifted values, removals, and new keys.
LEFT_SETTINGS: list[dict[str, Any]] = [
    {"SECTION": "Database", "IDENT": "CommandTimeout", "VALUE": "30"},
    {"SECTION": "Database", "IDENT": "MaxPoolSize", "VALUE": "100"},
    {"SECTION": "Database", "IDENT": "ReadOnly", "VALUE": "0"},
    {"SECTION": "Logging", "IDENT": "Level", "VALUE": "INFO"},
    {"SECTION": "Logging", "IDENT": "Path", "VALUE": "D:\\Logs\\App.log"},
    {"SECTION": "Logging", "IDENT": "RetainDays", "VALUE": "14"},
    {"SECTION": "Mail", "IDENT": "SmtpHost", "VALUE": "mail.internal.local"},
    {"SECTION": "Mail", "IDENT": "SmtpPort", "VALUE": "25"},
    {"SECTION": "Mail", "IDENT": "FromAddress", "VALUE": "noreply@internal.local"},
    {"SECTION": "UI", "IDENT": "Theme", "VALUE": "classic"},
    {"SECTION": "UI", "IDENT": "PageSize", "VALUE": "50"},
    {"SECTION": "UI", "IDENT": "EnableNewDashboard", "VALUE": "0"},
    {"SECTION": "Security", "IDENT": "SessionTimeout", "VALUE": "20"},
    {"SECTION": "Security", "IDENT": "PasswordExpiryDays", "VALUE": "90"},
    {"SECTION": "Security", "IDENT": "MfaRequired", "VALUE": "0"},
    {"SECTION": "Jobs", "IDENT": "NightlyRebuild", "VALUE": "1"},
    {"SECTION": "Jobs", "IDENT": "NightlyRebuildHour", "VALUE": "2"},
    {"SECTION": "Legacy", "IDENT": "UseOldReports", "VALUE": "1"},
    {"SECTION": "Legacy", "IDENT": "ExportFormat", "VALUE": "xls"},
    {"SECTION": "Integrations", "IDENT": "MapProvider", "VALUE": "internal"},
]

RIGHT_SETTINGS: list[dict[str, Any]] = [
    {"SECTION": "Database", "IDENT": "CommandTimeout", "VALUE": "60"},
    {"SECTION": "Database", "IDENT": "MaxPoolSize", "VALUE": "100"},
    {"SECTION": "Database", "IDENT": "ReadOnly", "VALUE": "0"},
    {"SECTION": "Logging", "IDENT": "Level", "VALUE": "DEBUG"},
    {"SECTION": "Logging", "IDENT": "Path", "VALUE": "D:\\Logs\\App.log"},
    {"SECTION": "Logging", "IDENT": "RetainDays", "VALUE": "30"},
    {"SECTION": "Mail", "IDENT": "SmtpHost", "VALUE": "smtp.office365.com"},
    {"SECTION": "Mail", "IDENT": "SmtpPort", "VALUE": "587"},
    {"SECTION": "Mail", "IDENT": "FromAddress", "VALUE": "noreply@internal.local"},
    {"SECTION": "UI", "IDENT": "Theme", "VALUE": "modern"},
    {"SECTION": "UI", "IDENT": "PageSize", "VALUE": "50"},
    {"SECTION": "UI", "IDENT": "EnableNewDashboard", "VALUE": "1"},
    {"SECTION": "Security", "IDENT": "SessionTimeout", "VALUE": "20"},
    {"SECTION": "Security", "IDENT": "PasswordExpiryDays", "VALUE": "90"},
    {"SECTION": "Security", "IDENT": "MfaRequired", "VALUE": "1"},
    {"SECTION": "Jobs", "IDENT": "NightlyRebuild", "VALUE": "1"},
    {"SECTION": "Jobs", "IDENT": "NightlyRebuildHour", "VALUE": "3"},
    {"SECTION": "Integrations", "IDENT": "MapProvider", "VALUE": "internal"},
    {"SECTION": "Integrations", "IDENT": "PlacesAPI", "VALUE": "enabled"},
    {"SECTION": "Features", "IDENT": "BetaGrid", "VALUE": "1"},
]


def demo_snapshot(label: str, database: str, rows: list[dict[str, Any]]) -> InstanceSnapshot:
    return InstanceSnapshot(
        label=label,
        driver="sqlite",
        database=database,
        table="TBLINISETTINGS",
        schema_name=None,
        row_count=len(rows),
        columns=DEMO_COLUMNS,
    )


def demo_connections() -> tuple[SqlConnection, SqlConnection]:
    left_path, right_path = ensure_sample_databases()
    return (
        SqlConnection(
            label="Demo — Instance A",
            driver="sqlite",
            database=str(left_path),
            schema_name=None,
            table="TBLINISETTINGS",
        ),
        SqlConnection(
            label="Demo — Instance B",
            driver="sqlite",
            database=str(right_path),
            schema_name=None,
            table="TBLINISETTINGS",
        ),
    )


def ensure_sample_databases() -> tuple[Path, Path]:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    left_path = SAMPLE_DIR / "instance_a.sqlite"
    right_path = SAMPLE_DIR / "instance_b.sqlite"
    _write_sqlite(left_path, LEFT_SETTINGS)
    _write_sqlite(right_path, RIGHT_SETTINGS)
    return left_path, right_path


def _write_sqlite(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        path.unlink()
    engine = create_engine(f"sqlite:///{path}")
    metadata = MetaData()
    table = Table(
        "TBLINISETTINGS",
        metadata,
        Column("SECTION", String(100), primary_key=True),
        Column("IDENT", String(100), primary_key=True),
        Column("VALUE", String(4000)),
    )
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(insert(table), rows)
    engine.dispose()
