export function DigestStat({
  icon,
  label,
  count,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg bg-background/50 p-2">
      <span className={color}>{icon}</span>
      <span className="text-lg font-bold">{count}</span>
      <span className="text-[10px] text-muted-foreground">{label}</span>
    </div>
  );
}
