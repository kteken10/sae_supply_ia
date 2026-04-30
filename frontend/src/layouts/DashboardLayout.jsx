import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  TrendingUp,
  Truck,
  ShieldCheck,
  Menu,
  Activity,
  Sparkles,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useNow } from "../context/NowContext";
import { settingsApi } from "../api/client";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard", end: true },
  { to: "/forecast", icon: TrendingUp, label: "Forecast & Reco" },
  { to: "/suppliers", icon: Truck, label: "Fournisseurs" },
  { to: "/audit", icon: ShieldCheck, label: "Tracabilite IA Act" },
];

function SidebarLink({ to, icon: Icon, label, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `group relative flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? "bg-accent-500 text-white shadow-sm shadow-accent-500/30"
            : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        }`
      }
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      <span>{label}</span>
    </NavLink>
  );
}

function Sidebar({ onClose }) {
  return (
    <>
      <div className="px-5 py-5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="bg-slate-900 text-white rounded-lg p-1.5">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-900">
              SAE <span className="text-accent-600">Carrefour</span>
            </div>
            <div className="text-[11px] text-slate-500 leading-none mt-0.5">
              Pilotage prescriptif
            </div>
          </div>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 px-3 pb-2">
          Operations
        </p>
        <div className="space-y-1">
          {navItems.map((item) => (
            <div key={item.to} onClick={onClose}>
              <SidebarLink {...item} />
            </div>
          ))}
        </div>
      </nav>
      <div className="border-t border-slate-100 px-4 py-3 space-y-3">
        <EnrichmentToggle />
        <div>
          <div className="text-[11px] text-slate-500">MVP v0.2 - enrichi</div>
          <div className="text-[11px] text-slate-400 mt-0.5">RF + bootstrap + multi-fournisseurs</div>
        </div>
      </div>
    </>
  );
}

function EnrichmentToggle() {
  const qc = useQueryClient();
  const settingsQ = useQuery({
    queryKey: ["settings"],
    queryFn: settingsApi.get,
  });
  const mutate = useMutation({
    mutationFn: (val) => settingsApi.setUseEnriched(val),
    onSuccess: (data) => {
      toast.success(
        data.use_enriched
          ? "Enrichissements actives"
          : "Mode dataset original (10 fournisseurs)"
      );
      qc.invalidateQueries();
    },
  });
  if (!settingsQ.data?.has_enrichment_data) return null;
  const active = settingsQ.data?.use_enriched;
  return (
    <button
      type="button"
      onClick={() => mutate.mutate(!active)}
      disabled={mutate.isPending}
      className={`w-full flex items-center gap-2 rounded-lg px-3 py-2 text-xs transition-colors ${
        active
          ? "bg-accent-50 text-accent-800 hover:bg-accent-100 border border-accent-200"
          : "bg-slate-50 text-slate-700 hover:bg-slate-100 border border-slate-200"
      }`}
    >
      <Sparkles
        className={`w-3.5 h-3.5 flex-shrink-0 ${
          active ? "text-accent-600" : "text-slate-400"
        }`}
      />
      <span className="flex-1 text-left">
        Enrichissements
        <span className="block text-[10px] opacity-75">
          {active ? "synthetiques actifs" : "donnees originales"}
        </span>
      </span>
      <span
        className={`relative inline-flex h-4 w-7 rounded-full transition-colors ${
          active ? "bg-accent-500" : "bg-slate-300"
        }`}
      >
        <span
          className={`absolute top-0.5 h-3 w-3 rounded-full bg-white shadow-sm transition-transform ${
            active ? "translate-x-3.5" : "translate-x-0.5"
          }`}
        />
      </span>
    </button>
  );
}

function NowSelector() {
  const { now, setNow } = useNow();
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        Date "now"
      </span>
      <input
        type="date"
        value={now}
        min="2025-01-15"
        max="2025-12-29"
        onChange={(e) => setNow(e.target.value)}
        className="h-8 px-2 rounded-lg border border-slate-300 bg-white text-xs focus:outline-none focus:ring-2 focus:ring-accent-500/20"
      />
      <span className="inline-flex items-center gap-1.5 text-[11px] text-slate-500">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-500/60" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-500" />
        </span>
        live
      </span>
    </div>
  );
}

export function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  return (
    <div className="flex h-screen bg-slate-50">
      <aside className="hidden lg:flex lg:flex-col lg:w-64 bg-white border-r border-slate-200">
        <Sidebar />
      </aside>

      {sidebarOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="fixed inset-y-0 left-0 z-50 flex flex-col w-64 bg-white border-r border-slate-200 lg:hidden">
            <Sidebar onClose={() => setSidebarOpen(false)} />
          </aside>
        </>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <header className="lg:hidden flex items-center justify-between gap-3 px-4 py-3 bg-white border-b border-slate-200">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg text-slate-700 hover:bg-slate-100"
          >
            <Menu className="w-5 h-5" />
          </button>
          <NowSelector />
        </header>

        <header className="hidden lg:flex items-center justify-end gap-3 px-8 py-3 bg-white border-b border-slate-200">
          <NowSelector />
        </header>

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-[1600px] mx-auto w-full">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
