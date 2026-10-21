import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  FileText,
  Loader2,
  Plus,
  Save,
  Sparkles,
  Trash2,
  UploadCloud,
  UserRound,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { EducationItem, ExperienceItem, Profile } from "@/lib/types";
import { cn, parseList } from "@/lib/utils";

type ProfileForm = {
  name: string;
  email: string;
  phone: string;
  location: string;
  headline: string;
  summary: string;
  skills: string;
  languagesText: string;
  years_experience: number;
  experience: ExperienceItem[];
  education: EducationItem[];
};

const emptyForm: ProfileForm = {
  name: "",
  email: "",
  phone: "",
  location: "Bogotá, Colombia",
  headline: "",
  summary: "",
  skills: "",
  languagesText: "Español: Nativo",
  years_experience: 0,
  experience: [],
  education: [],
};

function profileToForm(profile: Profile): ProfileForm {
  return {
    name: profile.name || "",
    email: profile.email || "",
    phone: profile.phone || "",
    location: profile.location || "Bogotá, Colombia",
    headline: profile.headline || "",
    summary: profile.summary || "",
    skills: (profile.skills ?? []).join(", "),
    languagesText: Object.entries(profile.languages ?? {})
      .map(([language, level]) => `${language}: ${level}`)
      .join(", "),
    years_experience: profile.years_experience || 0,
    experience: (profile.experience ?? []).map((item) => ({
      company: item.company || "",
      role: item.role || "",
      dates: item.dates || "",
      bullets: item.bullets ?? [],
    })),
    education: (profile.education ?? []).map((item) => ({
      institution: item.institution || "",
      degree: item.degree || "",
      dates: item.dates || "",
    })),
  };
}

function parseLanguages(value: string): Record<string, string> {
  const languages: Record<string, string> = {};
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .forEach((item) => {
      const [language, ...rest] = item.split(":");
      if (language?.trim()) {
        languages[language.trim()] = rest.join(":").trim() || "B2";
      }
    });
  return languages;
}

export function ProfilePage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState<ProfileForm>(emptyForm);
  const [dragActive, setDragActive] = useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["profile"],
    queryFn: api.profile,
  });

  useEffect(() => {
    if (data?.profile) setForm(profileToForm(data.profile));
  }, [data?.profile]);

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateProfile({
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        location: form.location.trim(),
        headline: form.headline.trim(),
        summary: form.summary.trim(),
        skills: parseList(form.skills),
        languages: parseLanguages(form.languagesText),
        years_experience: Number(form.years_experience) || 0,
        experience: form.experience
          .map((item) => ({
            company: item.company.trim(),
            role: item.role.trim(),
            dates: item.dates.trim(),
            bullets: item.bullets.map((bullet) => bullet.trim()).filter(Boolean),
          }))
          .filter((item) => item.company || item.role || item.bullets.length > 0),
        education: form.education
          .map((item) => ({
            institution: item.institution.trim(),
            degree: item.degree.trim(),
            dates: item.dates.trim(),
          }))
          .filter((item) => item.institution || item.degree),
      }),
    onSuccess: () => {
      toast.success("Perfil guardado y matches recalculados.");
      queryClient.invalidateQueries();
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  const uploadMutation = useMutation({
    mutationFn: api.uploadCv,
    onSuccess: (result) => {
      toast.success(result.message);
      setForm(profileToForm(result.profile));
      queryClient.invalidateQueries();
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast.error("El archivo supera los 10 MB.");
      return;
    }
    uploadMutation.mutate(file);
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-10 w-64 animate-pulse rounded-lg bg-white/[0.04]" />
        <div className="grid gap-6 xl:grid-cols-3">
          <div className="card h-[560px] animate-pulse bg-white/[0.02] xl:col-span-2" />
          <div className="card h-[420px] animate-pulse bg-white/[0.02]" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <EmptyState
        icon={UserRound}
        title="No pudimos cargar tu perfil"
        description={error instanceof Error ? error.message : "Revisa la conexión con el backend."}
        action={
          <button type="button" onClick={() => refetch()} className="btn-primary">
            Reintentar
          </button>
        }
      />
    );
  }

  const profile = data?.profile;
  const completeness = [
    Boolean(form.name),
    Boolean(form.headline),
    form.skills.trim().length > 0,
    form.experience.length > 0,
    Boolean(profile?.has_cv),
  ].filter(Boolean).length;
  const completenessPercent = Math.round((completeness / 5) * 100);

  const updateExperience = (index: number, patch: Partial<ExperienceItem>) => {
    setForm((current) => ({
      ...current,
      experience: current.experience.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    }));
  };

  const updateEducation = (index: number, patch: Partial<EducationItem>) => {
    setForm((current) => ({
      ...current,
      education: current.education.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    }));
  };

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Mi perfil"
        title="La base de tu radar"
        description="Mientras más claro esté tu perfil, mejor será el match y la adaptación del CV. Puedes editar todo lo que la IA haya detectado."
        actions={
          <button
            type="button"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="btn-primary"
          >
            {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Guardar perfil
          </button>
        }
      />

      {!profile && (
        <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-primary/20 bg-primary/[0.06] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
            <div>
              <p className="text-sm font-semibold text-white">Empieza subiendo tu CV</p>
              <p className="mt-1 text-xs leading-relaxed text-muted">
                Extraeremos tu experiencia y habilidades. Después podrás corregir lo que haga falta.
              </p>
            </div>
          </div>
          <button type="button" onClick={() => fileInputRef.current?.click()} className="btn-secondary shrink-0">
            <UploadCloud className="h-4 w-4" /> Subir CV
          </button>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <section className="card p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="section-title">Datos básicos</h2>
                <p className="mt-1 text-xs text-muted">Lo que verá un reclutador en la primera línea.</p>
              </div>
              <UserRound className="h-4 w-4 text-muted" />
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="profile-name">
                  Nombre completo
                </label>
                <input
                  id="profile-name"
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  className="input"
                  placeholder="Tu nombre"
                />
              </div>
              <div>
                <label className="label" htmlFor="profile-location">
                  Ubicación
                </label>
                <input
                  id="profile-location"
                  value={form.location}
                  onChange={(event) => setForm((current) => ({ ...current, location: event.target.value }))}
                  className="input"
                  placeholder="Bogotá, Colombia"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="label" htmlFor="profile-headline">
                  Titular profesional
                </label>
                <input
                  id="profile-headline"
                  value={form.headline}
                  onChange={(event) => setForm((current) => ({ ...current, headline: event.target.value }))}
                  className="input"
                  placeholder="Backend Developer · Python · FastAPI · AWS"
                />
              </div>
              <div>
                <label className="label" htmlFor="profile-email">
                  Email
                </label>
                <input
                  id="profile-email"
                  type="email"
                  value={form.email}
                  onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                  className="input"
                  placeholder="tu@email.com"
                />
              </div>
              <div>
                <label className="label" htmlFor="profile-phone">
                  Teléfono
                </label>
                <input
                  id="profile-phone"
                  value={form.phone}
                  onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
                  className="input"
                  placeholder="+57 300 000 0000"
                />
              </div>
              <div>
                <label className="label" htmlFor="profile-years">
                  Años de experiencia
                </label>
                <input
                  id="profile-years"
                  type="number"
                  min={0}
                  max={60}
                  value={form.years_experience}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, years_experience: Number(event.target.value) }))
                  }
                  className="input"
                />
              </div>
              <div>
                <label className="label" htmlFor="profile-languages">
                  Idiomas
                </label>
                <input
                  id="profile-languages"
                  value={form.languagesText}
                  onChange={(event) => setForm((current) => ({ ...current, languagesText: event.target.value }))}
                  className="input"
                  placeholder="Español: Nativo, Inglés: B2"
                />
              </div>
            </div>
          </section>

          <section className="card p-5 sm:p-6">
            <h2 className="section-title">Resumen profesional</h2>
            <p className="mt-1 text-xs text-muted">Dos o tres frases con tu enfoque, stack y tipo de impacto.</p>
            <textarea
              value={form.summary}
              onChange={(event) => setForm((current) => ({ ...current, summary: event.target.value }))}
              rows={5}
              className="input mt-4 resize-y leading-relaxed"
              placeholder="Desarrolladora backend con experiencia construyendo APIs..."
            />
          </section>

          <section className="card p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="section-title">Habilidades</h2>
                <p className="mt-1 text-xs text-muted">Sepáralas con comas. El motor las normaliza y compara con cada oferta.</p>
              </div>
              <span className="chip">{parseList(form.skills).length} skills</span>
            </div>
            <input
              value={form.skills}
              onChange={(event) => setForm((current) => ({ ...current, skills: event.target.value }))}
              className="input mt-4"
              placeholder="Python, FastAPI, PostgreSQL, AWS, Docker"
            />
            <div className="mt-3 flex flex-wrap gap-1.5">
              {parseList(form.skills).map((skill) => (
                <span key={skill} className="rounded-lg border border-primary/15 bg-primary/[0.06] px-2.5 py-1 text-[11px] text-emerald-200">
                  {skill}
                </span>
              ))}
            </div>
          </section>

          <section className="card p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="section-title">Experiencia</h2>
                <p className="mt-1 text-xs text-muted">Bullets concretos, con herramientas y resultados medibles.</p>
              </div>
              <button
                type="button"
                onClick={() =>
                  setForm((current) => ({
                    ...current,
                    experience: [...current.experience, { company: "", role: "", dates: "", bullets: [] }],
                  }))
                }
                className="btn-secondary px-3 py-2 text-xs"
              >
                <Plus className="h-3.5 w-3.5" /> Añadir
              </button>
            </div>

            <div className="mt-5 space-y-4">
              {form.experience.map((item, index) => (
                <div key={index} className="rounded-xl border border-line/70 bg-white/[0.02] p-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className="label">Empresa</label>
                      <input
                        value={item.company}
                        onChange={(event) => updateExperience(index, { company: event.target.value })}
                        className="input"
                        placeholder="FinTech Andina"
                      />
                    </div>
                    <div>
                      <label className="label">Cargo</label>
                      <input
                        value={item.role}
                        onChange={(event) => updateExperience(index, { role: event.target.value })}
                        className="input"
                        placeholder="Backend Developer"
                      />
                    </div>
                    <div>
                      <label className="label">Fechas</label>
                      <input
                        value={item.dates}
                        onChange={(event) => updateExperience(index, { dates: event.target.value })}
                        className="input"
                        placeholder="2022 - 2025"
                      />
                    </div>
                    <div className="flex items-end justify-end">
                      <button
                        type="button"
                        onClick={() =>
                          setForm((current) => ({
                            ...current,
                            experience: current.experience.filter((_, itemIndex) => itemIndex !== index),
                          }))
                        }
                        className="btn-ghost px-2.5 py-2 text-xs text-rose-300 hover:bg-rose-500/10"
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Quitar
                      </button>
                    </div>
                  </div>
                  <div className="mt-3">
                    <label className="label">Bullets (uno por línea)</label>
                    <textarea
                      value={item.bullets.join("\n")}
                      onChange={(event) => updateExperience(index, { bullets: event.target.value.split("\n") })}
                      rows={4}
                      className="input resize-y leading-relaxed"
                      placeholder="Diseñé APIs con FastAPI..."
                    />
                  </div>
                </div>
              ))}
              {form.experience.length === 0 && (
                <p className="rounded-xl border border-dashed border-line p-4 text-xs text-muted">
                  Aún no hay experiencia. Añádela manualmente o sube tu CV para extraerla.
                </p>
              )}
            </div>
          </section>

          <section className="card p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="section-title">Educación</h2>
                <p className="mt-1 text-xs text-muted">Títulos y formación relevante.</p>
              </div>
              <button
                type="button"
                onClick={() =>
                  setForm((current) => ({
                    ...current,
                    education: [...current.education, { institution: "", degree: "", dates: "" }],
                  }))
                }
                className="btn-secondary px-3 py-2 text-xs"
              >
                <Plus className="h-3.5 w-3.5" /> Añadir
              </button>
            </div>

            <div className="mt-5 space-y-3">
              {form.education.map((item, index) => (
                <div key={index} className="grid gap-3 rounded-xl border border-line/70 bg-white/[0.02] p-4 sm:grid-cols-3">
                  <div>
                    <label className="label">Institución</label>
                    <input
                      value={item.institution}
                      onChange={(event) => updateEducation(index, { institution: event.target.value })}
                      className="input"
                      placeholder="Universidad Nacional"
                    />
                  </div>
                  <div>
                    <label className="label">Título</label>
                    <input
                      value={item.degree}
                      onChange={(event) => updateEducation(index, { degree: event.target.value })}
                      className="input"
                      placeholder="Ingeniería de Sistemas"
                    />
                  </div>
                  <div className="flex items-end gap-2">
                    <div className="flex-1">
                      <label className="label">Fechas</label>
                      <input
                        value={item.dates}
                        onChange={(event) => updateEducation(index, { dates: event.target.value })}
                        className="input"
                        placeholder="2016 - 2020"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setForm((current) => ({
                          ...current,
                          education: current.education.filter((_, itemIndex) => itemIndex !== index),
                        }))
                      }
                      className="btn-ghost px-2.5 py-2.5 text-rose-300 hover:bg-rose-500/10"
                      aria-label="Quitar educación"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
              {form.education.length === 0 && <p className="text-xs text-muted">Sin formación registrada.</p>}
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
          <div
            className={cn(
              "card cursor-pointer p-5 transition",
              dragActive ? "border-primary/50 bg-primary/[0.06]" : "hover:border-primary/25",
            )}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragActive(false);
              handleFile(event.dataTransfer.files?.[0]);
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={(event) => {
                handleFile(event.target.files?.[0]);
                event.target.value = "";
              }}
            />
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20">
              {uploadMutation.isPending ? <Loader2 className="h-5 w-5 animate-spin" /> : <UploadCloud className="h-5 w-5" />}
            </div>
            <h2 className="mt-4 font-display text-base font-semibold text-white">
              {uploadMutation.isPending ? "Procesando CV..." : "Subir o reemplazar CV"}
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-muted">
              PDF, DOCX, TXT o MD. Hasta 10 MB. Extraemos texto; si es un PDF escaneado, usa DOCX o TXT.
            </p>
            {profile?.has_cv && (
              <div className="mt-3 flex items-center gap-2 rounded-lg border border-line/60 bg-white/[0.02] px-3 py-2 text-[11px] text-slate-300">
                <FileText className="h-3.5 w-3.5 shrink-0 text-primary" />
                <span className="truncate">{profile.cv_file_name}</span>
              </div>
            )}
            <button type="button" className="btn-secondary mt-4 w-full text-xs">
              Seleccionar archivo
            </button>
          </div>

          <div className="card p-5">
            <div className="flex items-center justify-between">
              <h2 className="section-title">Perfil completo</h2>
              <span className="text-xs font-semibold text-primary">{completenessPercent}%</span>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/[0.05]">
              <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${completenessPercent}%` }} />
            </div>
            <ul className="mt-4 space-y-2.5">
              {[
                ["Nombre", Boolean(form.name)],
                ["Titular profesional", Boolean(form.headline)],
                ["Habilidades", form.skills.trim().length > 0],
                ["Experiencia", form.experience.length > 0],
                ["CV cargado", Boolean(profile?.has_cv)],
              ].map(([label, done]) => (
                <li key={String(label)} className="flex items-center gap-2 text-xs">
                  <CheckCircle2 className={cn("h-3.5 w-3.5", done ? "text-emerald-400" : "text-slate-600")} />
                  <span className={done ? "text-slate-300" : "text-muted"}>{label}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-dashed border-line p-4 text-[11px] leading-relaxed text-muted">
            <p className="flex items-center gap-1.5 font-semibold text-slate-300">
              <Sparkles className="h-3.5 w-3.5 text-primary" /> Consejo
            </p>
            <p className="mt-2">
              Incluye tecnologías con el mismo nombre que usan las ofertas (por ejemplo, FastAPI o PostgreSQL). El motor
              también reconoce alias, pero un perfil limpio mejora el match.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
