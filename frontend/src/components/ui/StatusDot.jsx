import { cn } from "../../lib/cn";

const COLORS = {
  ok: "bg-emerald-500",
  active: "bg-emerald-500",
  rupture: "bg-rose-500",
  critical: "bg-rose-500",
  surstock: "bg-amber-500",
  high: "bg-rose-500",
  medium: "bg-amber-500",
  low: "bg-slate-400",
  pending: "bg-amber-500",
  validated: "bg-emerald-500",
  rejected: "bg-rose-500",
};

export function StatusDot({ status, label, className }) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full flex-shrink-0",
          COLORS[status] || "bg-slate-400"
        )}
      />
      {label !== undefined && (
        <span className="text-xs text-slate-700 capitalize">{label || status}</span>
      )}
    </span>
  );
}
