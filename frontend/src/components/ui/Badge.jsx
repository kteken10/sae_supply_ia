import { cn } from "../../lib/cn";

const TONES = {
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
  accent: "bg-accent-50 text-accent-700 ring-accent-200",
  success: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  warning: "bg-amber-50 text-amber-800 ring-amber-200",
  danger: "bg-rose-50 text-rose-700 ring-rose-200",
  mono: "bg-slate-900 text-white ring-slate-900",
};

export function Badge({ tone = "neutral", className, children, ...props }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium ring-1 ring-inset",
        TONES[tone],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
