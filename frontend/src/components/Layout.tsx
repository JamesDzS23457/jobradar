import { useQuery } from "@tanstack/react-query";
import {
  BriefcaseBusiness,
  KanbanSquare,
  LayoutDashboard,
  Menu,
  Radar,
  Settings,
  Sparkles,
  Upload,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { SearchButton } from "./SearchButton";

const navigation = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/jobs", label: "Vacantes", icon: BriefcaseBusiness },
  { to: "/tracker", label: "Seguimiento", icon: KanbanSquare },
  { to: "/profile", label: "Mi perfil", icon: UserRound },
  { to: "/settings", label: "Ajustes", icon: Settings },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: api.config });

  return (
    <div className="flex h-full flex-col">
      <Link to="/" onClick={onNavigate} className="flex items-center gap-3 px-1">
        <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/25">
          <Radar className="h-5 w-5" />
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-primary shadow-[0_0_10px_#34d399]" />
        </div>
        <div>
          <p className="font-display text-lg font-semibold tracking-tight text-white">JobRadar</p>
          <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted">Copiloto laboral</p>
        </div>
      </Link>

      <nav className="mt-8 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
                  isActive
                    ? "bg-primary/10 text-primary ring-1 ring-primary/20"
                    : "text-muted hover:bg-white/[0.04] hover:text-slate-200",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      <div className="mt-auto space-y-3">
        {config?.demo_mode && (
          <div className="rounded-2xl border border-primary/15 bg-primary/[0.05] p-3.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              Modo demo
            </div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
              Estás viendo un perfil y ofertas de ejemplo. Sube tu CV para empezar.
            </p>
            <Link
              to="/profile"
              onClick={onNavigate}
              className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-semibold text-primary hover:text-emerald-200"
            >
              <Upload className="h-3 w-3" /> Usar mi CV
            </Link>
          </div>
        )}

        <SearchButton className="w-full" />
        <p className="px-1 text-[10px] leading-relaxed text-slate-600">
          Bogotá · Remoto Colombia · Remoto global
        </p>
      </div>
    </div>
  );
}

export function Layout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: api.config });

  useEffect(() => {
    setOpen(false);
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [location.pathname]);

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-line/70 bg-ink/80 p-4 backdrop-blur-xl lg:block">
        <SidebarContent />
      </aside>

      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Cerrar menú"
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <aside className="relative h-full w-72 border-r border-line bg-ink p-4 shadow-2xl">
            <button
              type="button"
              aria-label="Cerrar menú"
              onClick={() => setOpen(false)}
              className="absolute right-3 top-3 rounded-lg p-1.5 text-muted hover:bg-white/5 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
            <SidebarContent onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line/60 bg-ink/75 px-4 py-3 backdrop-blur-xl lg:hidden">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
              <Radar className="h-4 w-4" />
            </div>
            <span className="font-display text-base font-semibold text-white">JobRadar</span>
          </Link>
          <button
            type="button"
            aria-label="Abrir menú"
            onClick={() => setOpen(true)}
            className="rounded-lg border border-line p-2 text-slate-300"
          >
            <Menu className="h-4 w-4" />
          </button>
        </header>

        {config?.demo_mode && (
          <div className="flex items-center justify-center gap-2 border-b border-primary/10 bg-primary/[0.04] px-4 py-2 text-[11px] text-emerald-200/90">
            <Sparkles className="h-3 w-3" />
            Modo demo con datos de ejemplo. Sube tu CV para personalizar el radar.
            <Link to="/profile" className="font-semibold underline decoration-primary/40 underline-offset-2 hover:text-white">
              Empezar
            </Link>
          </div>
        )}

        <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>

        <footer className="mx-auto max-w-7xl px-4 pb-8 text-[11px] text-slate-600 sm:px-6 lg:px-8">
          JobRadar · Copiloto personal de búsqueda laboral · No postula automáticamente por ti.
        </footer>
      </div>
    </div>
  );
}
