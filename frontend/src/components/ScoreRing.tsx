import { cn, scoreColor, scoreStroke } from "@/lib/utils";

type Props = {
  score: number;
  size?: number;
  stroke?: number;
  className?: string;
  showLabel?: boolean;
};

export function ScoreRing({ score, size = 64, stroke = 5, className, showLabel = true }: Props) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.max(0, Math.min(100, score)) / 100;
  const color = scoreStroke(score);

  return (
    <div className={cn("relative inline-flex shrink-0 items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#1d2a3c" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference * progress} ${circumference}`}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("font-display font-semibold leading-none", scoreColor(score), size >= 80 ? "text-xl" : "text-sm")}>
          {Math.round(score)}
        </span>
        {showLabel && size >= 80 && <span className="mt-0.5 text-[9px] uppercase tracking-wider text-muted">match</span>}
      </div>
    </div>
  );
}
