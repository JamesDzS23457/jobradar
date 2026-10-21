import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarClock,
  CheckCircle2,
  Radar,
  Send,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "@/components/EmptyState";
import { JobCard } from "@/components/JobCard";
import { PageHeader } from "@/components/PageHeader";
import { ScoreDistribution } from "@/components/ScoreDistribution";
import { SearchButton } from "@/components/SearchButton";
import { StatCard } from "@/components/StatCard";
import { api } from "@/lib/api";
import type { Application } from "@/lib/types";
import { cn, collectorLabel, formatDate, timeAgo } from "@/lib/utils";

const statusStyles: Record<Application["status"], string> = {
  saved: "bg-slate-400/10 text-slate-300 ring-slate-400/20",
  applied: "bg-cyan-400/10 text-cyan-300 ring-cyan-400/20",
  interview: "bg-amber-400/10 text-amber-300 ring-amber-400/20",
  offer: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20",
  rejected: "bg-rose-400/10 text-rose-300 ring-rose-400/20",
};

const statusLabels: Record<Application["status"], string> = {
  saved: "Guardada",
  applied: "Postulada",
  interview: "Entrevista",
  offer: "Oferta",
  rejected: "Rechazada",
};

function LoadingDashboard() {
  return (
    <div className="space-y-6">
      <div className="h-10 w-72 animate-pulse rounded-lg bg-white/[0.04]" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="card h-32 animate-pulse bg-white/[0.02]" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="card h-96 animate-pulse bg-white/[0.02] xl:col-span-2" />
        <div className="card h-96 animate-pulse bg-white/[0.02]" />
      </div>
    </div>
  );
}

export function DashboardPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard,
  });

  if (isLoading) return <LoadingDashboard />;
  if (isError || !data) {
    return (
      <EmptyState
        icon={Radar}
        title="No pudimos cargar tu radar"
        description={error instanceof Error ? error.message : "Revisa que el backend esté corriendo en el puerto 8000."}
        action={
          <button type="button" onClick={() => refetch()} className="btn-primary">
            Reintentar
          </button>
        }
      />
    );
  }

  const firstName = data.profile_name?.split(" ")[0] || "bienvenido";

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Tu radar laboral"
        title={`Hola, ${firstName}`}
        description={
          data.profile_complete
            ? `Estas son las oportunidades que mejor encajan con tu perfil en ${data.home_city}. La ubicación y la modalidad ya están filtradas.`
            : "Sube tu CV para empezar a recibir recomendaciones personalizadas."
        }
        actions={<SearchButton />}
      />

      <section className="card relative mb-6 overflow-hidden p-5 sm:p-6">
        <div className="pointer-events-none absolute -right-16 -top-20 h-56 w-56 rounded-full border border-primary/10" />
        <div className="pointer-events-none absolute -right-8 -top-12 h-36 w-36 rounded-full border border-primary/10" />
        <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20">
              <Target className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">
                {data.stats.excellent + data.stats.good} oportunidades con buen match
              </p>
              <p className="mt-1 text-xs leading-relaxed text-muted">
                {data.stats.excellent} excelentes (85%+) y {data.stats.good} buenas (70–84%). Tú decides dónde postular.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-5 text-xs text-muted">
            <div>
              <p className="font-display text-lg font-semibold text-white">{data.stats.average_score}%</p>
              <p>match promedio</p>
            </div>
            <div className="h-8 w-px bg-line" />
            <div>
              <p className="font-display text-lg font-semibold text-white">{data.stats.eligible_jobs}</p>
              <p>ofertas elegibles</p>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Ofertas elegibles"
          value={data.stats.eligible_jobs}
          hint={`${data.stats.potential_jobs} potenciales · ${data.stats.total_jobs} revisadas`}
          icon={BriefcaseBusiness}
        />
        <StatCard
          label="Matches excelentes"
          value={data.stats.excellent}
          hint="score de 85% o más"
          icon={Sparkles}
          tone="cyan"
        />
        <StatCard label="Postuladas" value={data.stats.applied} hint="en seguimiento activo" icon={Send} tone="amber" />
        <StatCard label="Entrevistas" value={data.stats.interviews} hint="conversaciones en curso" icon={TrendingUp} tone="rose" />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="section-title">Mejores coincidencias</h2>
              <p className="mt-1 text-xs text-muted">Ordenadas por compatibilidad con tu perfil.</p>
            </div>
            <Link to="/jobs" className="flex items-center gap-1 text-xs font-semibold text-primary hover:text-emerald-200">
              Ver todas <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {data.top_matches.length > 0 ? (
            <div className="space-y-3">
              {data.top_matches.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={BriefcaseBusiness}
              title="Aún no hay coincidencias"
              description="Ejecuta una búsqueda o sube tu CV para que el radar empiece a encontrar oportunidades."
              action={<SearchButton label="Ejecutar búsqueda" />}
            />
          )}
        </div>

        <div className="space-y-6">
          <section className="card p-5">
            <div className="flex items-center justify-between">
              <h2 className="section-title">Estado de búsqueda</h2>
              <CalendarClock className="h-4 w-4 text-muted" />
            </div>
            {data.last_run ? (
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted">Última ejecución</span>
                  <span className="font-medium text-slate-200">{timeAgo(data.last_run.finished_at || data.last_run.started_at)}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted">Ofertas revisadas</span>
                  <span className="font-medium text-slate-200">{data.last_run.found}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted">Nuevas</span>
                  <span className="font-medium text-emerald-300">{data.last_run.new}</span>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {Object.entries(data.last_run.sources).map(([source, count]) => (
                    <span key={source} className="chip">
                      {collectorLabel(source)} · {count}
                    </span>
                  ))}
                </div>
                {data.last_run.errors.length > 0 && (
                  <div className="rounded-lg bg-rose-400/10 p-2.5 text-[11px] text-rose-200">
                    <p className="font-semibold">
                      {data.last_run.errors.length} fuente(s) con error
                    </p>
                    <ul className="mt-1 space-y-1">
                      {data.last_run.errors.map((error, index) => (
                        <li key={`${index}-${error.slice(0, 20)}`} className="break-words leading-relaxed text-rose-100/80">
                          {error}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="mt-4">
                <p className="text-xs leading-relaxed text-muted">
                  Todavía no has ejecutado una búsqueda. El scheduler puede hacerlo cada 6 horas, o puedes lanzarla ahora.
                </p>
                <SearchButton className="mt-3 w-full" label="Primera búsqueda" />
              </div>
            )}
          </section>

          <section className="card p-5">
            <div className="flex items-center justify-between">
              <h2 className="section-title">Distribución de matches</h2>
              <CheckCircle2 className="h-4 w-4 text-muted" />
            </div>
            <p className="mt-1 text-xs text-muted">Cómo se reparten las ofertas elegibles.</p>
            <div className="mt-4">
              <ScoreDistribution data={data.distribution} />
            </div>
          </section>

          <section className="card p-5">
            <div className="flex items-center justify-between">
              <h2 className="section-title">Seguimiento</h2>
              <Link to="/tracker" className="text-[11px] font-semibold text-primary hover:text-emerald-200">
                Ver tracker
              </Link>
            </div>
            {data.recent_applications.length > 0 ? (
              <div className="mt-4 space-y-3">
                {data.recent_applications.map((application) => (
                  <Link
                    key={application.id}
                    to={`/jobs/${application.job_id}`}
                    className="flex items-center justify-between gap-3 rounded-xl border border-line/60 bg-white/[0.02] p-3 transition hover:border-primary/20 hover:bg-white/[0.04]"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-xs font-medium text-slate-200">{application.job?.title}</p>
                      <p className="truncate text-[11px] text-muted">{application.job?.company}</p>
                    </div>
                    <span className={cn("shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold ring-1", statusStyles[application.status])}>
                      {statusLabels[application.status]}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-xs leading-relaxed text-muted">
                Cuando marques una oferta como postulada, aparecerá aquí con su estado y próximos pasos.
              </p>
            )}
          </section>

          <div className="rounded-2xl border border-dashed border-line p-4 text-[11px] leading-relaxed text-muted">
            <p className="flex items-center gap-1.5 font-semibold text-slate-300">
              <Radar className="h-3.5 w-3.5 text-primary" /> Cómo funciona el score
            </p>
            <p className="mt-2">
              Skills (40%), rol (20%), seniority (15%), ubicación (10%), idioma (5%), salario (5%) y frescura (5%).
              Las ofertas presenciales fuera de Colombia se excluyen automáticamente.
            </p>
          </div>
        </div>
      </div>

      <p className="mt-6 text-center text-[10px] text-slate-600">Última actualización: {formatDate(new Date().toISOString())}</p>
    </div>
  );
}
