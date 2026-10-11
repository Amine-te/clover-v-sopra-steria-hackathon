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

// Voice reports (POST /api/reports/voice and /api/reports/{id}/transcribe).

// Transcribe can take up to 180 s server-side; leave margin for upload and read-back.
const VOICE_TIMEOUT_MS = 240_000;

export type VoiceReport = {
  report_id: string;
  audio_s3_key: string | null;
  transcript: string;
  source: "transcribe" | "cache";
};

export type VoiceReportFailure = {
  report_id: string | null;
  audio_s3_key: string | null;
  detail: string;
  retryable: boolean;
};

export type VoiceReportResult =
  | { ok: true; report: VoiceReport }
  | { ok: false; error: VoiceReportFailure };

function failure(detail: string, extra: Partial<VoiceReportFailure> = {}): VoiceReportResult {
  return {
    ok: false,
    error: { report_id: null, audio_s3_key: null, retryable: false, ...extra, detail },
  };
}

function nullableString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

/** Sends a voice report request and turns every outcome (including network errors) into a typed result. */
async function postVoice(path: string, body?: FormData): Promise<VoiceReportResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), VOICE_TIMEOUT_MS);
  let response: Response;
  let data: unknown;
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      method: "POST",
      headers: { Accept: "application/json" },
      body,
      cache: "no-store",
      signal: controller.signal,
    });
    data = await response.json().catch(() => null);
  } catch {
    return failure(`Impossible de joindre le serveur à ${getApiBaseUrl()}.`);
  } finally {
    clearTimeout(timer);
  }

  if (response.ok) {
    if (
      isRecord(data) &&
      typeof data.report_id === "string" &&
      typeof data.transcript === "string" &&
      (data.source === "transcribe" || data.source === "cache")
    ) {
      return {
        ok: true,
        report: {
          report_id: data.report_id,
          audio_s3_key: nullableString(data.audio_s3_key),
          transcript: data.transcript,
          source: data.source,
        },
      };
    }
    return failure("Réponse inattendue du serveur.");
  }

  // FastAPI errors carry a French `detail`; 502 bodies also say whether a retry is possible.
  const detail =
    isRecord(data) && typeof data.detail === "string"
      ? data.detail
      : `Erreur du serveur (HTTP ${response.status}).`;
  if (response.status === 502 && isRecord(data)) {
    return failure(detail, {
      report_id: nullableString(data.report_id),
      audio_s3_key: nullableString(data.audio_s3_key),
      retryable: data.retryable === true,
    });
  }
  return failure(detail);
}

/** POST /api/reports/voice with the recording (multipart field `audio`) and an optional fixture name. */
export function submitVoiceReport(
  file: Blob,
  filename: string,
  fixture?: string,
): Promise<VoiceReportResult> {
  const form = new FormData();
  form.append("audio", file, filename);
  if (fixture) form.append("fixture", fixture);
  return postVoice("/api/reports/voice", form);
}

/** POST /api/reports/{reportId}/transcribe: transcribe the stored audio again, without re-uploading. */
export function retryTranscription(reportId: string): Promise<VoiceReportResult> {
  return postVoice(`/api/reports/${encodeURIComponent(reportId)}/transcribe`);
}

// Fact extraction (POST /api/reports/extract).

// The backend makes one Bedrock Converse call; allow generous margin for it.
const EXTRACT_TIMEOUT_MS = 60_000;

export type Observation = {
  id: string;
  timestamp: string;
  reported_at: string;
  subject_id: string;
  category: string;
  value: string;
  severity: "info" | "watch" | "urgent";
  source: string;
  reported_by: string;
  confidence: number;
  transcript_span: string;
};

export type ExtractPayload = {
  transcript: string;
  subject_id: string;
  reported_by: string;
  reported_at?: string;
};

export type ExtractResult =
  | { ok: true; observations: Observation[] }
  | { ok: false; detail: string };

function isObservation(value: unknown): value is Observation {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.category === "string" &&
    typeof value.value === "string" &&
    typeof value.severity === "string"
  );
}

/** POST /api/reports/extract: turn a transcript into Observations, mapping every outcome to a typed result. */
export async function extractObservations(payload: ExtractPayload): Promise<ExtractResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), EXTRACT_TIMEOUT_MS);
  let response: Response;
  let data: unknown;
  try {
    response = await fetch(`${getApiBaseUrl()}/api/reports/extract`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: controller.signal,
    });
    data = await response.json().catch(() => null);
  } catch {
    return { ok: false, detail: `Impossible de joindre le serveur à ${getApiBaseUrl()}.` };
  } finally {
    clearTimeout(timer);
  }

  if (response.ok && isRecord(data) && Array.isArray(data.observations)) {
    return { ok: true, observations: data.observations.filter(isObservation) };
  }
  const detail =
    isRecord(data) && typeof data.detail === "string"
      ? data.detail
      : `Erreur du serveur (HTTP ${response.status}).`;
  return { ok: false, detail };
}

// Timeline store (POST /api/observations and GET /api/timeline).

const TIMELINE_TIMEOUT_MS = 30_000;

export type SaveObservationsResult =
  | { ok: true; saved: number; keys: string[] }
  | { ok: false; detail: string };

export type TimelineResult =
  | { ok: true; observations: Observation[]; count: number }
  | { ok: false; detail: string };

export type TimelineQuery = {
  subject_id: string;
  start?: string;
  end?: string;
  category?: string;
  severity?: string;
};

function errorDetail(data: unknown, status: number): string {
  return isRecord(data) && typeof data.detail === "string"
    ? data.detail
    : `Erreur du serveur (HTTP ${status}).`;
}

/** POST /api/observations: save a list of Observations, mapping every outcome to a typed result. */
export async function saveObservations(observations: Observation[]): Promise<SaveObservationsResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMELINE_TIMEOUT_MS);
  let response: Response;
  let data: unknown;
  try {
    response = await fetch(`${getApiBaseUrl()}/api/observations`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(observations),
      cache: "no-store",
      signal: controller.signal,
    });
    data = await response.json().catch(() => null);
  } catch {
    return { ok: false, detail: `Impossible de joindre le serveur à ${getApiBaseUrl()}.` };
  } finally {
    clearTimeout(timer);
  }

  if (response.ok && isRecord(data) && typeof data.saved === "number" && Array.isArray(data.keys)) {
    return { ok: true, saved: data.saved, keys: data.keys.filter((k): k is string => typeof k === "string") };
  }
  return { ok: false, detail: errorDetail(data, response.status) };
}

/** GET /api/timeline: fetch a subject's Observations in time order, mapping every outcome to a typed result. */
export async function getTimeline(query: TimelineQuery): Promise<TimelineResult> {
  const params = new URLSearchParams();
  params.set("subject_id", query.subject_id);
  if (query.start) params.set("start", query.start);
  if (query.end) params.set("end", query.end);
  if (query.category) params.set("category", query.category);
  if (query.severity) params.set("severity", query.severity);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMELINE_TIMEOUT_MS);
  let response: Response;
  let data: unknown;
  try {
    response = await fetch(`${getApiBaseUrl()}/api/timeline?${params.toString()}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal: controller.signal,
    });
    data = await response.json().catch(() => null);
  } catch {
    return { ok: false, detail: `Impossible de joindre le serveur à ${getApiBaseUrl()}.` };
  } finally {
    clearTimeout(timer);
  }

  if (response.ok && isRecord(data) && Array.isArray(data.observations) && typeof data.count === "number") {
    return { ok: true, observations: data.observations.filter(isObservation), count: data.count };
  }
  return { ok: false, detail: errorDetail(data, response.status) };
}
