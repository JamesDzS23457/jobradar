import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Download,
  FileText,
  GitCompare,
  Loader2,
  Mail,
  Sparkles,
  ThumbsUp,
} from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { ScoreRing } from "@/components/ScoreRing";
import { API_BASE, api } from "@/lib/api";
import type { TailoredCV } from "@/lib/types";
import { cn, scoreLabel } from "@/lib/utils";

type Tab = "cv" | "cover" | "changes" | "warnings";

const tabs: { id: Tab; label: string; icon: typeof FileText }[] = [
  { id: "cv", label: "CV adaptado", icon: FileText },
  { id: "cover", label: "Carta", icon: Mail },
  { id: "changes", label: "Cambios", icon: GitCompare },
  { id: "warnings", label: "Advertencias", icon: AlertTriangle },
];

export function TailorPage() {
  const { id } = useParams();
  const jobId = Number(id);
  const [tailored, setTailored] = useState<TailoredCV | null>(null);
  const [tab, setTab] = useState<Tab>("cv");

  const { data: jobData, isLoading } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.job(jobId),
    enabled: Number.isFinite(jobId),
  });

  const { data: profileData } = useQuery({
    queryKey: ["profile"],
    queryFn: api.profile,
  });

  const generateMutation = useMutation({
    mutationFn: () => api.tailor(jobId),
    onSuccess: (data) => {
      setTailored(data.tailored);
      setTab("cv");
      toast.success("CV adaptado generado. Revísalo antes de descargarlo.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const approveMutation = useMutation({
    mutationFn: () => api.updateTailored(tailored!.id, { approved: true }),
    onSuccess: (data) => {
      setTailored(data.tailored);
      toast.success("CV aprobado. Ya puedes descargarlo.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-32 animate-pulse rounded bg-white/[0.04]" />
        <div className="card h-[600px] animate-pulse bg-white/[0.02]" />
      </div>
    );
  }

  if (!jobData) {
    return (
      <EmptyState
        icon={FileText}
        title="No encontramos la vacante"
        description="Vuelve a la lista de vacantes y elige una oferta."
        action={
          <Link to="/jobs" className="btn-primary">
            Ver vacantes
          </Link>
        }
      />
    );
  }

  const job = jobData.job;
  const content = tailored?.content;
  const candidate = profileData?.profile;
  const contactLine = [candidate?.email, candidate?.phone, candidate?.location].filter(Boolean).join(" · ");

  return (
    <div className="animate-fade-up">
      <Link to={`/jobs/${job.id}`} className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-muted transition hover:text-white">
        <ArrowLeft className="h-3.5 w-3.5" /> Volver a la vacante
      </Link>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Estudio de adaptación</p>
          <h1 className="font-display text-2xl font-semibold text-white sm:text-3xl">{job.title}</h1>
          <p className="mt-1 text-sm text-muted">
            {job.company} · {job.location_text}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {job.match && <ScoreRing score={job.match.score} size={58} stroke={4} />}
          <div className="text-xs text-muted">
            <p className="font-medium text-slate-200">{job.match ? scoreLabel(job.match.score) : "Sin match"}</p>
            <p>compatibilidad actual</p>
          </div>
        </div>
      </div>

      {!tailored ? (
        <div className="grid gap-6 xl:grid-cols-3">
          <div className="card relative overflow-hidden p-8 xl:col-span-2">
            <div className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full border border-primary/10" />
            <div className="pointer-events-none absolute -right-10 -top-14 h-48 w-48 rounded-full border border-primary/10" />
            <div className="relative">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary ring-1 ring-primary/20">
                <Sparkles className="h-7 w-7" />
              </div>
              <h2 className="mt-6 font-display text-2xl font-semibold text-white">Un CV pensado para esta vacante</h2>
              <p className="mt-3 max-w-xl text-sm leading-7 text-muted">
                La IA reordena y reformula tu experiencia real para destacar lo que esta oferta pide. No inventa
                empresas, cargos ni métricas: tú revisas, editas y apruebas antes de descargar.
              </p>
              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                {[
                  ["Sin inventar", "Solo información de tu perfil"],
                  ["Formato ATS", "Sin tablas ni columnas"],
                  ["Tú apruebas", "Descarga cuando esté listo"],
                ].map(([title, description]) => (
                  <div key={title} className="rounded-xl border border-line/60 bg-white/[0.02] p-3">
                    <p className="text-xs font-semibold text-slate-200">{title}</p>
                    <p className="mt-1 text-[11px] leading-relaxed text-muted">{description}</p>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
                className="btn-primary mt-7"
              >
                {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {generateMutation.isPending ? "Generando CV..." : "Generar CV adaptado"}
              </button>
              {generateMutation.isPending && (
                <p className="mt-3 text-[11px] text-muted">
                  Analizando la vacante y reescribiendo tu experiencia. Puede tardar unos segundos.
                </p>
              )}
            </div>
          </div>

          <div className="space-y-4">
            <div className="card p-5">
              <p className="label">Lo que se adaptará</p>
              <ul className="mt-2 space-y-2.5 text-xs leading-relaxed text-slate-300">
                <li className="flex gap-2">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" /> Resumen profesional alineado al rol
                </li>
                <li className="flex gap-2">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" /> Skills priorizadas según la oferta
                </li>
                <li className="flex gap-2">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" /> Bullets de experiencia reordenados
                </li>
                <li className="flex gap-2">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" /> Carta de presentación
                </li>
              </ul>
            </div>
            <div className="rounded-2xl border border-dashed border-line p-4 text-[11px] leading-relaxed text-muted">
              <p className="flex items-center gap-1.5 font-semibold text-slate-300">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-400" /> Guardrail
              </p>
              <p className="mt-2">
                Si una afirmación no se puede respaldar con tu CV, se marca como advertencia. No envíes nada sin revisarlo.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-3">
          <div className="xl:col-span-2">
            <div className="mb-3 flex flex-wrap items-center gap-1 rounded-xl border border-line bg-surface/70 p-1">
              {tabs.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setTab(item.id)}
                    className={cn(
                      "flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition",
                      tab === item.id ? "bg-primary/10 text-primary" : "text-muted hover:text-slate-200",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {item.label}
                  </button>
                );
              })}
            </div>

            {tab === "cv" && content && (
              <article className="paper rounded-2xl p-8 shadow-2xl sm:p-10">
                <header className="border-b border-slate-200 pb-5">
                  <h1 className="font-display text-3xl font-semibold tracking-tight text-slate-900">
                    {candidate?.name || "Tu nombre"}
                  </h1>
                  <p className="mt-1 text-sm font-medium text-emerald-700">{content.headline}</p>
                  <p className="mt-2 text-xs text-slate-500">{contactLine || "Tu email · tu teléfono · tu ciudad"}</p>
                </header>

                <section className="mt-6">
                  <h2 className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Perfil</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{content.summary}</p>
                </section>

                <section className="mt-6">
                  <h2 className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Habilidades</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{content.skills_priority.join(" · ")}</p>
                </section>

                <section className="mt-6">
                  <h2 className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Experiencia</h2>
                  <div className="mt-3 space-y-5">
                    {content.experience.map((item, index) => (
                      <div key={`${item.company}-${index}`}>
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <h3 className="text-sm font-semibold text-slate-900">
                            {item.role} <span className="font-normal text-slate-500">— {item.company}</span>
                          </h3>
                          <span className="text-[11px] text-slate-500">{item.dates}</span>
                        </div>
                        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">
                          {item.bullets.map((bullet, bulletIndex) => (
                            <li key={bulletIndex}>{bullet}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </section>

                {content.education.length > 0 && (
                  <section className="mt-6">
                    <h2 className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Educación</h2>
                    <div className="mt-2 space-y-1">
                      {content.education.map((item, index) => (
                        <p key={index} className="text-sm text-slate-700">
                          {item.degree} — {item.institution} <span className="text-slate-500">({item.dates})</span>
                        </p>
                      ))}
                    </div>
                  </section>
                )}
              </article>
            )}

            {tab === "cover" && content && (
              <article className="card p-6 sm:p-8">
                <h2 className="font-display text-lg font-semibold text-white">Carta de presentación</h2>
                <p className="mt-1 text-xs text-muted">Revísala y personaliza el tono antes de enviarla.</p>
                <div className="mt-5 whitespace-pre-line text-sm leading-7 text-slate-300">{content.cover_letter}</div>
              </article>
            )}

            {tab === "changes" && content && (
              <div className="space-y-4">
                <section className="card p-5">
                  <h2 className="section-title">Palabras clave alineadas</h2>
                  <p className="mt-1 text-xs text-muted">Tecnologías de la vacante que ya están en tu perfil.</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {content.keywords_added.map((keyword) => (
                      <span key={keyword} className="chip border-primary/20 bg-primary/[0.06] text-emerald-200">
                        {keyword}
                      </span>
                    ))}
                    {content.keywords_added.length === 0 && <p className="text-xs text-muted">No se añadieron keywords nuevas.</p>}
                  </div>
                </section>
                <div className="grid gap-4 sm:grid-cols-2">
                  <section className="card p-5">
                    <h2 className="section-title text-emerald-300">Fortalezas</h2>
                    <ul className="mt-3 space-y-2">
                      {content.strengths.map((item) => (
                        <li key={item} className="flex gap-2 text-xs leading-relaxed text-slate-300">
                          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </section>
                  <section className="card p-5">
                    <h2 className="section-title text-amber-300">Brechas</h2>
                    <ul className="mt-3 space-y-2">
                      {content.gaps.length > 0 ? (
                        content.gaps.map((item) => (
                          <li key={item} className="flex gap-2 text-xs leading-relaxed text-slate-400">
                            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
                            {item}
                          </li>
                        ))
                      ) : (
                        <li className="text-xs text-muted">No se detectaron brechas importantes.</li>
                      )}
                    </ul>
                  </section>
                </div>
              </div>
            )}

            {tab === "warnings" && content && (
              <div className="space-y-4">
                {content.warnings.length > 0 ? (
                  content.warnings.map((warning) => (
                    <div key={warning} className="flex gap-3 rounded-2xl border border-amber-400/20 bg-amber-400/[0.06] p-4">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                      <p className="text-xs leading-relaxed text-amber-100/80">{warning}</p>
                    </div>
                  ))
                ) : (
                  <div className="flex gap-3 rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.06] p-4">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                    <p className="text-xs leading-relaxed text-emerald-100/80">No hay advertencias. Aun así, revisa el CV antes de enviarlo.</p>
                  </div>
                )}
                <div className="rounded-2xl border border-dashed border-line p-4 text-[11px] leading-relaxed text-muted">
                  <p className="font-semibold text-slate-300">Modelo utilizado</p>
                  <p className="mt-1">{content.model || "heurístico"}</p>
                </div>
              </div>
            )}
          </div>

          <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
            <div className="card p-5">
              <div className="flex items-center justify-between">
                <p className="label">Estado</p>
                <span
                  className={cn(
                    "rounded-full px-2 py-1 text-[10px] font-semibold ring-1",
                    tailored.approved
                      ? "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20"
                      : "bg-amber-400/10 text-amber-300 ring-amber-400/20",
                  )}
                >
                  {tailored.approved ? "Aprobado" : "Borrador"}
                </span>
              </div>
              <p className="mt-3 text-xs leading-relaxed text-muted">
                Revisa el CV, la carta y las advertencias. Cuando estés conforme, apruébalo y descarga los archivos.
              </p>
              <button
                type="button"
                onClick={() => approveMutation.mutate()}
                disabled={tailored.approved || approveMutation.isPending}
                className="btn-primary mt-4 w-full"
              >
                {approveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ThumbsUp className="h-4 w-4" />}
                {tailored.approved ? "CV aprobado" : "Aprobar CV"}
              </button>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <a
                  href={`${API_BASE}${tailored.docx_url}`}
                  className={cn("btn-secondary w-full text-xs", !tailored.approved && "pointer-events-none opacity-50")}
                >
                  <Download className="h-3.5 w-3.5" /> DOCX
                </a>
                <a
                  href={`${API_BASE}${tailored.pdf_url}`}
                  className={cn("btn-secondary w-full text-xs", !tailored.approved && "pointer-events-none opacity-50")}
                >
                  <Download className="h-3.5 w-3.5" /> PDF
                </a>
              </div>
              {!tailored.approved && <p className="mt-2 text-center text-[10px] text-slate-600">Aprueba para habilitar descargas.</p>}
            </div>

            <div className="card p-5">
              <p className="label">Vacante</p>
              <p className="text-sm font-semibold text-white">{job.title}</p>
              <p className="mt-1 text-xs text-muted">{job.company}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {job.skills_required.slice(0, 5).map((skill) => (
                  <span key={skill} className="chip">
                    {skill}
                  </span>
                ))}
              </div>
              <Link to={`/jobs/${job.id}`} className="btn-ghost mt-3 w-full text-xs">
                Ver detalle de la vacante
              </Link>
            </div>

            <div className="rounded-2xl border border-dashed border-line p-4 text-[11px] leading-relaxed text-muted">
              <p className="flex items-center gap-1.5 font-semibold text-slate-300">
                <Sparkles className="h-3.5 w-3.5 text-primary" /> Human-in-the-loop
              </p>
              <p className="mt-2">
                JobRadar prepara el material y el asistente puede rellenar el formulario. Tú decides qué compartir y confirmas el envío.
              </p>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
