export type Driver = "mssql" | "sqlite";
export type DiffStatus = "identical" | "changed" | "left_only" | "right_only";

export type ServerInfo = {
  name: string;
  label?: string | null;
  database?: string | null;
  port?: number | null;
  schema_name?: string | null;
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
  server_name?: string | null;
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
  query?: string | null;
};

export type InspectResponse = {
  snapshot: InstanceSnapshot;
  suggested_key_columns: string[];
  suggested_value_columns: string[];
  preview: Record<string, string | number | null>[];
  query?: string | null;
};

export type PublicConfig = {
  servers: ServerInfo[];
  database: string;
  username?: string | null;
  schema_name: string;
  table: string;
  query: string;
};

export const STATUS_LABEL: Record<DiffStatus, string> = {
  identical: "Match",
  changed: "Changed",
  left_only: "Only A",
  right_only: "Only B",
};

export function serverLabel(server: ServerInfo): string {
  return server.label || server.name;
}
