import type {
  Application,
  ApplicationAnswer,
  ApplicationPreview,
  ApplicationRun,
  ApplicationSession,
  ConfigStatus,
  Dashboard,
  Job,
  Preferences,
  Profile,
  SearchRun,
  TailoredCV,
} from "./types";

export const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";

type RequestOptions = RequestInit & { body?: BodyInit | null };

function describeApiDetail(item: unknown): string {
  if (typeof item === "string") return item;
  if (item && typeof item === "object") {
    const record = item as Record<string, unknown>;
    const location = Array.isArray(record.loc)
      ? record.loc.filter((part) => part !== "body").join(".")
      : "";
    const message = typeof record.msg === "string" ? record.msg : JSON.stringify(item);
    return location ? `${location}: ${message}` : message;
  }
  return String(item);
}

function apiErrorMessage(payload: unknown, status: number): string {
  if (!payload || typeof payload !== "object") return `Error ${status}`;
  const record = payload as Record<string, unknown>;
  if (typeof record.detail === "string") return record.detail;
  if (Array.isArray(record.detail)) {
    return record.detail.map(describeApiDetail).join("\n") || `Error ${status}`;
  }
  if (record.detail && typeof record.detail === "object") {
    return describeApiDetail(record.detail);
  }
  if (typeof record.message === "string") return record.message;
  return `Error ${status}`;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const raw = await response.text();
  let payload: unknown = null;
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = raw;
    }
  }
  if (!response.ok) {
    const message =
      typeof payload === "string" && payload.trim()
        ? payload.slice(0, 800)
        : apiErrorMessage(payload, response.status);
    throw new Error(message);
  }
  return payload as T;
}

function queryString(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== false) {
      search.set(key, String(value));
    }
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export const api = {
  dashboard: () => request<Dashboard>("/api/dashboard"),
  jobs: (params: {
    q?: string;
    remote_type?: string;
    min_score?: number;
    saved?: boolean;
    discarded?: boolean;
    include_ineligible?: boolean;
    max_age_days?: number;
    include_unknown_date?: boolean;
    limit?: number;
  } = {}) => request<{ items: Job[]; total: number }>(`/api/jobs${queryString(params)}`),
  job: (id: number) => request<{ job: Job }>(`/api/jobs/${id}`),
  importJob: (url: string) =>
    request<{ job: Job; created: boolean; extracted_with: string }>("/api/jobs/import-url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),
  updateJob: (id: number, status: Job["status"]) =>
    request<{ job: Job }>(`/api/jobs/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  discardJob: (id: number) => request<{ discarded: boolean; job: Job }>(`/api/jobs/${id}`, { method: "DELETE" }),
  restoreJob: (id: number) => request<{ restored: boolean; job: Job }>(`/api/jobs/${id}/restore`, { method: "POST" }),
  search: () => request<{ run: SearchRun }>("/api/search/run", { method: "POST" }),
  searchStatus: () => request<{ run: SearchRun | null }>("/api/search/status"),

  profile: () => request<{ exists: boolean; profile: Profile | null }>("/api/profile"),
  updateProfile: (data: Partial<Profile>) =>
    request<{ profile: Profile; warning?: string }>("/api/profile", { method: "PUT", body: JSON.stringify(data) }),
  uploadCv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{
      profile: Profile;
      parsed_with: string;
      message: string;
      search_suggestions?: {
        roles: string[];
        keywords: string[];
        source: string;
      };
      review?: {
        name: string;
        email: string;
        phone: string;
        location: string;
        headline: string;
        skills: string[];
        experience_count: number;
        education_count: number;
        languages: Record<string, string>;
        links: Record<string, string>;
        warnings: string[];
      };
    }>("/api/cv/upload", {
      method: "POST",
      body: form,
    });
  },
  originalCvUrl: () => `${API_BASE}/api/cv/original`,

  preferences: () => request<{ preferences: Preferences }>("/api/preferences"),
  updatePreferences: (data: Partial<Preferences>) =>
    request<{ preferences: Preferences; warning?: string }>("/api/preferences", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  tailor: (jobId: number) =>
    request<{ tailored: TailoredCV }>(`/api/jobs/${jobId}/tailor`, { method: "POST" }),
  updateTailored: (id: number, data: { approved?: boolean; content?: unknown }) =>
    request<{ tailored: TailoredCV }>(`/api/tailored/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  applicationPreview: (jobId: number, cvSource?: "tailored" | "original") =>
    request<{ preview: ApplicationPreview }>(
      `/api/jobs/${jobId}/application${queryString({ cv_source: cvSource })}`,
    ),
  prepareApplicationSession: (jobId: number, cvSource?: "tailored" | "original") =>
    request<{ session: ApplicationSession }>(`/api/jobs/${jobId}/application-session`, {
      method: "POST",
      body: JSON.stringify({ cv_source: cvSource }),
    }),
  applicationSession: (sessionId: number) =>
    request<{ session: ApplicationSession }>(`/api/application-sessions/${sessionId}`),
  sessionCvUrl: (sessionId: number) => `${API_BASE}/api/application-sessions/${sessionId}/cv`,
  draftAnswers: (jobId: number, questions: string[]) =>
    request<{ answers: ApplicationAnswer[] }>("/api/applications/draft-answers", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, questions }),
    }),
  autoRun: (maxItems?: number) =>
    request<{ run: ApplicationRun }>("/api/applications/auto-run", {
      method: "POST",
      body: JSON.stringify({ max_items: maxItems }),
    }),
  applicationRun: (runId: number) => request<{ run: ApplicationRun }>(`/api/application-runs/${runId}`),

  applications: () => request<{ items: Application[] }>("/api/applications"),
  createApplication: (data: {
    job_id: number;
    status: Application["status"];
    notes?: string;
    cv_source?: "tailored" | "original";
  }) =>
    request<{ application: Application }>("/api/applications", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateApplication: (id: number, data: { status?: Application["status"]; notes?: string }) =>
    request<{ application: Application }>(`/api/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  config: () => request<ConfigStatus>("/api/config/status"),
  testLlm: () =>
    request<{ ok: boolean; message: string; provider: string; model?: string; elapsed_ms?: number }>(
      "/api/llm/test",
      { method: "POST" },
    ),
  testEmail: () => request<{ sent: boolean; message: string }>("/api/alerts/test-email", { method: "POST" }),
  demoSeed: () => request<{ seeded: Record<string, unknown> }>("/api/demo/seed", { method: "POST" }),
  demoReset: () => request<{ reset: Record<string, unknown> }>("/api/demo/reset", { method: "POST" }),
  deleteData: () => request<{ deleted: boolean }>("/api/data", { method: "DELETE" }),
};
