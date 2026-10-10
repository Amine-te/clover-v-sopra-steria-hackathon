// Single HTTP client for the Karis backend API.

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const HEALTH_TIMEOUT_MS = 5000;

export type HealthResponse = {
  status: string;
  version: string;
  notify_channel: string;
};

/** Backend base URL from NEXT_PUBLIC_API_BASE_URL (inlined at build time), without trailing slash. */
export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return (configured || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** GET /health. Rejects on timeout (5 s), a non-200 status, or a body missing status/version. */
export async function getHealth(): Promise<HealthResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const response = await fetch(`${getApiBaseUrl()}/health`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal: controller.signal,
    });
    if (response.status !== 200) {
      throw new Error(`Health check failed with HTTP ${response.status}`);
    }
    const body: unknown = await response.json();
    if (!isRecord(body) || typeof body.status !== "string" || typeof body.version !== "string") {
      throw new Error("Health check returned an invalid body");
    }
    return {
      status: body.status,
      version: body.version,
      notify_channel: typeof body.notify_channel === "string" ? body.notify_channel : "",
    };
  } finally {
    clearTimeout(timer);
  }
}
