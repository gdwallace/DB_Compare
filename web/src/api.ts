import type { CompareResponse, InspectResponse, PublicConfig } from "./types";

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    return JSON.stringify(body.detail ?? body);
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}

export async function fetchConfig(): Promise<PublicConfig> {
  const response = await fetch("/api/config");
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function inspectServer(
  server: string,
  extras: { database?: string; schema_name?: string },
): Promise<InspectResponse> {
  const response = await fetch("/api/inspect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ server, ...extras }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function compareServers(
  leftServer: string,
  rightServer: string,
  extras: {
    includeIdentical: boolean;
    database?: string;
    schema_name?: string;
  },
): Promise<CompareResponse> {
  const response = await fetch("/api/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      left_server: leftServer,
      right_server: rightServer,
      include_identical: extras.includeIdentical,
      database: extras.database,
      schema_name: extras.schema_name,
    }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function loadDemo(includeIdentical = true): Promise<CompareResponse> {
  const response = await fetch(`/api/demo?include_identical=${includeIdentical}`);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}
