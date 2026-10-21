import { getScoreColor } from '@/lib/utils';

interface ValidationScoreRingProps {
  score: number | null;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const sizeConfig = {
  sm: { svgSize: 80, strokeWidth: 7, textSize: 'text-lg', labelSize: 'text-xs' },
  md: { svgSize: 120, strokeWidth: 10, textSize: 'text-2xl', labelSize: 'text-xs' },
  lg: { svgSize: 160, strokeWidth: 12, textSize: 'text-4xl', labelSize: 'text-sm' },
};

export function ValidationScoreRing({
  score,
  size = 'md',
  showLabel = true,
}: ValidationScoreRingProps) {
  const { svgSize, strokeWidth, labelSize } = sizeConfig[size];
  const center = svgSize / 2;
  const radius = center - strokeWidth - 2;
  const circumference = 2 * Math.PI * radius;
  const safeScore = score ?? 0;
  const percentage = Math.min(Math.max(safeScore, 0), 100) / 100;
  const strokeDashoffset = circumference * (1 - percentage);
  const color = getScoreColor(score);

  const labelText =
    score === null
      ? 'N/A'
      : score >= 70
      ? 'Good'
      : score >= 40
      ? 'Average'
      : 'Poor';

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={svgSize} height={svgSize} viewBox={`0 0 ${svgSize} ${svgSize}`}>
        {/* Background track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          transform={`rotate(-90 ${center} ${center})`}
          style={{ transition: 'stroke-dashoffset 0.5s ease-in-out' }}
        />
        {/* Score text */}
        <text
          x="50%"
          y="50%"
          dominantBaseline="middle"
          textAnchor="middle"
          fill={score === null ? '#9CA3AF' : color}
          fontWeight="700"
          fontSize={size === 'lg' ? 36 : size === 'md' ? 28 : 20}
          fontFamily="Inter, system-ui, sans-serif"
        >
          {score === null ? 'N/A' : Math.round(safeScore)}
        </text>
      </svg>
      {showLabel && (
        <span
          className={`font-medium ${labelSize}`}
          style={{ color: score === null ? '#9CA3AF' : color }}
        >
          {labelText}
        </span>
      )}
      {showLabel && (
        <span className={`text-gray-400 ${labelSize} -mt-1`}>Validation Score</span>
      )}
    </div>
  );
}

// Inline score display for tables
export function ScorePill({ score }: { score: number | null }) {
  const color = getScoreColor(score);
  const bgColor =
    score === null
      ? '#F3F4F6'
      : score >= 70
      ? '#F0FDF4'
      : score >= 40
      ? '#FFFBEB'
      : '#FEF2F2';

  return (
    <span
      className="inline-flex items-center px-2.5 py-1 rounded-full text-sm font-bold"
      style={{ color, backgroundColor: bgColor }}
    >
      {score === null ? '—' : Math.round(score)}
    </span>
  );
}
