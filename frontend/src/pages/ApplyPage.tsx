import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  Send,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Wand2,
  Zap,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { api } from "@/lib/api";
import type { ApplicationSession } from "@/lib/types";
import { cn } from "@/lib/utils";

const fieldLabels: Record<string, string> = {
  full_name: "Nombre completo",
  first_name: "Nombre",
  last_name: "Apellido",
  email: "Email",
  phone: "Teléfono",
  location: "Ubicación",
  city: "Ciudad",
  country: "País",
  linkedin: "LinkedIn",
  github: "GitHub",
  portfolio: "Portafolio",
  website: "Sitio web",
  current_title: "Cargo actual",
  current_company: "Empresa actual",
  years_experience: "Años de experiencia",
  salary_expectation: "Aspiración salarial",
  salary_currency: "Moneda",
};

function openSession(previewUrl: string, session: ApplicationSession) {
  let url = previewUrl;
  try {
    const parsed = new URL(previewUrl);
    parsed.hash = `jobradar-session=${session.id}`;
    url = parsed.toString();
  } catch {
    url = `${previewUrl}#jobradar-session=${session.id}`;
  }
  window.open(url, "_blank", "noopener,noreferrer");
  window.postMessage({ source: "jobradar-web", type: "SESSION_READY", sessionId: session.id }, "*");
}

export function ApplyPage() {
  const { id } = useParams();
  const jobId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [cvSource, setCvSource] = useState<"tailored" | "original">("tailored");
  const [lastSession, setLastSession] = useState<ApplicationSession | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["application-preview", jobId, cvSource],
    queryFn: () => api.applicationPreview(jobId, cvSource),
    enabled: Number.isFinite(jobId),
  });

  const prepareMutation = useMutation({
    mutationFn: () => api.prepareApplicationSession(jobId, cvSource),
    onSuccess: ({ session }) => {
      setLastSession(session);
      toast.success("Postulación preparada. Se abrió el portal con el asistente.");
      openSession(session.job?.url || data?.preview.job.url || "", session);
      queryClient.invalidateQueries({ queryKey: ["application-session", session.id] });
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  const appliedMutation = useMutation({
    mutationFn: () => api.createApplication({ job_id: jobId, status: "applied", cv_source: cvSource }),
    onSuccess: () => {
      toast.success("Postulación registrada en el tracker.");
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      navigate("/tracker");
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-32 animate-pulse rounded bg-white/[0.04]" />
        <div className="grid gap-6 xl:grid-cols-3">
          <div className="card h-[560px] animate-pulse bg-white/[0.02] xl:col-span-2" />
          <div className="card h-[460px] animate-pulse bg-white/[0.02]" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <EmptyState
        icon={Wand2}
        title="No pudimos preparar esta postulación"
        description={error instanceof Error ? error.message : "Vuelve a la vacante e inténtalo de nuevo."}
        action={
          <Link to={`/jobs/${jobId}`} className="btn-primary">
            Volver a la vacante
          </Link>
        }
      />
    );
  }

  const preview = data.preview;
  const job = preview.job;
  const portal = preview.portal;
  const tailored = preview.cv_options.tailored;
  const original = preview.cv_options.original;
  const selectedCv = preview.cv_options[cvSource];
  const isManual = portal.mode === "manual_only";

  return (
    <div className="animate-fade-up">
      <Link
        to={`/jobs/${job.id}`}
        className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-muted transition hover:text-white"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Volver a la vacante
      </Link>

      <div className="mb-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-primary">Asistente de postulación</p>
        <h1 className="mt-2 font-display text-2xl font-semibold text-white">{job.title}</h1>
        <p className="mt-1 text-sm text-muted">
          {job.company} · {job.location_text}
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <section
            className={cn(
              "card p-5 sm:p-6",
              portal.mode === "auto_submit" && "border-emerald-400/20",
              portal.mode === "manual_only" && "border-amber-400/20",
            )}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ring-1",
                    portal.mode === "auto_submit"
                      ? "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20"
                      : portal.mode === "assisted"
                        ? "bg-cyan-400/10 text-cyan-300 ring-cyan-400/20"
                        : "bg-amber-400/10 text-amber-300 ring-amber-400/20",
                  )}
                >
                  {portal.mode === "auto_submit" ? (
                    <Zap className="h-4 w-4" />
                  ) : portal.mode === "assisted" ? (
                    <ShieldCheck className="h-4 w-4" />
                  ) : (
                    <ExternalLink className="h-4 w-4" />
                  )}
                </div>
                <div>
                  <h2 className="section-title">
                    {isManual
                      ? "Este portal es solo manual"
                      : portal.mode === "auto_submit"
                        ? "Portal compatible con auto-envío"
                        : "Portal asistido con revisión"}
                  </h2>
                  <p className="mt-1 text-xs leading-relaxed text-muted">{portal.reason}</p>
                </div>
              </div>
              <span className="chip">{portal.label}</span>
            </div>
            {portal.mode === "auto_submit" && (
              <p className="mt-4 rounded-xl border border-emerald-400/15 bg-emerald-400/[0.05] p-3 text-[11px] leading-relaxed text-emerald-100/70">
                El auto-envío solo se ejecuta si lo activas en Ajustes. Aun así, el asistente reporta el resultado y
                guarda el registro en el tracker.
              </p>
            )}
          </section>

          <section className="card p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="section-title">Hoja de vida para esta postulación</h2>
                <p className="mt-1 text-xs text-muted">El CV adaptado es el predeterminado. Puedes elegir el PDF original.</p>
              </div>
              <FileText className="h-4 w-4 text-muted" />
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <label
                className={cn(
                  "cursor-pointer rounded-xl border p-4 transition",
                  cvSource === "tailored"
                    ? "border-primary/40 bg-primary/[0.06]"
                    : "border-line bg-white/[0.02] hover:border-primary/25",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="flex items-center gap-2 text-sm font-semibold text-white">
                      <Sparkles className="h-4 w-4 text-primary" /> CV adaptado ATS
                    </p>
                    <p className="mt-1 text-[11px] leading-relaxed text-muted">
                      {tailored.available ? tailored.file_name : "Se generará al preparar la postulación."}
                    </p>
                    {tailored.available && (
                      <p className="mt-2 text-[10px] font-medium text-emerald-300">
                        {tailored.approved ? "Aprobado" : "Borrador: revísalo antes de enviar"}
                      </p>
                    )}
                  </div>
                  <input
                    type="radio"
                    name="cv-source"
                    checked={cvSource === "tailored"}
                    onChange={() => setCvSource("tailored")}
                    className="mt-1 accent-emerald-400"
                  />
                </div>
              </label>

              <label
                className={cn(
                  "cursor-pointer rounded-xl border p-4 transition",
                  !original.available && "cursor-not-allowed opacity-60",
                  cvSource === "original"
                    ? "border-primary/40 bg-primary/[0.06]"
                    : "border-line bg-white/[0.02] hover:border-primary/25",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="flex items-center gap-2 text-sm font-semibold text-white">
                      <FileText className="h-4 w-4 text-cyan-300" /> PDF original
                    </p>
                    <p className="mt-1 text-[11px] leading-relaxed text-muted">
                      {original.available ? original.file_name : "No hay un CV original disponible."}
                    </p>
                    <p className="mt-2 text-[10px] text-slate-500">Conserva el diseño y formato que subiste.</p>
                  </div>
                  <input
                    type="radio"
                    name="cv-source"
                    checked={cvSource === "original"}
                    disabled={!original.available}
                    onChange={() => setCvSource("original")}
                    className="mt-1 accent-emerald-400"
                  />
                </div>
              </label>
            </div>

            {selectedCv.available &&
              selectedCv.download_url &&
              (cvSource === "original" || selectedCv.approved) && (
                <a
                  href={selectedCv.download_url}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-secondary mt-4 w-full text-xs"
                >
                  <Download className="h-3.5 w-3.5" /> Ver / descargar CV seleccionado
                </a>
              )}
            {cvSource === "tailored" && selectedCv.available && !selectedCv.approved && (
              <p className="mt-3 text-[10px] leading-relaxed text-amber-200/70">
                El CV adaptado está en borrador.{" "}
                <Link to={`/jobs/${job.id}/tailor`} className="underline">
                  Revísalo y apruébalo
                </Link>{" "}
                si quieres descargarlo antes de postular.
              </p>
            )}
          </section>

          {!isManual && (
            <section className="card p-5 sm:p-6">
              <h2 className="section-title">Datos que se rellenarán</h2>
              <p className="mt-1 text-xs text-muted">
                Revísalos antes de abrir el portal. El asistente solo completa campos que reconoce y te deja revisar.
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {Object.entries(preview.fields)
                  .filter(([, value]) => Boolean(value))
                  .map(([key, value]) => (
                    <div key={key} className="rounded-xl border border-line/60 bg-white/[0.02] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">
                        {fieldLabels[key] ?? key}
                      </p>
                      <p className="mt-1 break-words text-xs text-slate-200">{value}</p>
                    </div>
                  ))}
              </div>
              {preview.cover_letter && (
                <div className="mt-4">
                  <p className="label">Carta de presentación</p>
                  <div className="max-h-56 overflow-auto whitespace-pre-wrap rounded-xl border border-line/60 bg-ink/40 p-4 text-xs leading-relaxed text-slate-300">
                    {preview.cover_letter}
                  </div>
                </div>
              )}
            </section>
          )}

          {preview.warnings.length > 0 && (
            <section className="rounded-2xl border border-amber-400/20 bg-amber-400/[0.04] p-5">
              <div className="flex items-center gap-2 text-amber-300">
                <TriangleAlert className="h-4 w-4" />
                <h2 className="text-sm font-semibold">Antes de enviar</h2>
              </div>
              <ul className="mt-3 space-y-2">
                {preview.warnings.map((warning) => (
                  <li key={warning} className="text-[11px] leading-relaxed text-amber-100/70">
                    {warning}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
          <section className="card p-5">
            <h2 className="section-title">Acciones</h2>
            <div className="mt-4 space-y-2">
              {!isManual && (
                <button
                  type="button"
                  onClick={() => prepareMutation.mutate()}
                  disabled={prepareMutation.isPending}
                  className="btn-primary w-full"
                >
                  {prepareMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Wand2 className="h-4 w-4" />
                  )}
                  {prepareMutation.isPending ? "Preparando..." : "Abrir portal con asistente"}
                </button>
              )}
              {job.url && (
                <a href={job.url} target="_blank" rel="noreferrer" className="btn-secondary w-full">
                  <ExternalLink className="h-4 w-4" /> Abrir portal original
                </a>
              )}
              <button
                type="button"
                onClick={() => appliedMutation.mutate()}
                disabled={appliedMutation.isPending}
                className="btn-secondary w-full"
              >
                {appliedMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                )}
                Ya postulé / registrar
              </button>
              {lastSession && (
                <button
                  type="button"
                  onClick={() => openSession(job.url, lastSession)}
                  className="btn-ghost w-full text-xs"
                >
                  <Send className="h-3.5 w-3.5" /> Abrir de nuevo la sesión #{lastSession.id}
                </button>
              )}
            </div>
            <p className="mt-3 text-[10px] leading-relaxed text-slate-600">
              JobRadar no guarda contraseñas de portales. El asistente usa tu sesión real del navegador y nunca
              intenta evadir CAPTCHA ni verificación en dos pasos.
            </p>
          </section>

          <section className="rounded-2xl border border-dashed border-line p-4 text-[11px] leading-relaxed text-muted">
            <p className="flex items-center gap-1.5 font-semibold text-slate-300">
              <ShieldCheck className="h-3.5 w-3.5 text-primary" /> Revisión humana
            </p>
            <p className="mt-2">
              {portal.mode === "manual_only"
                ? "Completa el formulario directamente en el portal; no se automatiza nada."
                : "El asistente rellena, tú revisas cada campo y confirmas el envío. El auto-envío es opcional y solo para portales permitidos."}
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}
