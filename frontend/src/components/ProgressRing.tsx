interface ProgressRingProps {
  percentage: number;
  size?: number;
  showLabel?: boolean;
}

export function ProgressRing({ percentage, size = 80, showLabel = false }: ProgressRingProps) {
  const strokeWidth = size >= 100 ? 8 : 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  const svg = (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-primary/20"
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
        className="text-primary transition-all duration-500"
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
