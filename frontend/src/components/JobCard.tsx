import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Banknote, Globe2, LogIn, MapPin, Star } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";
import { cn, collectorLabel, formatSalary, initials, remoteLabel, scoreLabel, timeAgo } from "@/lib/utils";
import { ScoreRing } from "./ScoreRing";

const avatarStyles = [
  "from-emerald-400/25 to-cyan-400/10 text-emerald-200",
  "from-cyan-400/25 to-blue-500/10 text-cyan-200",
  "from-violet-400/25 to-fuchsia-500/10 text-violet-200",
  "from-amber-400/25 to-orange-500/10 text-amber-200",
  "from-rose-400/25 to-pink-500/10 text-rose-200",
];

type Props = {
  job: Job;
  compact?: boolean;
};

export function JobCard({ job, compact = false }: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const score = job.match?.score ?? 0;
  const saved = job.status === "saved";
  const avatar = avatarStyles[job.company.length % avatarStyles.length];

  const saveMutation = useMutation({
    mutationFn: () => api.updateJob(job.id, saved ? "new" : "saved"),
    onSuccess: () => {
      toast.success(saved ? "Oferta quitada de guardadas." : "Oferta guardada.");
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["job", job.id] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <article
      role="link"
      tabIndex={0}
      onClick={() => navigate(`/jobs/${job.id}`)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") navigate(`/jobs/${job.id}`);
      }}
      className={cn(
        "card card-hover group cursor-pointer p-5 outline-none focus-visible:ring-2 focus-visible:ring-primary/50",
        compact && "p-4",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 gap-3">
          <div
            className={cn(
              "flex shrink-0 items-center justify-center rounded-xl bg-gradient-to-br font-display font-semibold ring-1 ring-white/10",
              avatar,
              compact ? "h-10 w-10 text-xs" : "h-11 w-11 text-sm",
            )}
          >
            {initials(job.company)}
          </div>
          <div className="min-w-0">
            <h3 className={cn("font-display font-semibold leading-snug text-white group-hover:text-primary", compact ? "text-sm" : "text-base")}>
              {job.title}
            </h3>
            <p className="mt-0.5 truncate text-xs text-muted">
              {job.company} {job.seniority ? <span className="text-slate-600">·</span> : null} {job.seniority}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {(job.status === "new" || job.status === "saved") && (
            <button
              type="button"
              aria-label={saved ? "Quitar de guardadas" : "Guardar oferta"}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                saveMutation.mutate();
              }}
              className={cn(
                "rounded-lg p-1.5 transition hover:bg-white/5",
                saved ? "text-amber-300" : "text-slate-500 hover:text-slate-200",
              )}
            >
              <Star className={cn("h-4 w-4", saved && "fill-current")} />
            </button>
          )}
          {job.match ? <ScoreRing score={score} size={compact ? 52 : 58} stroke={4} /> : null}
        </div>
      </div>

      {job.match && !job.match.eligible && (
        <div className="mt-3 inline-flex rounded-full border border-rose-400/20 bg-rose-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-rose-300">
          {job.match.recommendation}
        </div>
      )}

      {(job.link_only || job.requires_login) && (
        <div className="mt-3 flex items-start gap-2 rounded-xl border border-amber-400/20 bg-amber-400/[0.06] px-3 py-2 text-[10px] leading-relaxed text-amber-100/80">
          <LogIn className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" />
          <span>
            <strong className="font-semibold text-amber-200">Requiere iniciar sesión.</strong>{" "}
            {job.access_note || "Abre el enlace original para ver la vacante y postularte."}
          </span>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="chip">
          <MapPin className="h-3 w-3" />
          {job.location_text || "Remoto"}
        </span>
        <span className="chip">{remoteLabel(job.remote_type)}</span>
        <span className="chip border-cyan-400/15 bg-cyan-400/[0.05] text-cyan-200">
          <Globe2 className="h-3 w-3" /> {job.portal.label}
        </span>
        <span className="chip">{collectorLabel(job.collector || job.source)}</span>
        {!compact && (
          <span className="chip">
            <Banknote className="h-3 w-3" />
            {formatSalary(job)}
          </span>
        )}
      </div>

      {!compact && job.skills_required.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {job.skills_required.slice(0, 4).map((skill) => (
            <span key={skill} className="rounded-md bg-white/[0.04] px-2 py-1 text-[10px] font-medium text-slate-400">
              {skill}
            </span>
          ))}
          {job.skills_required.length > 4 && (
            <span className="rounded-md bg-white/[0.04] px-2 py-1 text-[10px] font-medium text-slate-500">
              +{job.skills_required.length - 4}
            </span>
          )}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-line/60 pt-3">
        <div className="flex items-center gap-2 text-[11px] text-muted">
          <span>{timeAgo(job.posted_at)}</span>
          {job.match && (
            <>
              <span className="h-1 w-1 rounded-full bg-slate-600" />
              <span className={cn("font-medium", job.match.score >= 85 ? "text-emerald-300" : "text-slate-400")}>
                {scoreLabel(job.match.score)}
              </span>
            </>
          )}
        </div>
        <span className="flex items-center gap-1 text-[11px] font-semibold text-primary opacity-0 transition group-hover:opacity-100">
          Ver detalle <ArrowUpRight className="h-3 w-3" />
        </span>
      </div>
    </article>
  );
}
