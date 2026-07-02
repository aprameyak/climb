import { clsx } from 'clsx';
import { confidenceToColor, confidenceToLabel } from '@/utils/colors';

interface ConfidenceBarProps {
  value: number; // 0-1
  label?: string;
  showLabel?: boolean;
  showPercentage?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

export function ConfidenceBar({
  value,
  label,
  showLabel = true,
  showPercentage = true,
  size = 'md',
  className,
}: ConfidenceBarProps) {
  const color = confidenceToColor(value);
  const qualLabel = confidenceToLabel(value);
  const pct = Math.round(value * 100);

  return (
    <div className={clsx('flex flex-col gap-1', className)}>
      {(showLabel || showPercentage) && (
        <div className="flex items-center justify-between text-xs">
          {showLabel && (
            <span className="text-slate-400">{label ?? qualLabel}</span>
          )}
          {showPercentage && (
            <span className="font-mono font-semibold" style={{ color }}>
              {pct}%
            </span>
          )}
        </div>
      )}
      <div
        className={clsx(
          'w-full rounded-full bg-slate-700/50 overflow-hidden',
          size === 'sm' ? 'h-1.5' : 'h-2'
        )}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            backgroundColor: color,
            boxShadow: `0 0 6px ${color}40`,
          }}
        />
      </div>
    </div>
  );
}
