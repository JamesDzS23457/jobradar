import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Hand,
  Loader2,
  LogIn,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Star,
  Wand2,
  Zap,
} from "lucide-react";
import { Link } from "react-router-dom";
import type { Job } from "@/lib/types";
import { cn, scoreLabel, scoreStroke } from "@/lib/utils";
import { ScoreRing } from "./ScoreRing";

const labels: Record<string, string> = {
  skills: "Skills",
  title: "Rol",
  seniority: "Seniority",
  location: "Ubicación",
  language: "Idioma",
  salary: "Salario",
  freshness: "Frescura",
};

type Props = {
  job: Job;
  onApply?: () => void;
  onSave?: () => void;
  applying?: boolean;
  saving?: boolean;
  saved?: boolean;
  applied?: boolean;
};

export function MatchPanel({ job, onApply, onSave, applying, saving, saved, applied }: Props) {
  const match = job.match;
  if (!match) {
    return (
      <div className="card p-5">
        <p className="text-sm text-muted">Todavía no hay un match calculado para esta vacante.</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="border-b border-line/70 bg-gradient-to-br from-primary/[0.07] to-transparent p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Compatibilidad</p>
            <div className="mt-2 flex items-end gap-3">
              <span className="font-display text-4xl font-semibold" style={{ color: scoreStroke(match.score) }}>
                {Math.round(match.score)}%
              </span>
              <span className="pb-1 text-sm font-medium text-slate-300">{scoreLabel(match.score)}</span>
            </div>
            <p className="mt-1 text-xs text-muted">{match.recommendation}</p>
          </div>
          <ScoreRing score={match.score} size={78} stroke={5} />
        </div>
        {!match.eligible && (
          <div className="mt-4 flex items-start gap-2 rounded-xl border border-rose-400/20 bg-rose-400/10 p-3 text-xs text-rose-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            {match.reasons[0]}
          </div>
        )}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider",
              job.portal.mode === "auto_submit"
                ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-300"
                : job.portal.mode === "assisted"
                  ? "border-cyan-400/20 bg-cyan-400/10 text-cyan-300"
                  : "border-amber-400/20 bg-amber-400/10 text-amber-300",
            )}
          >
            {job.portal.mode === "auto_submit" ? (
              <Zap className="h-3 w-3" />
            ) : job.portal.mode === "assisted" ? (
              <ShieldCheck className="h-3 w-3" />
            ) : (
              <Hand className="h-3 w-3" />
            )}
            {job.portal.mode === "auto_submit"
              ? "Auto-envío disponible"
              : job.portal.mode === "assisted"
                ? "Asistido + revisión"
                : "Solo portal original"}
          </span>
          <span className="text-[10px] leading-relaxed text-slate-500">{job.portal.reason}</span>
        </div>
        {(job.link_only || job.requires_login) && (
          <div className="mt-3 flex items-start gap-2 rounded-xl border border-amber-400/20 bg-amber-400/[0.05] p-3 text-[10px] leading-relaxed text-amber-100/75">
            <LogIn className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" />
            <span>
              <strong className="font-semibold text-amber-200">Requiere iniciar sesión.</strong>{" "}
              {job.access_note || "Abre el enlace original para ver la vacante y postularte."}
            </span>
          </div>
        )}
      </div>

      <div className="space-y-5 p-5">
        <div>
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">Desglose del score</p>
          <div className="space-y-2.5">
            {Object.entries(match.subscores).map(([key, value]) => (
              <div key={key} className="flex items-center gap-3">
                <span className="w-16 shrink-0 text-[11px] text-slate-400">{labels[key] ?? key}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.05]">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${Math.max(2, value)}%`, backgroundColor: scoreStroke(value) }}
                  />
                </div>
                <span className="w-8 text-right text-[10px] tabular-nums text-slate-500">{Math.round(value)}</span>
              </div>
            ))}
          </div>
        </div>

        {match.reasons.length > 0 && (
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-emerald-300/80">Por qué encajas</p>
            <ul className="space-y-2">
              {match.reasons.map((reason) => (
                <li key={reason} className="flex items-start gap-2 text-xs leading-relaxed text-slate-300">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {match.gaps.length > 0 && (
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-amber-300/80">Brechas a revisar</p>
            <ul className="space-y-2">
              {match.gaps.map((gap) => (
                <li key={gap} className="flex items-start gap-2 text-xs leading-relaxed text-slate-400">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
                  {gap}
                </li>
              ))}
            </ul>
          </div>
        )}

        {match.red_flags.length > 0 && (
          <div className="rounded-xl border border-rose-400/20 bg-rose-400/[0.06] p-3">
            <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-rose-300">
              <ShieldAlert className="h-3.5 w-3.5" /> Señales de alerta
            </p>
            <ul className="space-y-1.5">
              {match.red_flags.map((flag) => (
                <li key={flag} className="text-xs leading-relaxed text-rose-200/80">
                  {flag}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="space-y-2 border-t border-line/70 pt-4">
          {job.portal.can_assist ? (
            <Link to={`/jobs/${job.id}/apply`} className={cn("btn-primary w-full", !match.eligible && "opacity-70")}>
              <Wand2 className="h-4 w-4" /> Preparar postulación
            </Link>
          ) : (
            job.url && (
              <a href={job.url} target="_blank" rel="noreferrer" className="btn-primary w-full">
                <ExternalLink className="h-4 w-4" /> Abrir portal original
              </a>
            )
          )}
          {job.url && job.portal.can_assist && (
            <a href={job.url} target="_blank" rel="noreferrer" className="btn-secondary w-full">
              <ExternalLink className="h-4 w-4" /> Abrir portal sin asistente
            </a>
          )}
          <Link to={`/jobs/${job.id}/tailor`} className="btn-secondary w-full">
            <Sparkles className="h-4 w-4" /> Adaptar mi CV
          </Link>
          <div className="grid grid-cols-2 gap-2">
            {applied ? (
              <Link to="/tracker" className="btn-secondary col-span-2 w-full">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" /> Ya está en tu tracker
              </Link>
            ) : (
              <>
                <button type="button" onClick={onSave} disabled={saving} className="btn-secondary w-full">
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Star className={cn("h-4 w-4", saved && "fill-current text-primary")} />}
                  {saved ? "Guardada" : "Guardar"}
                </button>
                <button type="button" onClick={onApply} disabled={applying} className="btn-secondary w-full">
                  {applying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  Ya postulé
                </button>
              </>
            )}
          </div>
          {job.url && (
            <p className="text-center text-[10px] leading-relaxed text-slate-600">
              {job.portal.mode === "manual_only"
                ? "Este portal exige que completes la postulación directamente. No hay autocompletado."
                : "La IA prepara los datos; tú revisas y confirmas antes de enviar."}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
