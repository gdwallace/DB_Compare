export type Driver = "mssql" | "sqlite";
export type DiffStatus = "identical" | "changed" | "left_only" | "right_only";

export type SqlConnection = {
  label: string;
  driver: Driver;
  host?: string | null;
  port: number;
  database: string;
  username?: string | null;
  password?: string | null;
  trusted_connection: boolean;
  encrypt: boolean;
  schema_name?: string | null;
  table: string;
};

export type ColumnInfo = {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
};

export type InstanceSnapshot = {
  label: string;
  driver: Driver;
  database: string;
  table: string;
  schema_name?: string | null;
  row_count: number;
  columns: ColumnInfo[];
};

export type DiffRow = {
  status: DiffStatus;
  key: Record<string, string | number | null>;
  left: Record<string, string | number | null> | null;
  right: Record<string, string | number | null> | null;
};

export type CompareSummary = {
  identical: number;
  changed: number;
  left_only: number;
  right_only: number;
  total: number;
  duplicate_keys_left: number;
  duplicate_keys_right: number;
};

export type CompareResponse = {
  left: InstanceSnapshot;
  right: InstanceSnapshot;
  key_columns: string[];
  value_columns: string[];
  summary: CompareSummary;
  rows: DiffRow[];
  warnings: string[];
};

export type InspectResponse = {
  snapshot: InstanceSnapshot;
  suggested_key_columns: string[];
  suggested_value_columns: string[];
  preview: Record<string, string | number | null>[];
};

export type PublicConnection = SqlConnection & { configured: boolean };

export type PublicConfig = {
  left: PublicConnection;
  right: PublicConnection;
};

export const emptyConnection = (label: string): SqlConnection => ({
  label,
  driver: "mssql",
  host: "",
  port: 1433,
  database: "",
  username: "",
  password: "",
  trusted_connection: false,
  encrypt: false,
  schema_name: "dbo",
  table: "TBLINISETTINGS",
});

export const STATUS_LABEL: Record<DiffStatus, string> = {
  identical: "Match",
  changed: "Changed",
  left_only: "Only A",
  right_only: "Only B",
};
