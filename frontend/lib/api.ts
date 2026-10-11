/**
 * Base API client for the Karis backend.
 *
 * The base URL is public (exposed to the browser) and defaults to the local
 * FastAPI dev server.
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    path: string,
    detail?: string,
  ) {
    super(detail ?? (status === 404 ? "Cet élément n’est plus disponible. Revenez à l’accueil après une réinitialisation." : "Une erreur est survenue. Les données déjà enregistrées ont été conservées."));
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: isFormData ? { ...init?.headers } : { "Content-Type": "application/json", ...init?.headers },
  }).catch(() => { throw new Error("Connexion à Karis indisponible. Vérifiez que le serveur est lancé, puis réessayez."); });
  if (!res.ok) {
    const error = await res.json().catch(() => null);
    throw new ApiError(
      res.status, path,
      typeof error?.detail === "string" && /[àâéèêîôùûçœ’]/i.test(error.detail) ? error.detail : undefined,
    );
  }
  return res.json() as Promise<T>;
}

export interface HealthResponse {
  status: string;
  service: string;
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function api<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>(`/api${path}`, init);
}

export function uploadAudio<T>(path: string, file: Blob): Promise<T> {
  const form = new FormData();
  form.append("audio", file, "recording.webm");
  return api<T>(path, { method: "POST", body: form });
}

export type User = { id: string; full_name: string; email: string | null };
export type ProviderMetadata = {
  provider_used: "mock" | "bedrock" | "mock-fallback";
  model_id: string | null;
  latency_ms: number;
  validation_retry_count: number;
  fallback_used: boolean;
};
export type Recipient = { id: string; first_name: string; last_name: string; date_of_birth?: string | null };
export type Member = { id: string; user_id: string; name: string; role: string; active: boolean };
export type Observation = { id: string; category: string; description: string; visibility: string };
export type Action = { id: string; description: string; status: string };
export type Clarification = {
  id: string; question: string; reason: string; answer: string | null;
  answered_at: string | null;
};
export type Journal = {
  provider_metadata?: ProviderMetadata | null;
  id: string; care_recipient_id: string; status: string; input_type: "text" | "voice";
  original_text: string; short_summary: string | null; observations: Observation[];
  caregiver_feelings: { id: string; description: string; visibility: string }[];
  actions: Action[]; has_private_data: boolean;
  clarifications: Clarification[]; clarification_needed: boolean;
  transcript?: string | null; audio_object_key?: string | null;
};
export type Timeline = { items: Array<{
  id: string; date: string; short_summary: string; observations: Observation[];
  actions: Action[]; source_type: "text" | "voice"; has_private_data: boolean;
}> };
export type MultimodalContext = {
  journal_entry_id: string;
  transcript_or_text: string;
  semantic_analysis: Record<string, unknown>;
  caregiver_vocal_affect: {
    source: string; valence: string | null; arousal: string | null;
    top_label: string | null; confidence: number; quality: string;
    model_version: string; visibility: string; provider: string;
  } | null;
  caregiver_wearable: {
    source: string; subject_type: string; metrics: Record<string, number>;
    quality: string; visibility: string; provider: string;
  } | null;
  care_recipient_wearable: {
    source: string; subject_type: string; metrics: Record<string, number>;
    quality: string; visibility: string; provider: string;
  } | null;
  modalities_present: string[];
  provenance: Record<string, string>;
};
export type Message = {
  provider_metadata?: ProviderMetadata | null;
  privacy_pipeline?: { structured_count: number; shareable_count: number; authorized_count: number; transmitted_count: number; private_transmitted_count: number } | null;
  id: string; recipient_member_id: string; recipient_name: string; recipient_role: string;
  source_entry_id: string | null; channel: string; text: string; approved: boolean;
  delivery_status: string; sent_at: string | null; structured_item_count: number;
  allowed_item_count: number; excluded_private_count: number;
};
export type MessageGeneration = { drafts: Message[] };
export type MockInbox = { messages: Array<{
  id: string; recipient_name: string; recipient_role: string; channel: string;
  text: string; delivery_status: string; sent_at: string;
}> };
export type WeeklyReport = {
  provider_metadata?: ProviderMetadata | null;
  id: string; recipient_id: string; period_start: string; period_end: string;
  title: string; content: string; approved: boolean; approved_at: string | null;
  source_entry_count: number; structured_item_count: number;
  reportable_item_count: number; excluded_private_count: number;
};
