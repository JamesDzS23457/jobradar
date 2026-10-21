type Props = {
  data: { range: string; count: number }[];
};

const colors = ["#34d399", "#22d3ee", "#fbbf24", "#fb7185"];

export function ScoreDistribution({ data }: Props) {
  const max = Math.max(1, ...data.map((item) => item.count));
  return (
    <div className="space-y-3">
      {data.map((item, index) => (
        <div key={item.range} className="flex items-center gap-3">
          <span className="w-16 shrink-0 text-xs font-medium text-muted">{item.range}</span>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-white/[0.04]">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${Math.max(4, (item.count / max) * 100)}%`, backgroundColor: colors[index] }}
            />
          </div>
          <span className="w-6 text-right text-xs font-semibold text-slate-300">{item.count}</span>
        </div>
      ))}
    </div>
  );
}
