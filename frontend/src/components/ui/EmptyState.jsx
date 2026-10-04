import React from 'react';
import { cn } from '../../utils/cn';

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center p-8 sm:p-12 bg-white rounded-xl border border-dashed border-slate-300 shadow-sm max-w-2xl mx-auto',
        className
      )}
    >
      {icon && (
        <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-2xl text-emerald-700 mb-4 shadow-xs">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold text-slate-900 tracking-tight">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-slate-500 mt-1.5 max-w-md leading-relaxed">
          {description}
        </p>
      )}
      {action && (
        <div className="mt-6 flex items-center gap-3">
          {action}
        </div>
      )}
    </div>
  );
}
