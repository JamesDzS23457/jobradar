export type Match = {
  id?: number;
  score: number;
  eligible: boolean;
  subscores: Record<string, number>;
  reasons: string[];
  gaps: string[];
  red_flags: string[];
  recommendation: string;
  model: string;
  fit_level: "exact" | "stretch" | "not_fit" | "link_only";
  stretch_reasons: string[];
};

export type ExperienceItem = {
  company: string;
  role: string;
  dates: string;
  bullets: string[];
  source_bullets?: number[];
};

export type EducationItem = {
  institution: string;
  degree: string;
  dates: string;
};

export type Profile = {
  id: number;
  name: string;
  email: string;
  phone: string;
  location: string;
  headline: string;
  summary: string;
  skills: string[];
  experience: ExperienceItem[];
  education: EducationItem[];
  languages: Record<string, string>;
  links: Record<string, string>;
  years_experience: number;
  has_cv: boolean;
  cv_file_name: string;
  cv_original_url: string;
  updated_at: string;
};

export type PortalMode = "manual_only" | "assisted" | "auto_submit";

export type PortalInfo = {
  source: string;
  label: string;
  domain: string;
  mode: PortalMode;
  can_assist: boolean;
  can_auto_submit: boolean;
  reason: string;
};

export type Preferences = {
  id: number;
  roles: string[];
  keywords: string[];
  home_city: string;
  commute_cities: string[];
  country: string;
  remote_preference: string;
  accept_relocation: boolean;
  accept_international_remote: boolean;
  timezone: string;
  salary_min: number;
  currency: string;
  seniority: string;
  contract_types: string[];
  languages: Record<string, string>;
  alert_threshold: number;
  digest_threshold: number;
  digest_hour: number;
  search_interval_hours: number;
  blacklist_companies: string[];
  blacklist_keywords: string[];
  freshness_days: number;
  auto_submit_enabled: boolean;
  auto_submit_max_per_run: number;
  default_cv_source: "tailored" | "original";
  updated_at: string;
};

export type Job = {
  id: number;
  source: string;
  title: string;
  company: string;
  description?: string;
  location_text: string;
  city: string;
  country: string;
  remote_type: "remote" | "hybrid" | "onsite" | "unknown";
  remote_scope: string;
  salary_min: number | null;
  salary_max: number | null;
  currency: string;
  url: string;
  posted_at: string | null;
  status: "new" | "saved" | "dismissed" | "applied" | "discarded";
  imported_manually: boolean;
  link_only: boolean;
  requires_login: boolean;
  access_note: string;
  collector: string;
  skills_required: string[];
  skills_nice: string[];
  seniority: string;
  years_experience: number;
  languages: Record<string, string>;
  red_flags: string[];
  match: Match | null;
  portal: PortalInfo;
};

export type SearchRun = {
  id: number;
  started_at: string;
  finished_at: string | null;
  found: number;
  new: number;
  sources: Record<string, number>;
  errors: string[];
};

export type Dashboard = {
  profile_complete: boolean;
  profile_name: string;
  headline: string;
  home_city: string;
  stats: {
    total_jobs: number;
    eligible_jobs: number;
    potential_jobs: number;
    excellent: number;
    good: number;
    applied: number;
    interviews: number;
    offers: number;
    average_score: number;
  };
  top_matches: Job[];
  distribution: { range: string; count: number }[];
  last_run: SearchRun | null;
  recent_applications: Application[];
};

export type Application = {
  id: number;
  job_id: number;
  status: "saved" | "applied" | "interview" | "offer" | "rejected";
  applied_at: string | null;
  notes: string;
  next_action_at: string | null;
  cv_source: "tailored" | "original";
  cv_file_name: string;
  portal_mode: PortalMode;
  application_url: string;
  created_at: string;
  updated_at: string;
  job: Job | null;
};

export type TailoredContent = {
  headline: string;
  summary: string;
  skills_priority: string[];
  experience: ExperienceItem[];
  education: EducationItem[];
  keywords_added: string[];
  cover_letter: string;
  strengths: string[];
  gaps: string[];
  warnings: string[];
  model?: string;
};

export type TailoredCV = {
  id: number;
  job_id: number;
  content: TailoredContent;
  approved: boolean;
  created_at: string;
  docx_url: string;
  pdf_url: string;
};

export type CvOption = {
  available: boolean;
  file_name: string;
  approved?: boolean;
  download_url: string;
};

export type ApplicationPreview = {
  job: Job;
  portal: PortalInfo;
  cv_source: "tailored" | "original";
  cv_options: {
    tailored: CvOption;
    original: CvOption;
  };
  fields: Record<string, string>;
  cover_letter: string;
  warnings: string[];
  can_assist: boolean;
  can_auto_submit: boolean;
};

export type ApplicationSession = {
  id: number;
  job_id: number;
  run_id: number | null;
  status: string;
  portal_mode: PortalMode;
  portal: PortalInfo | null;
  cv_source: "tailored" | "original";
  cv_file_name: string;
  cv_url: string;
  fields: Record<string, string>;
  answers: Record<string, unknown>;
  message: string;
  created_at: string;
  updated_at: string;
  job: Job | null;
};

export type ApplicationAnswer = {
  question: string;
  answer: string;
  confidence: "high" | "medium" | "low";
  needs_user_input: boolean;
  source: string;
};

export type ApplicationRunItem = {
  id: number;
  run_id: number;
  job_id: number;
  session_id: number | null;
  status: "queued" | "processing" | "submitted" | "manual" | "failed" | "skipped";
  message: string;
  updated_at: string;
  job: Job | null;
};

export type ApplicationRun = {
  id: number;
  status: "running" | "completed";
  max_items: number;
  total: number;
  submitted: number;
  manual: number;
  failed: number;
  created_at: string;
  finished_at: string | null;
  items: ApplicationRunItem[];
};

export type ConfigStatus = {
  app_name: string;
  demo_mode: boolean;
  llm_configured: boolean;
  llm_provider: string;
  llm_base_url: string;
  llm_model: string | null;
  llm_model_fast: string;
  llm_model_quality: string;
  llm_model_fallback: string;
  auto_submit_enabled: boolean;
  auto_submit_max_per_run: number;
  auto_submit_portals: string[];
  manual_only_portals: string[];
  default_cv_source: "tailored" | "original";
  smtp_configured: boolean;
  jsearch_configured: boolean;
  jooble_configured: boolean;
  web_search_provider: string;
  tavily_configured: boolean;
  tavily_keyless: boolean;
  brave_configured: boolean;
  scheduler_enabled: boolean;
  alert_threshold: number;
  database: string;
};
