import { forwardRef } from "react";
import { cn } from "../../lib/cn";

export const Input = forwardRef(function Input(
  { className, error, ...props },
  ref
) {
  return (
    <input
      ref={ref}
      className={cn(
        "w-full h-10 px-3 rounded-lg border bg-white text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2",
        error
          ? "border-rose-300 focus:border-rose-400 focus:ring-rose-500/30"
          : "border-slate-300 focus:border-slate-400 focus:ring-accent-500/20",
        className
      )}
      {...props}
    />
  );
});

export function FormField({ label, htmlFor, error, hint, children }) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label
          htmlFor={htmlFor}
          className="text-[11px] font-semibold uppercase tracking-wider text-slate-500"
        >
          {label}
        </label>
      )}
      {children}
      {error ? (
        <p className="text-xs text-rose-600">{error}</p>
      ) : hint ? (
        <p className="text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  );
}

export const Select = forwardRef(function Select({ className, children, ...props }, ref) {
  return (
    <select
      ref={ref}
      className={cn(
        "w-full h-10 px-3 pr-9 rounded-lg border border-slate-300 bg-white text-sm appearance-none focus:outline-none focus:ring-2 focus:border-slate-400 focus:ring-accent-500/20",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
});

export const Textarea = forwardRef(function Textarea({ className, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={cn(
        "w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:border-slate-400 focus:ring-accent-500/20",
        className
      )}
      {...props}
    />
  );
});
