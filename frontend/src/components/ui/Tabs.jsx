import * as TabsPrimitive from "@radix-ui/react-tabs";
import { forwardRef } from "react";
import { cn } from "../../lib/cn";

export const Tabs = TabsPrimitive.Root;

export const TabsList = forwardRef(function TabsList({ className, ...props }, ref) {
  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        "inline-flex bg-slate-100 p-1 rounded-lg gap-1",
        className
      )}
      {...props}
    />
  );
});

export const TabsTrigger = forwardRef(function TabsTrigger({ className, ...props }, ref) {
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "px-3 py-1.5 rounded-md text-xs font-medium text-slate-600 transition-colors data-[state=active]:bg-white data-[state=active]:text-accent-700 data-[state=active]:shadow-sm",
        className
      )}
      {...props}
    />
  );
});

export const TabsContent = forwardRef(function TabsContent({ className, ...props }, ref) {
  return (
    <TabsPrimitive.Content
      ref={ref}
      className={cn("mt-4 focus:outline-none", className)}
      {...props}
    />
  );
});
