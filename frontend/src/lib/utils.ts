import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Job } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatSalary(job: Pick<Job, "salary_min" | "salary_max" | "currency">): string {
  if (!job.salary_min && !job.salary_max) return "Salario no publicado";
  const currency = job.currency || "COP";
  const format = (value: number | null) => {
    if (!value) return "";
    if (currency === "COP") {
      return value >= 1_000_000 ? `$${(value / 1_000_000).toFixed(0)}M` : `$${value.toLocaleString("es-CO")}`;
    }
    return value >= 1000 ? `$${Math.round(value / 1000)}k` : `$${value}`;
  };
  const min = format(job.salary_min);
  const max = format(job.salary_max);
  if (min && max) return `${min} – ${max} ${currency}`;
  return `${min || max} ${currency}`;
}

export function timeAgo(value: string | null | undefined): string {
  if (!value) return "Sin fecha";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sin fecha";
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "Hace un momento";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `Hace ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `Hace ${hours} h`;
  const days = Math.round(hours / 24);
  if (days === 1) return "Ayer";
  if (days < 30) return `Hace ${days} días`;
  const months = Math.round(days / 30);
  return `Hace ${months} mes${months > 1 ? "es" : ""}`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "numeric" });
}

export function remoteLabel(type: Job["remote_type"] | string): string {
  if (type === "remote") return "Remoto";
  if (type === "hybrid") return "Híbrido";
  if (type === "onsite") return "Presencial";
  return "No definido";
}

export function scoreColor(score: number): string {
  if (score >= 85) return "text-emerald-400";
  if (score >= 70) return "text-cyan-300";
  if (score >= 55) return "text-amber-300";
  return "text-rose-300";
}

export function scoreStroke(score: number): string {
  if (score >= 85) return "#34d399";
  if (score >= 70) return "#22d3ee";
  if (score >= 55) return "#fbbf24";
  return "#fb7185";
}

export function scoreLabel(score: number): string {
  if (score >= 85) return "Excelente";
  if (score >= 70) return "Buen match";
  if (score >= 55) return "Para revisar";
  return "Match bajo";
}

export function initials(value: string): string {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "JR";
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");
}

export function parseList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinList(values: string[] | undefined): string {
  return (values ?? []).join(", ");
}


export function collectorLabel(value: string | undefined | null): string {
  const key = (value || "").toLowerCase();
  const labels: Record<string, string> = {
    jsearch: "JSearch",
    jooble: "Jooble",
    tavily: "Tavily",
    websearch: "Búsqueda web",
    remotive: "Remotive",
    remoteok: "RemoteOK",
    manual: "Importación manual",
    demo: "Demo",
  };
  return labels[key] || (key ? key.charAt(0).toUpperCase() + key.slice(1) : "JobRadar");
}
