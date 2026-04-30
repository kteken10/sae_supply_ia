import { forwardRef } from "react";
import { cn } from "../../lib/cn";

export const Card = forwardRef(function Card({ className, ...props }, ref) {
  return (
    <div
      ref={ref}
      className={cn(
        "rounded-2xl border border-slate-200 bg-white shadow-sm",
        className
      )}
      {...props}
    />
  );
});

export const CardHeader = forwardRef(function CardHeader({ className, ...props }, ref) {
  return (
    <div ref={ref} className={cn("px-5 py-4 border-b border-slate-100", className)} {...props} />
  );
});

export const CardTitle = forwardRef(function CardTitle({ className, ...props }, ref) {
  return (
    <h3 ref={ref} className={cn("text-base font-semibold text-slate-900", className)} {...props} />
  );
});

export const CardDescription = forwardRef(function CardDescription({ className, ...props }, ref) {
  return (
    <p ref={ref} className={cn("text-sm text-slate-500 mt-1", className)} {...props} />
  );
});

export const CardContent = forwardRef(function CardContent({ className, ...props }, ref) {
  return <div ref={ref} className={cn("px-5 py-4", className)} {...props} />;
});

export const CardFooter = forwardRef(function CardFooter({ className, ...props }, ref) {
  return (
    <div
      ref={ref}
      className={cn("px-5 py-3 border-t border-slate-100 bg-slate-50/50 rounded-b-2xl", className)}
      {...props}
    />
  );
});
