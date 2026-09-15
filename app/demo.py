from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import Column, MetaData, String, Table, create_engine, insert

from app.models import ColumnInfo, InstanceSnapshot, SqlConnection
from app.query import KEY_COLUMNS, QUERY_COLUMNS, TABLE_NAME

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"

DEMO_COLUMNS = [
    ColumnInfo(name=name, type="VARCHAR", nullable=name not in KEY_COLUMNS, primary_key=name in KEY_COLUMNS)
    for name in QUERY_COLUMNS
]


def _row(
    section: str,
    name: str,
    value: str,
    description: str,
    *,
    exposed: str = "1",
    datatype: str = "string",
    dataformat: str = "",
) -> dict[str, Any]:
    return {
        "SECTION": section,
        "NAME": name,
        "INIVALUE": value,
        "DESCRIPTION": description,
        "EXPOSED": exposed,
        "DATATYPE": datatype,
        "DATAFORMAT": dataformat,
    }


LEFT_SETTINGS: list[dict[str, Any]] = [
    _row("Database", "CommandTimeout", "30", "Command timeout in seconds", datatype="int"),
    _row("Database", "MaxPoolSize", "100", "ADO pool size", datatype="int"),
    _row("Database", "ReadOnly", "0", "Open connections read-only", datatype="bool"),
    _row("Logging", "Level", "INFO", "Minimum log level"),
    _row("Logging", "Path", "D:\\Logs\\App.log", "Log file path", dataformat="path"),
    _row("Logging", "RetainDays", "14", "Days to keep log files", datatype="int"),
    _row("Mail", "SmtpHost", "mail.internal.local", "SMTP server name"),
    _row("Mail", "SmtpPort", "25", "SMTP port", datatype="int"),
    _row("Mail", "FromAddress", "noreply@internal.local", "From address", dataformat="email"),
    _row("UI", "Theme", "classic", "UI theme name"),
    _row("UI", "PageSize", "50", "Grid page size", datatype="int"),
    _row("UI", "EnableNewDashboard", "0", "Show the redesigned dashboard", datatype="bool", exposed="0"),
    _row("Security", "SessionTimeout", "20", "Idle session timeout minutes", datatype="int"),
    _row("Security", "PasswordExpiryDays", "90", "Password age limit", datatype="int"),
    _row("Security", "MfaRequired", "0", "Require MFA at login", datatype="bool", exposed="0"),
    _row("Jobs", "NightlyRebuild", "1", "Rebuild caches overnight", datatype="bool"),
    _row("Jobs", "NightlyRebuildHour", "2", "Local hour for nightly rebuild", datatype="int"),
    _row("Legacy", "UseOldReports", "1", "Keep classic report engine", datatype="bool", exposed="0"),
    _row("Legacy", "ExportFormat", "xls", "Default export format"),
    _row("Integrations", "MapProvider", "internal", "Map tile provider"),
]

RIGHT_SETTINGS: list[dict[str, Any]] = [
    _row("Database", "CommandTimeout", "60", "Command timeout in seconds", datatype="int"),
    _row("Database", "MaxPoolSize", "100", "ADO pool size", datatype="int"),
    _row("Database", "ReadOnly", "0", "Open connections read-only", datatype="bool"),
    _row("Logging", "Level", "DEBUG", "Minimum log level"),
    _row("Logging", "Path", "D:\\Logs\\App.log", "Log file path", dataformat="path"),
    _row("Logging", "RetainDays", "30", "Days to keep log files", datatype="int"),
    _row("Mail", "SmtpHost", "smtp.office365.com", "SMTP server name"),
    _row("Mail", "SmtpPort", "587", "SMTP port", datatype="int"),
    _row("Mail", "FromAddress", "noreply@internal.local", "From address", dataformat="email"),
    _row("UI", "Theme", "modern", "UI theme name"),
    _row("UI", "PageSize", "50", "Grid page size", datatype="int"),
    _row("UI", "EnableNewDashboard", "1", "Show the redesigned dashboard", datatype="bool", exposed="1"),
    _row("Security", "SessionTimeout", "20", "Idle session timeout minutes", datatype="int"),
    _row("Security", "PasswordExpiryDays", "90", "Password age limit", datatype="int"),
    _row("Security", "MfaRequired", "1", "Require MFA at login", datatype="bool", exposed="1"),
    _row("Jobs", "NightlyRebuild", "1", "Rebuild caches overnight", datatype="bool"),
    _row("Jobs", "NightlyRebuildHour", "3", "Local hour for nightly rebuild", datatype="int"),
    _row("Integrations", "MapProvider", "internal", "Map tile provider"),
    _row("Integrations", "PlacesAPI", "enabled", "Places API integration", datatype="bool"),
    _row("Features", "BetaGrid", "1", "Enable beta grid control", datatype="bool", exposed="0"),
]


def demo_snapshot(label: str, database: str, rows: list[dict[str, Any]]) -> InstanceSnapshot:
    return InstanceSnapshot(
        label=label,
        driver="sqlite",
        database=database,
        table=TABLE_NAME,
        schema_name=None,
        row_count=len(rows),
        columns=DEMO_COLUMNS,
        server_name=label,
    )


def demo_connections() -> tuple[SqlConnection, SqlConnection]:
    left_path, right_path = ensure_sample_databases()
    return (
        SqlConnection(
            label="SQL-PROD-01",
            driver="sqlite",
            database=str(left_path),
            schema_name=None,
            table=TABLE_NAME,
        ),
        SqlConnection(
            label="SQL-UAT-01",
            driver="sqlite",
            database=str(right_path),
            schema_name=None,
            table=TABLE_NAME,
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
        TABLE_NAME,
        metadata,
        Column("SECTION", String(100), primary_key=True),
        Column("NAME", String(100), primary_key=True),
        Column("INIVALUE", String(4000)),
        Column("DESCRIPTION", String(4000)),
        Column("EXPOSED", String(10)),
        Column("DATATYPE", String(50)),
        Column("DATAFORMAT", String(50)),
    )
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(insert(table), rows)
    engine.dispose()
