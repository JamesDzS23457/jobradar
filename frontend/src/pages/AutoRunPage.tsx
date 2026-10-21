import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  ExternalLink,
  Hand,
  Loader2,
  RefreshCw,
  Send,
  TriangleAlert,
  WandSparkles,
  Zap,
} from "lucide-react";
import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { EmptyState } from "@/components/EmptyState";
import { api } from "@/lib/api";
import type { ApplicationRunItem } from "@/lib/types";
import { cn, timeAgo } from "@/lib/utils";

const statusStyles: Record<ApplicationRunItem["status"], string> = {
  queued: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
  processing: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
  submitted: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
  manual: "border-amber-400/20 bg-amber-400/10 text-amber-300",
  failed: "border-rose-400/20 bg-rose-400/10 text-rose-300",
  skipped: "border-line bg-white/[0.03] text-slate-400",
};

const statusLabels: Record<ApplicationRunItem["status"], string> = {
  queued: "En cola para la extensión",
  processing: "Procesando",
  submitted: "Enviada",
  manual: "Requiere tu intervención",
  failed: "Falló",
  skipped: "Omitida",
};

function sessionUrl(url: string, sessionId: number) {
  try {
    const parsed = new URL(url);
    parsed.hash = `jobradar-session=${sessionId}`;
    return parsed.toString();
  } catch {
    return `${url}#jobradar-session=${sessionId}`;
  }
}

function ItemCard({ item }: { item: ApplicationRunItem }) {
  const job = item.job;
  if (!job) return null;
  return (
    <article className="card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-display text-sm font-semibold text-white">{job.title}</p>
          <p className="mt-0.5 truncate text-xs text-muted">
            {job.company} · {job.location_text}
          </p>
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider",
            statusStyles[item.status],
          )}
        >
          {statusLabels[item.status]}
        </span>
      </div>

      <p className="mt-3 line-clamp-3 text-[11px] leading-relaxed text-slate-400">
        {job.description || "Sin descripción disponible."}
      </p>
      {item.message && <p className="mt-2 text-[10px] leading-relaxed text-slate-500">{item.message}</p>}

      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line/60 pt-3">
        <span className="text-[10px] text-slate-600">{timeAgo(job.posted_at)}</span>
        <Link to={`/jobs/${job.id}`} className="btn-ghost px-2 py-1 text-[10px]">
          Ver detalle
        </Link>
        {job.url && (
          <a href={job.url} target="_blank" rel="noreferrer" className="btn-ghost px-2 py-1 text-[10px]">
            <ExternalLink className="h-3 w-3" /> Portal original
          </a>
        )}
        {item.session_id && job.url && (
          <a
            href={sessionUrl(job.url, item.session_id)}
            target="_blank"
            rel="noreferrer"
            className="btn-ghost px-2 py-1 text-[10px]"
          >
            <WandSparkles className="h-3 w-3" /> Abrir asistente
          </a>
        )}
      </div>
    </article>
  );
}

export function AutoRunPage() {
  const { id } = useParams();
  const runId = Number(id);

  useEffect(() => {
    if (Number.isFinite(runId)) {
      window.postMessage({ source: "jobradar-web", type: "START_AUTO_RUN", runId }, "*");
    }
  }, [runId]);

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["application-run", runId],
    queryFn: () => api.applicationRun(runId),
    enabled: Number.isFinite(runId),
    refetchInterval: (query) => (query.state.data?.run.status === "running" ? 2500 : false),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded bg-white/[0.04]" />
        <div className="grid gap-4 sm:grid-cols-4">
          {[0, 1, 2, 3].map((item) => (
            <div key={item} className="card h-24 animate-pulse bg-white/[0.02]" />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <EmptyState
        icon={WandSparkles}
        title="No encontramos esta ronda"
        description={error instanceof Error ? error.message : "Vuelve a vacantes e inicia otra ronda."}
        action={
          <Link to="/jobs" className="btn-primary">
            Volver a vacantes
          </Link>
        }
      />
    );
  }

  const run = data.run;
  const pending = run.items.filter((item) => item.status === "queued" || item.status === "processing").length;
  const actionable = run.items.filter((item) => item.status !== "submitted");

  return (
    <div className="animate-fade-up">
      <Link
        to="/jobs"
        className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-muted transition hover:text-white"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Volver a vacantes
      </Link>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-primary">Auto-envío</p>
          <h1 className="mt-2 font-display text-2xl font-semibold text-white">Ronda #{run.id}</h1>
          <p className="mt-1 text-sm text-muted">
            {run.status === "completed"
              ? "La ronda terminó. Revisa los resultados y las vacantes que requieren tu intervención."
              : "La extensión procesa la cola en orden. Puedes dejar esta página abierta para ver el progreso."}
          </p>
        </div>
        <button type="button" onClick={() => refetch()} disabled={isFetching} className="btn-secondary">
          {isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Actualizar
        </button>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">Total</p>
          <p className="mt-1 font-display text-2xl font-semibold text-white">{run.total}</p>
        </div>
        <div className="card p-4">
          <p className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-300">
            <CheckCircle2 className="h-3.5 w-3.5" /> Enviadas
          </p>
          <p className="mt-1 font-display text-2xl font-semibold text-emerald-300">{run.submitted}</p>
        </div>
        <div className="card p-4">
          <p className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-amber-300">
            <Hand className="h-3.5 w-3.5" /> Manuales
          </p>
          <p className="mt-1 font-display text-2xl font-semibold text-amber-300">{run.manual}</p>
        </div>
        <div className="card p-4">
          <p className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-rose-300">
            <TriangleAlert className="h-3.5 w-3.5" /> Fallidas
          </p>
          <p className="mt-1 font-display text-2xl font-semibold text-rose-300">{run.failed}</p>
        </div>
      </div>

      {pending > 0 && (
        <div className="mt-5 flex items-start gap-3 rounded-2xl border border-cyan-400/20 bg-cyan-400/[0.05] p-4">
          <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" />
          <div>
            <p className="text-xs font-semibold text-cyan-200">
              {pending} vacante{pending === 1 ? "" : "s"} esperando a la extensión de Chrome
            </p>
            <p className="mt-1 text-[11px] leading-relaxed text-cyan-100/60">
              Instala la extensión desde <code className="rounded bg-white/[0.06] px-1">extension/</code> y déjala
              activa. Si el portal pide CAPTCHA, login o un paso manual, la extensión marcará la vacante como manual
              en lugar de intentar evadirlo.
            </p>
          </div>
        </div>
      )}

      {run.status === "running" && pending === 0 && (
        <div className="mt-5 flex items-center gap-2 rounded-2xl border border-line/60 bg-white/[0.02] p-4 text-xs text-muted">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          Esperando el reporte final de la extensión...
        </div>
      )}

      <div className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="section-title">Resultados</h2>
          <span className="text-[11px] text-slate-600">{actionable.length} por revisar</span>
        </div>

        {run.items.length === 0 ? (
          <EmptyState
            icon={Zap}
            title="No hay vacantes elegibles en esta ronda"
            description="No encontramos vacantes elegibles dentro del filtro de frescura. Amplía el filtro o ejecuta una nueva búsqueda."
            action={
              <Link to="/jobs" className="btn-primary">
                <Send className="h-4 w-4" /> Ver vacantes
              </Link>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {run.items.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
