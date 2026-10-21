import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, BriefcaseBusiness, CalendarClock, KanbanSquare, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { Application } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

const columns: { id: Application["status"]; label: string; accent: string; dot: string }[] = [
  { id: "saved", label: "Guardadas", accent: "text-slate-300", dot: "bg-slate-400" },
  { id: "applied", label: "Postuladas", accent: "text-cyan-300", dot: "bg-cyan-400" },
  { id: "interview", label: "Entrevistas", accent: "text-amber-300", dot: "bg-amber-400" },
  { id: "offer", label: "Ofertas", accent: "text-emerald-300", dot: "bg-emerald-400" },
  { id: "rejected", label: "Rechazadas", accent: "text-rose-300", dot: "bg-rose-400" },
];

const statusLabels: Record<Application["status"], string> = {
  saved: "Guardada",
  applied: "Postulada",
  interview: "Entrevista",
  offer: "Oferta",
  rejected: "Rechazada",
};

export function TrackerPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["applications"],
    queryFn: api.applications,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: Application["status"] }) =>
      api.updateApplication(id, { status }),
    onSuccess: () => {
      toast.success("Estado actualizado.");
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  const applications = data?.items ?? [];
  const counts = {
    total: applications.length,
    interviews: applications.filter((application) => application.status === "interview").length,
    offers: applications.filter((application) => application.status === "offer").length,
  };

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Seguimiento"
        title="Tu pipeline de postulaciones"
        description="Mueve cada oportunidad a medida que avanza. Tú controlas el proceso; el auto-envío es opcional y solo para portales permitidos."
        actions={
          <Link to="/jobs" className="btn-secondary">
            <BriefcaseBusiness className="h-4 w-4" /> Buscar vacantes
          </Link>
        }
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">En pipeline</p>
          <p className="mt-1 font-display text-2xl font-semibold text-white">{counts.total}</p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Entrevistas</p>
          <p className="mt-1 font-display text-2xl font-semibold text-amber-300">{counts.interviews}</p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Ofertas</p>
          <p className="mt-1 font-display text-2xl font-semibold text-emerald-300">{counts.offers}</p>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 xl:grid-cols-5">
          {columns.map((column) => (
            <div key={column.id} className="card h-72 animate-pulse bg-white/[0.02]" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={KanbanSquare}
          title="No pudimos cargar el seguimiento"
          description={error instanceof Error ? error.message : "Revisa la conexión con el backend."}
          action={
            <button type="button" onClick={() => refetch()} className="btn-primary">
              Reintentar
            </button>
          }
        />
      ) : applications.length === 0 ? (
        <EmptyState
          icon={KanbanSquare}
          title="Tu pipeline está vacío"
          description="Guarda una vacante o márcala como postulada para empezar a seguir el proceso."
          action={
            <Link to="/jobs" className="btn-primary">
              Explorar vacantes <ArrowRight className="h-4 w-4" />
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {columns.map((column) => {
            const items = applications.filter((application) => application.status === column.id);
            return (
              <section key={column.id} className="flex min-h-[280px] flex-col rounded-2xl border border-line/70 bg-surface/40 p-3">
                <header className="mb-3 flex items-center justify-between px-1">
                  <div className="flex items-center gap-2">
                    <span className={cn("h-2 w-2 rounded-full", column.dot)} />
                    <h2 className={cn("text-xs font-semibold", column.accent)}>{column.label}</h2>
                  </div>
                  <span className="rounded-full bg-white/[0.04] px-2 py-0.5 text-[10px] text-muted">{items.length}</span>
                </header>

                <div className="space-y-2.5">
                  {items.map((application) => (
                    <article key={application.id} className="rounded-xl border border-line/70 bg-ink/60 p-3 transition hover:border-primary/20">
                      <Link to={`/jobs/${application.job_id}`} className="block">
                        <p className="line-clamp-2 text-xs font-semibold leading-snug text-slate-200 hover:text-primary">
                          {application.job?.title ?? "Vacante"}
                        </p>
                        <p className="mt-1 truncate text-[11px] text-muted">{application.job?.company ?? "—"}</p>
                      </Link>

                      <div className="mt-2 flex items-center justify-between gap-2 text-[10px] text-slate-500">
                        <span className="flex items-center gap-1">
                          <CalendarClock className="h-3 w-3" />
                          {formatDate(application.applied_at || application.updated_at)}
                        </span>
                        {application.job?.match && (
                          <span
                            className={cn(
                              "font-semibold",
                              application.job.match.score >= 85
                                ? "text-emerald-300"
                                : application.job.match.score >= 70
                                  ? "text-cyan-300"
                                  : "text-amber-300",
                            )}
                          >
                            {Math.round(application.job.match.score)}%
                          </span>
                        )}
                      </div>

                      <div className="relative mt-3">
                        <select
                          value={application.status}
                          onChange={(event) =>
                            updateMutation.mutate({
                              id: application.id,
                              status: event.target.value as Application["status"],
                            })
                          }
                          className="w-full appearance-none rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[10px] font-medium text-slate-300 outline-none hover:border-primary/30"
                        >
                          {columns.map((option) => (
                            <option key={option.id} value={option.id} className="bg-surface">
                              {statusLabels[option.id]}
                            </option>
                          ))}
                        </select>
                        {updateMutation.isPending && updateMutation.variables?.id === application.id && (
                          <Loader2 className="absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 animate-spin text-primary" />
                        )}
                      </div>
                    </article>
                  ))}

                  {items.length === 0 && (
                    <div className="rounded-xl border border-dashed border-line/70 px-3 py-6 text-center text-[10px] text-slate-600">
                      Sin postulaciones
                    </div>
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
