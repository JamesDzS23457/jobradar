import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArchiveRestore,
  BriefcaseBusiness,
  Clock3,
  Filter,
  Link2,
  Loader2,
  Search,
  SlidersHorizontal,
  Sparkles,
  WandSparkles,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { JobCard } from "@/components/JobCard";
import { PageHeader } from "@/components/PageHeader";
import { SearchButton } from "@/components/SearchButton";
import { Toggle } from "@/components/Toggle";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export function JobsPage() {
  const [q, setQ] = useState("");
  const [remoteType, setRemoteType] = useState("all");
  const [minScore, setMinScore] = useState(0);
  const [includeIneligible, setIncludeIneligible] = useState(false);
  const [maxAgeDays, setMaxAgeDays] = useState(2);
  const [includeUnknownDate, setIncludeUnknownDate] = useState(false);
  const [showDiscarded, setShowDiscarded] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const importMutation = useMutation({
    mutationFn: () => api.importJob(importUrl.trim()),
    onSuccess: (result) => {
      toast.success(
        result.created
          ? "Vacante importada y analizada contra tu CV."
          : "La vacante ya estaba en el radar. Actualizamos sus datos y el match.",
      );
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      setImportUrl("");
      setImportOpen(false);
      navigate(`/jobs/${result.job.id}`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const { data: preferencesData } = useQuery({ queryKey: ["preferences"], queryFn: api.preferences });
  const autoSubmitEnabled = Boolean(preferencesData?.preferences.auto_submit_enabled);
  const [preferencesApplied, setPreferencesApplied] = useState(false);

  useEffect(() => {
    if (!preferencesData || preferencesApplied) return;
    const savedFreshness = preferencesData.preferences.freshness_days || 2;
    setMaxAgeDays([1, 2, 7].includes(savedFreshness) ? savedFreshness : 2);
    setPreferencesApplied(true);
  }, [preferencesData, preferencesApplied]);

  const autoRunMutation = useMutation({
    mutationFn: () => api.autoRun(preferencesData?.preferences.auto_submit_max_per_run),
    onSuccess: ({ run }) => {
      window.postMessage({ source: "jobradar-web", type: "START_AUTO_RUN", runId: run.id }, "*");
      toast.success(`Ronda #${run.id} creada con ${run.total} vacante${run.total === 1 ? "" : "s"}.`);
      navigate(`/auto-run/${run.id}`);
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  const autoSubmitPreferenceMutation = useMutation({
    mutationFn: (enabled: boolean) => api.updatePreferences({ auto_submit_enabled: enabled }),
    onSuccess: (result, enabled) => {
      queryClient.setQueryData(["preferences"], result);
      if (result.warning) toast.warning(result.warning);
      else
        toast.success(
          enabled
            ? "Auto-envío activado. Solo se aplicará a los ATS permitidos."
            : "Auto-envío desactivado.",
        );
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  const filters = useMemo(
    () => ({
      q: q.trim() || undefined,
      remote_type: remoteType === "all" ? undefined : remoteType,
      min_score: minScore || undefined,
      include_ineligible: includeIneligible || undefined,
      max_age_days: maxAgeDays || undefined,
      include_unknown_date: includeUnknownDate || undefined,
      discarded: showDiscarded || undefined,
      limit: 100,
    }),
    [q, remoteType, minScore, includeIneligible, maxAgeDays, includeUnknownDate, showDiscarded],
  );

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["jobs", filters],
    queryFn: () => api.jobs(filters),
  });
  const { data: dashboardSnapshot } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const eligibleTotal = dashboardSnapshot?.stats.eligible_jobs;
  const showing = data?.total ?? 0;
  const hiddenByFilters = !showDiscarded && eligibleTotal !== undefined && showing < eligibleTotal;

  const hasFilters = Boolean(
    q ||
      remoteType !== "all" ||
      minScore > 0 ||
      includeIneligible ||
      maxAgeDays !== 2 ||
      includeUnknownDate ||
      showDiscarded,
  );

  const resetFilters = () => {
    setQ("");
    setRemoteType("all");
    setMinScore(0);
    setIncludeIneligible(false);
    setMaxAgeDays(2);
    setIncludeUnknownDate(false);
    setShowDiscarded(false);
  };

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Oportunidades"
        title="Vacantes para tu perfil"
        description="Filtra por modalidad, score y texto. Las ofertas presenciales fuera de Colombia no entran al radar."
        actions={
          <>
            <div className="flex items-center gap-2 rounded-xl border border-line bg-ink/60 px-3 py-2">
              <span className="text-[11px] font-medium text-muted">Auto-envío</span>
              <Toggle
                checked={autoSubmitEnabled}
                onChange={(checked) => autoSubmitPreferenceMutation.mutate(checked)}
                disabled={autoSubmitPreferenceMutation.isPending}
                label="Activar o desactivar auto-envío"
              />
            </div>
            {autoSubmitEnabled && !showDiscarded && (
              <button
                type="button"
                onClick={() => autoRunMutation.mutate()}
                disabled={autoRunMutation.isPending}
                className="btn-primary"
              >
                {autoRunMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <WandSparkles className="h-4 w-4" />
                )}
                Realizar auto-envío
              </button>
            )}
            <button
              type="button"
              onClick={() => setImportOpen((open) => !open)}
              className={cn("btn-secondary", importOpen && "border-primary/30 text-primary")}
            >
              <Link2 className="h-4 w-4" /> Importar por URL
            </button>
            <SearchButton />
          </>
        }
      />

      {hiddenByFilters && (
        <section className="mb-4 flex flex-col gap-3 rounded-2xl border border-cyan-400/20 bg-cyan-400/[0.04] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <SlidersHorizontal className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" />
            <div>
              <p className="text-xs font-semibold text-cyan-100">
                Mostrando {showing} de {eligibleTotal} ofertas elegibles.
              </p>
              <p className="mt-1 text-[11px] leading-relaxed text-cyan-100/60">
                Los filtros activos de frescura, modalidad, búsqueda o seniority están ocultando el resto.
                Las vacantes descartadas y las no elegibles no se cuentan aquí.
              </p>
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            {maxAgeDays !== 0 && (
              <button type="button" onClick={() => setMaxAgeDays(0)} className="btn-secondary px-3 py-2 text-xs">
                Ver todo el histórico
              </button>
            )}
            <button type="button" onClick={resetFilters} className="btn-ghost px-3 py-2 text-xs">
              Limpiar filtros
            </button>
          </div>
        </section>
      )}

      {importOpen && (
        <section className="card mb-6 border-primary/20 p-4">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (importUrl.trim() && !importMutation.isPending) importMutation.mutate();
            }}
            className="flex flex-col gap-2.5 sm:flex-row"
          >
            <div className="relative flex-1">
              <Link2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                autoFocus
                type="url"
                value={importUrl}
                onChange={(event) => setImportUrl(event.target.value)}
                placeholder="https://www.computrabajo.com.co/oferta-de-trabajo..."
                className="input pl-9"
              />
            </div>
            <button
              type="submit"
              disabled={!importUrl.trim() || importMutation.isPending}
              className="btn-primary shrink-0"
            >
              {importMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {importMutation.isPending ? "Analizando..." : "Analizar vacante"}
            </button>
          </form>
          <p className="mt-2 text-[11px] leading-relaxed text-muted">
            Pega el enlace público de cualquier vacante. JobRadar extrae la información, la compara con tu CV y
            conserva el enlace original. La importación manual no se bloquea por el filtro de frescura.
          </p>
        </section>
      )}

      <section className="card mb-6 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              value={q}
              onChange={(event) => setQ(event.target.value)}
              placeholder="Buscar por cargo, empresa o tecnología..."
              className="input pl-9"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 rounded-xl border border-line bg-ink/60 px-3 py-2">
              <SlidersHorizontal className="h-3.5 w-3.5 text-muted" />
              <select
                value={remoteType}
                onChange={(event) => setRemoteType(event.target.value)}
                className="bg-transparent text-xs font-medium text-slate-200 outline-none"
              >
                <option value="all" className="bg-surface">Todas las modalidades</option>
                <option value="remote" className="bg-surface">Remoto</option>
                <option value="hybrid" className="bg-surface">Híbrido</option>
                <option value="onsite" className="bg-surface">Presencial</option>
              </select>
            </div>

            <div className="flex items-center gap-2 rounded-xl border border-line bg-ink/60 px-3 py-2">
              <Filter className="h-3.5 w-3.5 text-muted" />
              <select
                value={minScore}
                onChange={(event) => setMinScore(Number(event.target.value))}
                className="bg-transparent text-xs font-medium text-slate-200 outline-none"
              >
                <option value={0} className="bg-surface">Cualquier score</option>
                <option value={70} className="bg-surface">70% o más</option>
                <option value={85} className="bg-surface">85% o más</option>
              </select>
            </div>

            <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-line bg-ink/60 px-3 py-2 text-xs text-muted">
              <input
                type="checkbox"
                checked={includeIneligible}
                onChange={(event) => setIncludeIneligible(event.target.checked)}
                className="accent-emerald-400"
              />
              Ver no elegibles
            </label>

            {hasFilters && (
              <button type="button" onClick={resetFilters} className="btn-ghost px-2.5 py-2 text-xs">
                <X className="h-3.5 w-3.5" /> Limpiar
              </button>
            )}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line/60 pt-3">
          <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">
            <Clock3 className="h-3.5 w-3.5" /> Frescura
          </span>
          <div className="flex items-center gap-1 rounded-xl border border-line bg-ink/60 p-1">
            {[
              { label: "24 h", value: 1 },
              { label: "48 h", value: 2 },
              { label: "7 días", value: 7 },
              { label: "Todo", value: 0 },
            ].map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setMaxAgeDays(option.value)}
                className={cn(
                  "rounded-lg px-2.5 py-1.5 text-[11px] font-medium transition",
                  maxAgeDays === option.value
                    ? "bg-primary/15 text-primary ring-1 ring-primary/20"
                    : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-line bg-ink/60 px-3 py-2 text-xs text-muted">
            <input
              type="checkbox"
              checked={includeUnknownDate}
              onChange={(event) => setIncludeUnknownDate(event.target.checked)}
              className="accent-emerald-400"
            />
            Incluir sin fecha
          </label>
          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-line bg-ink/60 px-3 py-2 text-xs text-muted">
            <input
              type="checkbox"
              checked={showDiscarded}
              onChange={(event) => setShowDiscarded(event.target.checked)}
              className="accent-amber-400"
            />
            <ArchiveRestore className="h-3.5 w-3.5" /> Ver descartadas
          </label>
          <span className="text-[10px] text-slate-600">Por defecto: 48 horas, más recientes primero. Cambia el default en Ajustes.</span>
        </div>
      </section>

      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs text-muted">
          {isLoading ? "Buscando..." : `${data?.total ?? 0} vacante${data?.total === 1 ? "" : "s"} encontrada${data?.total === 1 ? "" : "s"}`}
        </p>
        <p className="hidden text-[11px] text-slate-600 sm:block">Más recientes primero</p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1, 2, 3, 4, 5].map((item) => (
            <div key={item} className="card h-56 animate-pulse bg-white/[0.02]" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={BriefcaseBusiness}
          title="No pudimos cargar las vacantes"
          description={error instanceof Error ? error.message : "Revisa la conexión con el backend."}
          action={
            <button type="button" onClick={() => refetch()} className="btn-primary">
              Reintentar
            </button>
          }
        />
      ) : data && data.items.length > 0 ? (
        <div className={cn("grid gap-4", "sm:grid-cols-2")}>
          {data.items.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={BriefcaseBusiness}
          title="No hay vacantes con esos filtros"
          description="Prueba una búsqueda más amplia o ejecuta una nueva búsqueda para traer ofertas."
          action={
            <button
              type="button"
              onClick={resetFilters}
              className="btn-secondary"
            >
              Limpiar filtros
            </button>
          }
        />
      )}
    </div>
  );
}
