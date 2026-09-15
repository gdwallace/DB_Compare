import type {
  CompareResponse,
  InspectResponse,
  PublicConfig,
  SqlConnection,
} from "./types";

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

export async function inspectConnection(connection: SqlConnection): Promise<InspectResponse> {
  const response = await fetch("/api/inspect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ connection }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function compareInstances(
  left: SqlConnection,
  right: SqlConnection,
  includeIdentical: boolean,
): Promise<CompareResponse> {
  const response = await fetch("/api/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      left,
      right,
      include_identical: includeIdentical,
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
