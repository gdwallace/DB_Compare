from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Driver = Literal["mssql", "sqlite"]
DiffStatus = Literal["identical", "changed", "left_only", "right_only"]


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
    table: str = "TBLINISETTINGS"


class CompareRequest(BaseModel):
    left: SqlConnection
    right: SqlConnection
    key_columns: list[str] | None = None
    value_columns: list[str] | None = None
    include_identical: bool = True
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


class InspectRequest(BaseModel):
    connection: SqlConnection
    max_preview_rows: int = Field(default=8, ge=0, le=50)


class InspectResponse(BaseModel):
    snapshot: InstanceSnapshot
    suggested_key_columns: list[str]
    suggested_value_columns: list[str]
    preview: list[dict[str, Any]]


class PublicConnection(BaseModel):
    label: str
    driver: Driver
    host: str | None = None
    port: int = 1433
    database: str = ""
    username: str | None = None
    trusted_connection: bool = False
    encrypt: bool = False
    schema_name: str | None = "dbo"
    table: str = "TBLINISETTINGS"
    configured: bool = False


class PublicConfig(BaseModel):
    left: PublicConnection
    right: PublicConnection


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    left_label: str = "SQL Instance A"
    left_driver: Driver = "mssql"
    left_host: str = ""
    left_port: int = 1433
    left_database: str = ""
    left_username: str = ""
    left_password: str = ""
    left_trusted_connection: bool = False
    left_schema: str = "dbo"
    left_table: str = "TBLINISETTINGS"

    right_label: str = "SQL Instance B"
    right_driver: Driver = "mssql"
    right_host: str = ""
    right_port: int = 1433
    right_database: str = ""
    right_username: str = ""
    right_password: str = ""
    right_trusted_connection: bool = False
    right_schema: str = "dbo"
    right_table: str = "TBLINISETTINGS"

    def public_config(self) -> PublicConfig:
        return PublicConfig(
            left=self._public("left"),
            right=self._public("right"),
        )

    def _public(self, side: Literal["left", "right"]) -> PublicConnection:
        host = getattr(self, f"{side}_host")
        database = getattr(self, f"{side}_database")
        username = getattr(self, f"{side}_username")
        return PublicConnection(
            label=getattr(self, f"{side}_label"),
            driver=getattr(self, f"{side}_driver"),
            host=host or None,
            port=getattr(self, f"{side}_port"),
            database=database,
            username=username or None,
            trusted_connection=getattr(self, f"{side}_trusted_connection"),
            schema_name=getattr(self, f"{side}_schema") or None,
            table=getattr(self, f"{side}_table"),
            configured=bool(host and database),
        )
