import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  label?: string;
  className?: string;
  fullscreen?: boolean;
}

const sizeMap = { sm: 16, md: 24, lg: 36, xl: 48 };

export function LoadingSpinner({
  size = 'md',
  label,
  className,
  fullscreen = false,
}: LoadingSpinnerProps) {
  const content = (
    <div className={clsx('flex flex-col items-center gap-3', className)}>
      <Loader2
        className="animate-spin text-accent-500"
        size={sizeMap[size]}
      />
      {label && (
        <p className="text-sm text-slate-400 animate-pulse">{label}</p>
      )}
    </div>
  );

  if (fullscreen) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-slate-900/80 backdrop-blur-sm z-50">
        {content}
      </div>
    );
  }

  return content;
}
