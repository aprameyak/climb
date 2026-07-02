import { clsx } from 'clsx';
import type { ReactNode } from 'react';

type Variant = 'default' | 'highlighted' | 'crux';

interface CardProps {
  variant?: Variant;
  header?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}

const variantClasses: Record<Variant, string> = {
  default: 'bg-surface-card border border-slate-700/50',
  highlighted: 'bg-slate-800 border border-accent-500/50 shadow-lg shadow-accent-500/10',
  crux: 'bg-slate-800 border border-red-500/50 shadow-lg shadow-red-500/10',
};

export function Card({ variant = 'default', header, footer, children, className, onClick }: CardProps) {
  return (
    <div
      className={clsx(
        'rounded-xl overflow-hidden',
        variantClasses[variant],
        onClick && 'cursor-pointer hover:border-slate-500 transition-colors',
        className
      )}
      onClick={onClick}
    >
      {header && (
        <div className="px-4 py-3 border-b border-slate-700/50 bg-slate-800/50">
          {header}
        </div>
      )}
      <div className="p-4">{children}</div>
      {footer && (
        <div className="px-4 py-3 border-t border-slate-700/50 bg-slate-800/30">
          {footer}
        </div>
      )}
    </div>
  );
}
