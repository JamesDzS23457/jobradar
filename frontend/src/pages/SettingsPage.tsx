import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bell,
  Bot,
  CheckCircle2,
  Database,
  Globe2,
  KeyRound,
  Loader2,
  Mail,
  MapPin,
  RefreshCw,
  Save,
  Search,
  Server,
  Settings,
  ShieldCheck,
  Trash2,
  WandSparkles,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Toggle } from "@/components/Toggle";
import { api } from "@/lib/api";
import type { Preferences } from "@/lib/types";
import { cn, joinList, parseList } from "@/lib/utils";

type SettingsForm = {
  roles: string;
  keywords: string;
  home_city: string;
  commute_cities: string;
  country: string;
  salary_min: number;
  currency: string;
  seniority: string;
  remote_preference: string;
  accept_relocation: boolean;
  accept_international_remote: boolean;
  alert_threshold: number;
  digest_threshold: number;
  digest_hour: number;
  search_interval_hours: number;
  freshness_days: number;
  auto_submit_enabled: boolean;
  auto_submit_max_per_run: number;
  default_cv_source: "tailored" | "original";
};

const emptyForm: SettingsForm = {
  roles: "",
  keywords: "",
  home_city: "Bogotá",
  commute_cities: "",
  country: "Colombia",
  salary_min: 0,
  currency: "COP",
  seniority: "mid",
  remote_preference: "any",
  accept_relocation: false,
  accept_international_remote: true,
  alert_threshold: 85,
  digest_threshold: 70,
  digest_hour: 8,
  search_interval_hours: 6,
  freshness_days: 2,
  auto_submit_enabled: false,
  auto_submit_max_per_run: 5,
  default_cv_source: "tailored",
};

function preferencesToForm(preferences: Preferences): SettingsForm {
  return {
    roles: joinList(preferences.roles),
    keywords: joinList(preferences.keywords),
    home_city: preferences.home_city || "Bogotá",
    commute_cities: joinList(preferences.commute_cities),
    country: preferences.country || "Colombia",
    salary_min: preferences.salary_min || 0,
    currency: preferences.currency || "COP",
    seniority: preferences.seniority || "mid",
    remote_preference: preferences.remote_preference || "any",
    accept_relocation: Boolean(preferences.accept_relocation),
    accept_international_remote: Boolean(preferences.accept_international_remote),
    alert_threshold: preferences.alert_threshold ?? 85,
    digest_threshold: preferences.digest_threshold ?? 70,
    digest_hour: preferences.digest_hour ?? 8,
    search_interval_hours: preferences.search_interval_hours ?? 6,
    freshness_days: preferences.freshness_days ?? 2,
    auto_submit_enabled: Boolean(preferences.auto_submit_enabled),
    auto_submit_max_per_run: preferences.auto_submit_max_per_run ?? 5,
    default_cv_source: preferences.default_cv_source || "tailored",
  };
}


function intInRange(value: number, minimum: number, maximum: number, fallback: number): number {
  const parsed = Math.trunc(Number(value));
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(maximum, Math.max(minimum, parsed));
}

function IntegrationRow({
  icon: Icon,
  title,
  description,
  connected,
  note,
}: {
  icon: typeof Bot;
  title: string;
  description: string;
  connected: boolean;
  note?: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-line/60 bg-white/[0.02] p-3">
      <div
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ring-1",
          connected ? "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20" : "bg-white/[0.03] text-slate-500 ring-line",
        )}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-semibold text-slate-200">{title}</p>
          <span
            className={cn(
              "shrink-0 rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider",
              connected ? "bg-emerald-400/10 text-emerald-300" : "bg-white/[0.04] text-slate-500",
            )}
          >
            {connected ? "Conectado" : "Opcional"}
          </span>
        </div>
        <p className="mt-1 text-[11px] leading-relaxed text-muted">{note || description}</p>
      </div>
    </div>
  );
}

export function SettingsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<SettingsForm>(emptyForm);

  const { data: preferencesData, isLoading } = useQuery({
    queryKey: ["preferences"],
    queryFn: api.preferences,
  });
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: api.config });

  useEffect(() => {
    if (preferencesData?.preferences) setForm(preferencesToForm(preferencesData.preferences));
  }, [preferencesData?.preferences]);

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updatePreferences({
        roles: parseList(form.roles),
        keywords: parseList(form.keywords),
        home_city: form.home_city.trim() || "Bogotá",
        commute_cities: parseList(form.commute_cities),
        country: form.country.trim() || "Colombia",
        salary_min: Math.max(0, Math.trunc(Number(form.salary_min) || 0)),
        currency: form.currency === "USD" ? "USD" : "COP",
        seniority: form.seniority,
        remote_preference: form.remote_preference,
        accept_relocation: form.accept_relocation,
        accept_international_remote: form.accept_international_remote,
        alert_threshold: intInRange(form.alert_threshold, 0, 100, 85),
        digest_threshold: intInRange(form.digest_threshold, 0, 100, 70),
        digest_hour: intInRange(form.digest_hour, 0, 23, 8),
        search_interval_hours: intInRange(form.search_interval_hours, 1, 168, 6),
        freshness_days: intInRange(form.freshness_days, 1, 365, 2),
        auto_submit_enabled: form.auto_submit_enabled,
        auto_submit_max_per_run: intInRange(form.auto_submit_max_per_run, 1, 20, 5),
        default_cv_source: form.default_cv_source,
      }),
    onSuccess: (result) => {
      if (result.warning) toast.warning(result.warning);
      else toast.success("Preferencias guardadas y matches recalculados.");
      queryClient.invalidateQueries();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const testLlmMutation = useMutation({
    mutationFn: api.testLlm,
    onSuccess: (result) => {
      if (result.ok) toast.success(`${result.message} ${result.model ?? ""}`.trim());
      else toast.error(result.message);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const testEmailMutation = useMutation({
    mutationFn: api.testEmail,
    onSuccess: (result) => {
      if (result.sent) toast.success(result.message);
      else toast.error(result.message);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const resetMutation = useMutation({
    mutationFn: api.demoReset,
    onSuccess: () => {
      toast.success("Modo demo reiniciado.");
      queryClient.invalidateQueries();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteData,
    onSuccess: () => {
      toast.success("Datos eliminados. Puedes empezar de cero con tu CV.");
      queryClient.clear();
      navigate("/profile");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const confirmDelete = () => {
    const confirmed = window.confirm(
      "Esto borra tu perfil, CVs, ofertas, matches, postulaciones y archivos generados. No se puede deshacer. ¿Continuar?",
    );
    if (confirmed) deleteMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-10 w-64 animate-pulse rounded-lg bg-white/[0.04]" />
        <div className="grid gap-6 xl:grid-cols-3">
          <div className="card h-[620px] animate-pulse bg-white/[0.02] xl:col-span-2" />
          <div className="card h-[480px] animate-pulse bg-white/[0.02]" />
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Configuración"
        title="Ajusta el radar a tu vida"
        description="Define qué roles buscas, dónde aceptas trabajar y cuándo quieres recibir alertas. Los cambios recalculan los matches."
        actions={
          <button
            type="button"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="btn-primary"
          >
            {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Guardar ajustes
          </button>
        }
      />

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <section className="card p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-400/10 text-cyan-300 ring-1 ring-cyan-400/20">
                <Search className="h-4 w-4" />
              </div>
              <div>
                <h2 className="section-title">Búsqueda</h2>
                <p className="text-xs text-muted">Los cargos y keywords que alimentan las consultas a las fuentes.</p>
              </div>
            </div>

            <div className="mt-5 grid gap-4">
              <div>
                <label className="label" htmlFor="roles">
                  Roles objetivo
                </label>
                <input
                  id="roles"
                  value={form.roles}
                  onChange={(event) => setForm((current) => ({ ...current, roles: event.target.value }))}
                  className="input"
                  placeholder="Backend Developer, Desarrollador Backend, Python Developer, Desarrollador Python"
                />
                <p className="mt-1.5 text-[11px] text-muted">
                  Se completan al subir tu CV, en español e inglés. Puedes editarlos; se usan en JSearch y Jooble.
                </p>
              </div>
              <div>
                <label className="label" htmlFor="keywords">
                  Keywords extra
                </label>
                <input
                  id="keywords"
                  value={form.keywords}
                  onChange={(event) => setForm((current) => ({ ...current, keywords: event.target.value }))}
                  className="input"
                  placeholder="Python, FastAPI, AWS, PostgreSQL"
                />
                <p className="mt-1.5 text-[11px] text-muted">
                  Se detectan desde tus habilidades. Añade o quita términos cuando quieras.
                </p>
              </div>
              <div>
                <label className="label" htmlFor="freshness_days">
                  Frescura por defecto
                </label>
                <select
                  id="freshness_days"
                  value={form.freshness_days}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, freshness_days: Number(event.target.value) }))
                  }
                  className="input max-w-xs"
                >
                  <option value={1} className="bg-surface">Últimas 24 horas</option>
                  <option value={2} className="bg-surface">Últimas 48 horas</option>
                  <option value={7} className="bg-surface">Últimos 7 días</option>
                </select>
                <p className="mt-1.5 text-[11px] text-muted">
                  Se aplica al listado y a las rondas de auto-envío. Las importaciones manuales por URL no se filtran.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="label" htmlFor="seniority">
                    Seniority
                  </label>
                  <select
                    id="seniority"
                    value={form.seniority}
                    onChange={(event) => setForm((current) => ({ ...current, seniority: event.target.value }))}
                    className="input"
                  >
                    <option value="junior" className="bg-surface">Junior</option>
                    <option value="mid" className="bg-surface">Mid</option>
                    <option value="senior" className="bg-surface">Senior</option>
                    <option value="lead" className="bg-surface">Lead / Staff</option>
                    <option value="any" className="bg-surface">Cualquiera</option>
                  </select>
                  <p className="mt-1.5 text-[11px] text-muted">
                    No se muestran cargos por encima de este nivel. Elige Cualquiera para ver todos.
                  </p>
                </div>
                <div>
                  <label className="label" htmlFor="salary_min">
                    Salario mínimo
                  </label>
                  <input
                    id="salary_min"
                    type="number"
                    min={0}
                    step={500000}
                    value={form.salary_min}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, salary_min: Number(event.target.value) }))
                    }
                    className="input"
                  />
                </div>
                <div>
                  <label className="label" htmlFor="currency">
                    Moneda
                  </label>
                  <select
                    id="currency"
                    value={form.currency}
                    onChange={(event) => setForm((current) => ({ ...current, currency: event.target.value }))}
                    className="input"
                  >
                    <option value="COP" className="bg-surface">COP</option>
                    <option value="USD" className="bg-surface">USD</option>
                  </select>
                </div>
              </div>
            </div>
          </section>

          <section className="card p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-400/10 text-emerald-300 ring-1 ring-emerald-400/20">
                <MapPin className="h-4 w-4" />
              </div>
              <div>
                <h2 className="section-title">Ubicación y modalidad</h2>
                <p className="text-xs text-muted">La regla más importante: no perder tiempo con ofertas que no puedes tomar.</p>
              </div>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="home_city">
                  Ciudad base
                </label>
                <input
                  id="home_city"
                  value={form.home_city}
                  onChange={(event) => setForm((current) => ({ ...current, home_city: event.target.value }))}
                  className="input"
                  placeholder="Bogotá"
                />
              </div>
              <div>
                <label className="label" htmlFor="country">
                  País
                </label>
                <input
                  id="country"
                  value={form.country}
                  onChange={(event) => setForm((current) => ({ ...current, country: event.target.value }))}
                  className="input"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="label" htmlFor="commute_cities">
                  Ciudades cercanas para presencial/híbrido
                </label>
                <input
                  id="commute_cities"
                  value={form.commute_cities}
                  onChange={(event) => setForm((current) => ({ ...current, commute_cities: event.target.value }))}
                  className="input"
                  placeholder="Chía, Cota, Funza, Mosquera, Soacha"
                />
                <p className="mt-1.5 text-[11px] text-muted">
                  Solo aplica dentro de Colombia. Otras ciudades quedan fuera salvo que aceptes reubicarte.
                </p>
              </div>
              <div className="sm:col-span-2">
                <label className="label" htmlFor="remote_preference">
                  Preferencia de modalidad
                </label>
                <select
                  id="remote_preference"
                  value={form.remote_preference}
                  onChange={(event) => setForm((current) => ({ ...current, remote_preference: event.target.value }))}
                  className="input"
                >
                  <option value="any" className="bg-surface">Cualquier modalidad</option>
                  <option value="remote" className="bg-surface">Remoto</option>
                  <option value="hybrid" className="bg-surface">Híbrido</option>
                  <option value="onsite" className="bg-surface">Presencial</option>
                </select>
              </div>
            </div>

            <div className="mt-5 space-y-3 border-t border-line/60 pt-5">
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={form.accept_relocation}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, accept_relocation: event.target.checked }))
                  }
                  className="mt-1 accent-emerald-400"
                />
                <span>
                  <span className="block text-xs font-medium text-slate-200">Acepto reubicarme dentro de Colombia</span>
                  <span className="mt-0.5 block text-[11px] leading-relaxed text-muted">
                    Habilita ofertas presenciales o híbridas en Medellín, Cali y otras ciudades.
                  </span>
                </span>
              </label>
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={form.accept_international_remote}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, accept_international_remote: event.target.checked }))
                  }
                  className="mt-1 accent-emerald-400"
                />
                <span>
                  <span className="block text-xs font-medium text-slate-200">Acepto remoto internacional</span>
                  <span className="mt-0.5 block text-[11px] leading-relaxed text-muted">
                    Remoto en LatAm o global. Nunca presencial fuera de Colombia.
                  </span>
                </span>
              </label>
            </div>
          </section>

          <section className="card p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-400/10 text-violet-300 ring-1 ring-violet-400/20">
                <WandSparkles className="h-4 w-4" />
              </div>
              <div>
                <h2 className="section-title">Postulaciones y auto-envío</h2>
                <p className="text-xs text-muted">
                  El asistente rellena formularios en portales compatibles. El auto-envío es opcional y nunca se usa en
                  portales manuales.
                </p>
              </div>
            </div>

            <div className="mt-5 space-y-4">
              <div className="flex items-start justify-between gap-4 rounded-xl border border-line/60 bg-white/[0.02] p-4">
                <div>
                  <p className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                    <Zap className="h-3.5 w-3.5 text-emerald-300" /> Habilitar “Realizar auto-envío”
                  </p>
                  <p className="mt-1 max-w-xl text-[11px] leading-relaxed text-muted">
                    Cuando esté activo, aparecerá el botón en Vacantes. Solo se procesan portales permitidos; LinkedIn,
                    Indeed, Computrabajo, Magneto, elempleo y Glassdoor siguen siendo manuales.
                  </p>
                </div>
                <Toggle
                  checked={form.auto_submit_enabled}
                  onChange={(checked) =>
                    setForm((current) => ({ ...current, auto_submit_enabled: checked }))
                  }
                  label="Habilitar auto-envío"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="label" htmlFor="auto_submit_max_per_run">
                    Máximo de vacantes por ronda
                  </label>
                  <input
                    id="auto_submit_max_per_run"
                    type="number"
                    min={1}
                    max={20}
                    value={form.auto_submit_max_per_run}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        auto_submit_max_per_run: Number(event.target.value),
                      }))
                    }
                    className="input"
                  />
                  <p className="mt-1.5 text-[11px] text-muted">
                    Se procesan en orden, una por una. Las que no se pueden automatizar quedan como cartas manuales.
                  </p>
                </div>
                <div>
                  <label className="label" htmlFor="default_cv_source">
                    CV predeterminado
                  </label>
                  <select
                    id="default_cv_source"
                    value={form.default_cv_source}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        default_cv_source: event.target.value as "tailored" | "original",
                      }))
                    }
                    className="input"
                  >
                    <option value="tailored" className="bg-surface">CV adaptado ATS</option>
                    <option value="original" className="bg-surface">PDF original</option>
                  </select>
                  <p className="mt-1.5 text-[11px] text-muted">
                    Siempre puedes cambiarlo en la pantalla de preparación de cada postulación.
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-amber-400/15 bg-amber-400/[0.04] p-3 text-[11px] leading-relaxed text-amber-100/70">
                <p className="flex items-center gap-1.5 font-semibold text-amber-300">
                  <ShieldCheck className="h-3.5 w-3.5" /> Sin atajos peligrosos
                </p>
                <p className="mt-1.5">
                  La extensión usa tu sesión real del navegador. No guarda contraseñas, no evade CAPTCHA, no simula
                  huellas del navegador y no salta 2FA. Si el portal bloquea o pide un paso humano, la vacante se marca
                  como manual.
                </p>
              </div>
              <p className="text-[11px] text-muted">
                Portales con auto-envío permitido:{" "}
                <span className="text-slate-300">
                  {(config?.auto_submit_portals ?? ["greenhouse", "lever", "ashby", "workable"]).join(", ")}
                </span>
              </p>
            </div>
          </section>

          <section className="card p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-400/10 text-amber-300 ring-1 ring-amber-400/20">
                <Bell className="h-4 w-4" />
              </div>
              <div>
                <h2 className="section-title">Alertas y frecuencia</h2>
                <p className="text-xs text-muted">Correo inmediato para matches excelentes y resumen diario para el resto.</p>
              </div>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              <div>
                <label className="label" htmlFor="alert_threshold">
                  Alerta inmediata (score)
                </label>
                <input
                  id="alert_threshold"
                  type="number"
                  min={0}
                  max={100}
                  value={form.alert_threshold}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, alert_threshold: Number(event.target.value) }))
                  }
                  className="input"
                />
              </div>
              <div>
                <label className="label" htmlFor="digest_threshold">
                  Resumen diario (desde)
                </label>
                <input
                  id="digest_threshold"
                  type="number"
                  min={0}
                  max={100}
                  value={form.digest_threshold}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, digest_threshold: Number(event.target.value) }))
                  }
                  className="input"
                />
              </div>
              <div>
                <label className="label" htmlFor="digest_hour">
                  Hora del resumen
                </label>
                <input
                  id="digest_hour"
                  type="number"
                  min={0}
                  max={23}
                  value={form.digest_hour}
                  onChange={(event) => setForm((current) => ({ ...current, digest_hour: Number(event.target.value) }))}
                  className="input"
                />
              </div>
              <div className="sm:col-span-3">
                <label className="label" htmlFor="search_interval_hours">
                  Frecuencia de búsqueda automática (horas)
                </label>
                <input
                  id="search_interval_hours"
                  type="number"
                  min={1}
                  max={168}
                  value={form.search_interval_hours}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, search_interval_hours: Number(event.target.value) }))
                  }
                  className="input max-w-xs"
                />
                <p className="mt-1.5 text-[11px] text-muted">
                  El scheduler debe estar activo (`ENABLE_SCHEDULER=true`). En modo demo no se envían correos.
                </p>
              </div>
            </div>
          </section>

          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              className="btn-primary"
            >
              {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Guardar cambios
            </button>
          </div>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
          <section className="card p-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="section-title">Integraciones</h2>
                <p className="mt-1 text-xs text-muted">Opcionales para producción.</p>
              </div>
              <Server className="h-4 w-4 text-muted" />
            </div>

            <div className="mt-4 space-y-2.5">
              <IntegrationRow
                icon={Bot}
                title="IA / LLM"
                description="Parsing avanzado y adaptación de CV."
                connected={Boolean(config?.llm_configured)}
                note={
                  config?.llm_configured
                    ? `OpenRouter · ${config.llm_model_quality} (fallback: ${config.llm_model_fallback})`
                    : "Sin clave: se usan heurísticas locales. Añade OPENROUTER/LLM_API_KEY en backend/.env."
                }
              />
              <IntegrationRow
                icon={Mail}
                title="Gmail / SMTP"
                description="Alertas por correo."
                connected={Boolean(config?.smtp_configured)}
                note={config?.smtp_configured ? "Listo para enviar alertas." : "Configura SMTP_USER y SMTP_PASSWORD."}
              />
              <IntegrationRow
                icon={Search}
                title="JSearch"
                description="Ofertas de Colombia vía RapidAPI."
                connected={Boolean(config?.jsearch_configured)}
                note={config?.jsearch_configured ? "Fuente activa." : "Añade JSEARCH_API_KEY."}
              />
              <IntegrationRow
                icon={KeyRound}
                title="Jooble"
                description="Ofertas agregadas de Colombia."
                connected={Boolean(config?.jooble_configured)}
                note={config?.jooble_configured ? "Fuente activa." : "Añade JOOBLE_API_KEY."}
              />
              <IntegrationRow
                icon={Globe2}
                title="Búsqueda web · Tavily"
                description="Enlaces públicos de Computrabajo, elempleo, Magneto, GetOnBoard y más."
                connected={Boolean(config?.tavily_configured)}
                note={
                  config?.tavily_configured
                    ? config.tavily_keyless
                      ? "Activo. Usa TAVILY_API_KEY si la configuras; si no, modo keyless."
                      : "Activo con TAVILY_API_KEY."
                    : "Activa TAVILY_KEYLESS=true o añade TAVILY_API_KEY."
                }
              />
              <IntegrationRow
                icon={KeyRound}
                title="Brave Search (opcional)"
                description="Alternativa de búsqueda web; requiere tarjeta."
                connected={Boolean(config?.brave_configured)}
                note={
                  config?.web_search_provider === "brave" && config?.brave_configured
                    ? "Proveedor activo."
                    : "Opcional. Tavily es el proveedor recomendado."
                }
              />
            </div>

            <button
              type="button"
              onClick={() => testLlmMutation.mutate()}
              disabled={!config?.llm_configured || testLlmMutation.isPending}
              className="btn-secondary mt-4 w-full text-xs"
            >
              {testLlmMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Bot className="h-3.5 w-3.5" />}
              Probar modelo de IA
            </button>
            <button
              type="button"
              onClick={() => testEmailMutation.mutate()}
              disabled={testEmailMutation.isPending}
              className="btn-secondary mt-2 w-full text-xs"
            >
              {testEmailMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}
              Enviar correo de prueba
            </button>
            <p className="mt-2 text-center text-[10px] text-slate-600">
              {config?.smtp_configured
                ? "Se enviará al correo configurado en ALERT_TO."
                : "Aún no hay SMTP configurado."}
            </p>
          </section>

          <section className="card p-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="section-title">Modo demo</h2>
                <p className="mt-1 text-xs text-muted">Datos de ejemplo para probar.</p>
              </div>
              <Database className="h-4 w-4 text-muted" />
            </div>
            <p className="mt-3 text-[11px] leading-relaxed text-muted">
              Reinicia el perfil de Ana Torres, las 18 ofertas y las postulaciones de ejemplo. Útil para mostrar el
              portafolio desde cero.
            </p>
            <button
              type="button"
              onClick={() => resetMutation.mutate()}
              disabled={resetMutation.isPending}
              className="btn-secondary mt-4 w-full text-xs"
            >
              {resetMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Reiniciar demo
            </button>
          </section>

          <section className="rounded-2xl border border-rose-400/20 bg-rose-400/[0.04] p-5">
            <div className="flex items-center gap-2 text-rose-300">
              <AlertTriangle className="h-4 w-4" />
              <h2 className="text-sm font-semibold">Zona de peligro</h2>
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-rose-100/60">
              Borra tu perfil, CV cargado, ofertas, matches, postulaciones y archivos exportados. No se puede deshacer.
            </p>
            <button
              type="button"
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
              className="btn-danger mt-4 w-full text-xs"
            >
              {deleteMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              Borrar todos mis datos
            </button>
          </section>

          <div className="rounded-2xl border border-dashed border-line p-4 text-[11px] leading-relaxed text-muted">
            <p className="flex items-center gap-1.5 font-semibold text-slate-300">
              <Settings className="h-3.5 w-3.5 text-primary" /> Variables de entorno
            </p>
            <p className="mt-2">
              Las claves viven en <code className="rounded bg-white/[0.06] px-1 py-0.5 text-[10px] text-slate-300">backend/.env</code>,
              nunca en el navegador. Consulta <code className="rounded bg-white/[0.06] px-1 py-0.5 text-[10px] text-slate-300">.env.example</code>.
            </p>
            <div className="mt-3 flex items-center gap-1.5 text-emerald-300/80">
              <CheckCircle2 className="h-3 w-3" /> {config?.database === "sqlite" ? "SQLite local" : "Base externa"}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
