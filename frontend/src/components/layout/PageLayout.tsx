import type { ReactNode } from 'react';
import { Header } from './Header';

interface PageLayoutProps {
  children: ReactNode;
  title?: string;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '7xl' | 'full';
}

const maxWidthMap = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  '7xl': 'max-w-7xl',
  full: 'max-w-full',
};

export function PageLayout({ children, title, maxWidth = '7xl' }: PageLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header />
      <main className={`mx-auto px-4 sm:px-6 lg:px-8 py-6 ${maxWidthMap[maxWidth]}`}>
        {title && (
          <h1 className="text-2xl font-bold text-white mb-6">{title}</h1>
        )}
        {children}
      </main>
    </div>
  );
}
