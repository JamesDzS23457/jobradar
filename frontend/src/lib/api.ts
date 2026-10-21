import type {
  Application,
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

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = `Error ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail || payload.message || message;
    } catch {
      // Keep the status message.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
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
    include_ineligible?: boolean;
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
  search: () => request<{ run: SearchRun }>("/api/search/run", { method: "POST" }),
  searchStatus: () => request<{ run: SearchRun | null }>("/api/search/status"),

  profile: () => request<{ exists: boolean; profile: Profile | null }>("/api/profile"),
  updateProfile: (data: Partial<Profile>) =>
    request<{ profile: Profile }>("/api/profile", { method: "PUT", body: JSON.stringify(data) }),
  uploadCv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ profile: Profile; parsed_with: string; message: string }>("/api/cv/upload", {
      method: "POST",
      body: form,
    });
  },

  preferences: () => request<{ preferences: Preferences }>("/api/preferences"),
  updatePreferences: (data: Partial<Preferences>) =>
    request<{ preferences: Preferences }>("/api/preferences", {
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

  applications: () => request<{ items: Application[] }>("/api/applications"),
  createApplication: (data: { job_id: number; status: Application["status"]; notes?: string }) =>
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
  testEmail: () => request<{ sent: boolean; message: string }>("/api/alerts/test-email", { method: "POST" }),
  demoSeed: () => request<{ seeded: Record<string, unknown> }>("/api/demo/seed", { method: "POST" }),
  demoReset: () => request<{ reset: Record<string, unknown> }>("/api/demo/reset", { method: "POST" }),
  deleteData: () => request<{ deleted: boolean }>("/api/data", { method: "DELETE" }),
};
