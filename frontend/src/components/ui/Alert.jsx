import React from 'react';
import { cn } from '../../utils/cn';

const VARIANTS = {
  error: 'bg-rose-50 border-rose-200 text-rose-800',
  success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
};

const ICONS = {
  error: '⚠️',
  success: '✓',
  warning: '⚠️',
  info: 'ℹ️',
};

export function Alert({
  variant = 'info',
  title,
  children,
  onDismiss,
  className,
}) {
  return (
    <div
      role="alert"
      className={cn(
        'p-4 rounded-xl border text-sm flex items-start justify-between gap-3 shadow-xs',
        VARIANTS[variant] || VARIANTS.info,
        className
      )}
    >
      <div className="flex items-start gap-2.5">
        <span className="text-base select-none mt-0.5">{ICONS[variant] || 'ℹ️'}</span>
        <div>
          {title && <p className="font-semibold mb-0.5">{title}</p>}
          <div className="leading-relaxed">{children}</div>
        </div>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="text-xs font-semibold opacity-70 hover:opacity-100 transition-opacity p-1 -mr-1"
          aria-label="Dismiss alert"
        >
          ✕
        </button>
      )}
    </div>
  );
}

export default Alert;
