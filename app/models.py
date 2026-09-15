from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.query import KEY_COLUMNS, TABLE_NAME, VALUE_COLUMNS

Driver = Literal["mssql", "sqlite"]
DiffStatus = Literal["identical", "changed", "left_only", "right_only"]


class ServerInfo(BaseModel):
    name: str
    label: str | None = None
    database: str | None = None
    port: int | None = None
    schema_name: str | None = None

    def display_name(self) -> str:
        return self.label or self.name


class SqlConnection(BaseModel):
    label: str = "Instance"
    driver: Driver = "mssql"
    host: str | None = None
    port: int = 1433
    database: str
    username: str | None = None
    password: str | None = None
    trusted_connection: bool = False
    encrypt: bool = False
    schema_name: str | None = "dbo"
    table: str = TABLE_NAME


class CompareRequest(BaseModel):
    left_server: str | None = None
    right_server: str | None = None
    left: SqlConnection | None = None
    right: SqlConnection | None = None
    include_identical: bool = True
    database: str | None = None
    username: str | None = None
    password: str | None = None
    schema_name: str | None = None
    max_rows: int = Field(default=50_000, ge=1, le=200_000)


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False


class InstanceSnapshot(BaseModel):
    label: str
    driver: Driver
    database: str
    table: str
    schema_name: str | None = None
    row_count: int
    columns: list[ColumnInfo]
    server_name: str | None = None


class DiffRow(BaseModel):
    status: DiffStatus
    key: dict[str, Any]
    left: dict[str, Any] | None = None
    right: dict[str, Any] | None = None


class CompareSummary(BaseModel):
    identical: int = 0
    changed: int = 0
    left_only: int = 0
    right_only: int = 0
    total: int = 0
    duplicate_keys_left: int = 0
    duplicate_keys_right: int = 0


class CompareResponse(BaseModel):
    left: InstanceSnapshot
    right: InstanceSnapshot
    key_columns: list[str]
    value_columns: list[str]
    summary: CompareSummary
    rows: list[DiffRow]
    warnings: list[str] = Field(default_factory=list)
    query: str | None = None


class InspectRequest(BaseModel):
    server: str | None = None
    connection: SqlConnection | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    schema_name: str | None = None
    max_preview_rows: int = Field(default=8, ge=0, le=50)


class InspectResponse(BaseModel):
    snapshot: InstanceSnapshot
    suggested_key_columns: list[str] = Field(default_factory=lambda: list(KEY_COLUMNS))
    suggested_value_columns: list[str] = Field(default_factory=lambda: list(VALUE_COLUMNS))
    preview: list[dict[str, Any]]
    query: str | None = None


class PublicConfig(BaseModel):
    servers: list[ServerInfo]
    database: str = ""
    username: str | None = None
    schema_name: str = "dbo"
    table: str = TABLE_NAME
    query: str = (
        "SELECT SECTION, NAME, INIVALUE, DESCRIPTION, EXPOSED, DATATYPE, DATAFORMAT "
        "FROM TBLINISETTINGS"
    )


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    sql_server_names: str = ""
    sql_database: str = ""
    sql_username: str = ""
    sql_password: str = ""
    sql_port: int = 1433
    sql_schema: str = "dbo"
