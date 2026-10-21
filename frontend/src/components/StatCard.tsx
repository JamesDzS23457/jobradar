import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  value: string | number;
  hint: string;
  icon: LucideIcon;
  tone?: "primary" | "cyan" | "amber" | "rose";
};

const tones = {
  primary: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20",
  cyan: "bg-cyan-400/10 text-cyan-300 ring-cyan-400/20",
  amber: "bg-amber-400/10 text-amber-300 ring-amber-400/20",
  rose: "bg-rose-400/10 text-rose-300 ring-rose-400/20",
};

export function StatCard({ label, value, hint, icon: Icon, tone = "primary" }: Props) {
  return (
    <div className="card card-hover p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{label}</p>
          <p className="mt-2 font-display text-3xl font-semibold text-white">{value}</p>
          <p className="mt-1 text-xs text-muted">{hint}</p>
        </div>
        <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl ring-1", tones[tone])}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}
