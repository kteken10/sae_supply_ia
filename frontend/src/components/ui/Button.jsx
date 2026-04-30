import { forwardRef } from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "../../lib/cn";

const variants = {
  primary: "bg-slate-900 text-white hover:bg-slate-800 disabled:bg-slate-400",
  accent: "bg-accent-500 text-white hover:bg-accent-600 disabled:bg-accent-300",
  secondary:
    "bg-white text-slate-900 border border-slate-300 hover:bg-slate-50 hover:border-slate-400",
  outline:
    "bg-transparent border border-slate-300 text-slate-700 hover:border-accent-500 hover:text-accent-700",
  ghost:
    "bg-transparent text-slate-700 hover:bg-slate-100 hover:text-accent-700",
  danger: "bg-rose-600 text-white hover:bg-rose-700 disabled:bg-rose-300",
};

const sizes = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-11 px-5 text-base",
  icon: "h-9 w-9",
};

const base =
  "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/40 focus-visible:ring-offset-1 disabled:cursor-not-allowed";

export const Button = forwardRef(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    asChild = false,
    className,
    children,
    disabled,
    ...props
  },
  ref
) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      ref={ref}
      disabled={disabled || loading}
      className={cn(base, variants[variant], sizes[size], className)}
      {...props}
    >
      {loading ? (
        <>
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-r-transparent" />
          Chargement...
        </>
      ) : (
        children
      )}
    </Comp>
  );
});
