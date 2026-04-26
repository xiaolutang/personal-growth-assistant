interface ProgressRingProps {
  percentage: number;
  size?: number;
  showLabel?: boolean;
}

/** 进度颜色语义：<30% 红色、30-70% 黄色、>70% 绿色 */
function getProgressColor(pct: number): string {
  if (pct < 30) return "text-red-500";
  if (pct <= 70) return "text-yellow-500";
  return "text-green-500";
}

function getProgressBgColor(pct: number): string {
  if (pct < 30) return "text-red-500/20";
  if (pct <= 70) return "text-yellow-500/20";
  return "text-green-500/20";
}

export function ProgressRing({ percentage, size = 80, showLabel = false }: ProgressRingProps) {
  const strokeWidth = size >= 100 ? 8 : 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;
  const colorClass = getProgressColor(percentage);
  const bgClass = getProgressBgColor(percentage);

  const svg = (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className={bgClass}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className={`${colorClass} transition-all duration-500`}
      />
    </svg>
  );

  if (!showLabel) return svg;

  return (
    <div className="relative inline-flex items-center justify-center">
      {svg}
      <span className={`absolute font-bold ${size >= 100 ? "text-2xl" : "text-xs"}`}>
        {Math.round(percentage)}%
      </span>
    </div>
  );
}
