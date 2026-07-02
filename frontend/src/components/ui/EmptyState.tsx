import type { ReactNode } from 'react';
import { clsx } from 'clsx';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center gap-4 py-16 px-8 text-center',
        className
      )}
    >
      {icon && (
        <div className="text-slate-600 opacity-60">{icon}</div>
      )}
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-slate-300">{title}</h3>
        {description && (
          <p className="text-sm text-slate-500 max-w-sm">{description}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
