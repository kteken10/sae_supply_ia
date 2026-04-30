import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowUpRight,
  Boxes,
  Layers,
  Activity,
  TrendingUp,
} from "lucide-react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  PageLoader,
} from "../components/ui";
import { PageHeader } from "../components/PageHeader";
import { kpisApi, stockApi, recosApi } from "../api/client";
import { useNow } from "../context/NowContext";

const STATUS_COLORS = {
  ok: "#0f172a",
  rupture: "#f97316",
  surstock: "#94a3b8",
};

function MiniStat({ icon: Icon, label, value, sub, accent, to }) {
  const Wrapper = to ? Link : "div";
  const props = to ? { to } : {};
  return (
    <Wrapper
      {...props}
      className={`group flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 transition-all ${
        to ? "hover:border-slate-300 hover:shadow-sm" : ""
      }`}
    >
      <div
        className={`p-2 rounded-lg ${
          accent ? "bg-accent-50 text-accent-700" : "bg-slate-100 text-slate-700"
        }`}
      >
        <Icon className="w-4 h-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[11px] text-slate-500 uppercase tracking-wider leading-tight">
          {label}
        </div>
        <div className="text-xl font-bold text-slate-900 leading-tight mt-0.5 tabular-nums">
          {value}
        </div>
        {sub && (
          <div className="text-[11px] text-slate-500 mt-0.5">{sub}</div>
        )}
      </div>
      {to && (
        <ArrowUpRight className="w-4 h-4 text-slate-300 group-hover:text-accent-600 transition-colors" />
      )}
    </Wrapper>
  );
}

function HeroCard({ kpis }) {
  const taux = Math.round((kpis?.taux_service ?? 0) * 100);
  return (
    <Card className="lg:col-span-2 bg-slate-900 border-slate-900 text-white overflow-hidden relative">
      <div className="absolute -right-10 -top-10 w-48 h-48 rounded-full bg-accent-500/20 blur-2xl" />
      <div className="absolute -left-5 -bottom-5 w-32 h-32 rounded-full bg-accent-500/10 blur-xl" />
      <CardContent className="py-6 relative">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs uppercase tracking-wider text-white/50">
              SKU sous surveillance
            </div>
            <div className="text-5xl font-bold mt-1 tabular-nums">
              {kpis?.ruptures ?? 0}
            </div>
            <div className="text-sm text-white/70 mt-1 tabular-nums">
              sur {kpis?.skus_total ?? 0} SKU * {kpis?.surstocks ?? 0}{" "}
              surstocks
            </div>
          </div>
          <Link
            to="/forecast"
            className="inline-flex items-center gap-1.5 rounded-lg bg-accent-500 hover:bg-accent-600 px-3 py-1.5 text-xs font-medium shadow-sm shadow-accent-500/40"
          >
            Recommandations <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <div className="mt-5">
          <div className="flex justify-between text-[11px] text-white/60 mb-1.5">
            <span>Taux de service</span>
            <span className="font-medium text-white/90 tabular-nums">{taux}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full bg-accent-500 rounded-full transition-all"
              style={{ width: `${taux}%` }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatusDonut({ kpis }) {
  const data = [
    { status: "ok", count: kpis?.status?.ok ?? 0, fill: STATUS_COLORS.ok },
    {
      status: "rupture",
      count: kpis?.status?.rupture ?? 0,
      fill: STATUS_COLORS.rupture,
    },
    {
      status: "surstock",
      count: kpis?.status?.surstock ?? 0,
      fill: STATUS_COLORS.surstock,
    },
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Statut des SKU</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
          <ResponsiveContainer width={100} height={100}>
            <PieChart>
              <Pie
                data={data}
                dataKey="count"
                innerRadius={28}
                outerRadius={48}
                paddingAngle={2}
              >
                {data.map((d, i) => (
                  <Cell key={i} fill={d.fill} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="flex-1 space-y-1.5">
            {data.map((d) => (
              <div key={d.status} className="flex items-center gap-2 text-xs">
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: d.fill }}
                />
                <span className="text-slate-500 capitalize flex-1">
                  {d.status}
                </span>
                <span className="font-medium text-slate-900 tabular-nums">
                  {d.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CATimeseries({ data }) {
  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle>Chiffre d'affaires mensuel</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data}>
            <XAxis
              dataKey="month"
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              tickFormatter={(v) => v.slice(0, 7)}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
              tickFormatter={(v) => `${(v / 1e6).toFixed(1)}M`}
            />
            <Tooltip
              contentStyle={{
                background: "white",
                border: "1px solid #e2e8f0",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "#0f172a", fontWeight: 600 }}
              formatter={(v) => [`${(v / 1e6).toFixed(2)} M EUR`, "CA"]}
            />
            <Line
              type="monotone"
              dataKey="ca"
              stroke="#f97316"
              strokeWidth={2}
              dot={{ r: 3, fill: "#f97316" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function AlertsStrip({ alerts }) {
  if (!alerts?.length)
    return (
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          A surveiller
        </span>
        <span className="text-xs text-slate-500">Aucune alerte critique</span>
      </div>
    );
  const critical = alerts.filter((a) => a.urgence === "critical").length;
  const high = alerts.filter((a) => a.urgence === "high").length;
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        A surveiller
      </span>
      {critical > 0 && (
        <Link
          to="/forecast"
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-800 hover:border-rose-300"
        >
          <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
          {critical} rupture{critical > 1 ? "s" : ""} imminente{critical > 1 ? "s" : ""}
        </Link>
      )}
      {high > 0 && (
        <Link
          to="/forecast"
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-800 hover:border-amber-300"
        >
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
          {high} couverture{high > 1 ? "s" : ""} {"<"} 5 jours
        </Link>
      )}
      <Link
        to="/forecast"
        className="text-xs text-accent-700 hover:text-accent-800 ml-auto"
      >
        Voir tout {"->"}
      </Link>
    </div>
  );
}

function AlertsList({ alerts }) {
  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle>SKU les plus critiques</CardTitle>
      </CardHeader>
      <CardContent className="px-0 py-0">
        {!alerts?.length ? (
          <div className="px-5 py-10 text-center text-sm text-slate-500">
            Aucune alerte sur le perimetre selectionne
          </div>
        ) : (
          <ul>
            {alerts.slice(0, 8).map((a, i) => (
              <li
                key={`${a.store_id}-${a.product_id}-${i}`}
                className="flex items-center gap-3 px-5 py-3 border-t border-slate-100 first:border-t-0 hover:bg-slate-50"
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    a.urgence === "critical"
                      ? "bg-rose-500"
                      : a.urgence === "high"
                      ? "bg-amber-500"
                      : "bg-slate-400"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-slate-900 truncate">
                    {a.product_name}{" "}
                    <span className="font-mono text-xs text-slate-500">
                      {a.product_id}
                    </span>{" "}
                    - {a.store_city}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    Stock <span className="tabular-nums">{a.stock_actuel}</span>{" "}
                    / seuil min{" "}
                    <span className="tabular-nums">{a.seuil_min}</span> *
                    couverture{" "}
                    <span className="tabular-nums">{a.jours_couverture}j</span>
                  </div>
                </div>
                <Badge
                  tone={
                    a.urgence === "critical"
                      ? "danger"
                      : a.urgence === "high"
                      ? "warning"
                      : "neutral"
                  }
                >
                  {a.urgence}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function CategoryBreakdown({ kpis }) {
  const data = kpis?.by_categorie ?? [];
  const total = data.reduce((s, d) => s + d.skus, 0) || 1;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Par categorie</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {data.map((d, i) => {
            const pct = (d.ruptures / Math.max(d.skus, 1)) * 100;
            return (
              <li key={d.categorie} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-700 truncate">{d.categorie}</span>
                  <span className="text-slate-500 tabular-nums">
                    {d.ruptures} / {d.skus}
                  </span>
                </div>
                <div className="h-1 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className={
                      i === 0 || d.ruptures === Math.max(...data.map((x) => x.ruptures))
                        ? "h-full bg-accent-500"
                        : "h-full bg-slate-700"
                    }
                    style={{ width: `${Math.max(pct, 4)}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { now } = useNow();
  const kpisQ = useQuery({ queryKey: ["kpis", now], queryFn: () => kpisApi.overview(now) });
  const tsQ = useQuery({ queryKey: ["kpis_ts", now], queryFn: () => kpisApi.timeseries(now) });
  const alertsQ = useQuery({
    queryKey: ["alerts", now],
    queryFn: () => stockApi.alerts(now, 10),
  });
  const recosQ = useQuery({
    queryKey: ["recos_count", now],
    queryFn: () => recosApi.list(now, 5),
  });

  if (kpisQ.isLoading || tsQ.isLoading || alertsQ.isLoading) return <PageLoader />;
  const kpis = kpisQ.data;
  const series = tsQ.data?.series ?? [];
  const alerts = alertsQ.data?.alerts ?? [];

  const fmtMoney = (v) =>
    v >= 1e6 ? `${(v / 1e6).toFixed(1)} M EUR` : `${(v / 1e3).toFixed(0)} k EUR`;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pilotage prescriptif"
        description={`Vue consolidee a la date "${now}". Recommandations IA + supervision humaine.`}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <HeroCard kpis={kpis} />
        <StatusDonut kpis={kpis} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MiniStat
          icon={Boxes}
          label="SKU suivis"
          value={kpis?.skus_total ?? 0}
          sub="8 magasins x 10 produits"
        />
        <MiniStat
          icon={AlertTriangle}
          label="Recos a valider"
          value={recosQ.data?.count ?? 0}
          sub="actions prescriptives"
          accent
          to="/forecast"
        />
        <MiniStat
          icon={TrendingUp}
          label="Marge 3M"
          value={fmtMoney(kpis?.marge_3m ?? 0)}
          sub={`${Math.round((kpis?.taux_marge_3m ?? 0) * 100)}% de marge`}
        />
        <MiniStat
          icon={Activity}
          label="Taux service"
          value={`${Math.round((kpis?.taux_service ?? 0) * 100)}%`}
          sub={`vs taux rupture 3M ${Math.round((kpis?.taux_rupture_3m ?? 0) * 100)}%`}
        />
      </div>

      <AlertsStrip alerts={alerts} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <CATimeseries data={series} />
        <CategoryBreakdown kpis={kpis} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <AlertsList alerts={alerts} />
        <Card>
          <CardHeader>
            <CardTitle>Conformite IA Act</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-xs">
              {[
                "Tracabilite des decisions",
                "Documentation technique",
                "Supervision humaine obligatoire",
                "Transparence des recommandations",
                "Metriques retournees a chaque appel",
              ].map((t) => (
                <li key={t} className="flex items-start gap-2">
                  <Layers className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                  <span className="text-slate-700">{t}</span>
                </li>
              ))}
            </ul>
            <Link
              to="/audit"
              className="inline-flex items-center gap-1 text-xs text-accent-700 hover:text-accent-800 mt-4"
            >
              Voir le journal d'audit{" "}
              <ArrowUpRight className="w-3 h-3" />
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
