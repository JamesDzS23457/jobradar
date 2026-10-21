import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Banknote, BriefcaseBusiness, CalendarDays, ExternalLink, MapPin, Sparkles } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { MatchPanel } from "@/components/MatchPanel";
import { ScoreRing } from "@/components/ScoreRing";
import { api } from "@/lib/api";
import { formatDate, formatSalary, initials, remoteLabel } from "@/lib/utils";

export function JobDetailPage() {
  const { id } = useParams();
  const jobId = Number(id);
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.job(jobId),
    enabled: Number.isFinite(jobId),
  });

  const saveMutation = useMutation({
    mutationFn: (status: "saved" | "new") => api.updateJob(jobId, status),
    onSuccess: () => {
      toast.success("Estado de la oferta actualizado.");
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  const applyMutation = useMutation({
    mutationFn: () => api.createApplication({ job_id: jobId, status: "applied" }),
    onSuccess: () => {
      toast.success("Postulación registrada en el tracker.");
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-24 animate-pulse rounded bg-white/[0.04]" />
        <div className="grid gap-6 xl:grid-cols-3">
          <div className="card h-[520px] animate-pulse bg-white/[0.02] xl:col-span-2" />
          <div className="card h-[520px] animate-pulse bg-white/[0.02]" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <EmptyState
        icon={BriefcaseBusiness}
        title="No encontramos esta vacante"
        description={error instanceof Error ? error.message : "Puede que haya sido eliminada del radar."}
        action={
          <Link to="/jobs" className="btn-primary">
            Volver a vacantes
          </Link>
        }
      />
    );
  }

  const job = data.job;
  const saved = job.status === "saved";

  return (
    <div className="animate-fade-up">
      <Link to="/jobs" className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-muted transition hover:text-white">
        <ArrowLeft className="h-3.5 w-3.5" /> Volver a vacantes
      </Link>

      <div className="card mb-6 p-5 sm:p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400/25 to-cyan-400/10 font-display text-lg font-semibold text-emerald-200 ring-1 ring-white/10">
              {initials(job.company)}
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="font-display text-xl font-semibold leading-tight text-white sm:text-2xl">{job.title}</h1>
                {job.match && (
                  <span className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-primary">
                    {job.match.recommendation}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-muted">
                {job.company} <span className="text-slate-600">·</span> {job.location_text}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="chip">
                  <MapPin className="h-3 w-3" /> {job.location_text || "Remoto"}
                </span>
                <span className="chip">{remoteLabel(job.remote_type)}</span>
                <span className="chip">
                  <Banknote className="h-3 w-3" /> {formatSalary(job)}
                </span>
                <span className="chip">
                  <CalendarDays className="h-3 w-3" /> {formatDate(job.posted_at)}
                </span>
              </div>
            </div>
          </div>
          {job.match && <ScoreRing score={job.match.score} size={92} stroke={6} />}
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <section className="card p-5 sm:p-6">
            <h2 className="section-title">Descripción de la vacante</h2>
            <div className="mt-4 space-y-4 text-sm leading-7 text-slate-300">
              {(job.description || "Sin descripción disponible.").split("\n").filter(Boolean).map((paragraph, index) => (
                <p key={index}>{paragraph}</p>
              ))}
            </div>
          </section>

          <section className="card p-5 sm:p-6">
            <h2 className="section-title">Requisitos y tecnologías</h2>
            <div className="mt-4 grid gap-5 sm:grid-cols-2">
              <div>
                <p className="label">Requisitos</p>
                <div className="flex flex-wrap gap-1.5">
                  {job.skills_required.length > 0 ? (
                    job.skills_required.map((skill) => (
                      <span key={skill} className="rounded-lg border border-primary/15 bg-primary/[0.06] px-2.5 py-1.5 text-xs text-emerald-200">
                        {skill}
                      </span>
                    ))
                  ) : (
                    <p className="text-xs text-muted">No especificados.</p>
                  )}
                </div>
              </div>
              <div>
                <p className="label">Deseables</p>
                <div className="flex flex-wrap gap-1.5">
                  {job.skills_nice.length > 0 ? (
                    job.skills_nice.map((skill) => (
                      <span key={skill} className="rounded-lg border border-line bg-white/[0.03] px-2.5 py-1.5 text-xs text-slate-300">
                        {skill}
                      </span>
                    ))
                  ) : (
                    <p className="text-xs text-muted">No especificados.</p>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-5 grid gap-3 border-t border-line/60 pt-5 sm:grid-cols-3">
              <div>
                <p className="label">Seniority</p>
                <p className="text-sm capitalize text-slate-200">{job.seniority}</p>
              </div>
              <div>
                <p className="label">Experiencia</p>
                <p className="text-sm text-slate-200">{job.years_experience ? `${job.years_experience}+ años` : "No especificada"}</p>
              </div>
              <div>
                <p className="label">Idiomas</p>
                <p className="text-sm text-slate-200">
                  {Object.entries(job.languages).length > 0
                    ? Object.entries(job.languages).map(([language, level]) => `${language} ${level}`).join(" · ")
                    : "No especificados"}
                </p>
              </div>
            </div>
          </section>

          <div className="flex flex-wrap gap-2">
            <Link to={`/jobs/${job.id}/tailor`} className="btn-primary">
              <Sparkles className="h-4 w-4" /> Adaptar CV a esta vacante
            </Link>
            {job.url && (
              <a href={job.url} target="_blank" rel="noreferrer" className="btn-secondary">
                <ExternalLink className="h-4 w-4" /> Ver oferta original
              </a>
            )}
          </div>
        </div>

        <div className="xl:sticky xl:top-6 xl:self-start">
          <MatchPanel
            job={job}
            applying={applyMutation.isPending}
            saving={saveMutation.isPending}
            saved={saved}
            applied={job.status === "applied"}
            onApply={() => applyMutation.mutate()}
            onSave={() => saveMutation.mutate(saved ? "new" : "saved")}
          />
        </div>
      </div>
    </div>
  );
}
