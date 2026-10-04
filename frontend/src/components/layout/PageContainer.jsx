import React from 'react';
import { cn } from '../../utils/cn';

export function PageContainer({
  title,
  subtitle,
  action,
  children,
  className,
}) {
  return (
    <div className={cn('p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6', className)}>
      {/* Page Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="text-sm text-slate-500 mt-1">
              {subtitle}
            </p>
          )}
        </div>
        {action && (
          <div className="flex items-center gap-3 shrink-0">
            {action}
          </div>
        )}
      </div>

      {/* Main Page Content */}
      <div>{children}</div>
    </div>
  );
}
