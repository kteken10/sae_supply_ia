import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Area,
  ComposedChart,
} from "recharts";
import {
  CheckCircle2,
  ShieldAlert,
  Truck,
  Package,
  Building2,
  ArrowRight,
  AlertTriangle,
  Sparkles,
  Coins,
} from "lucide-react";
import { toast } from "sonner";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
  Button,
  Badge,
  Select,
  PageLoader,
  EmptyState,
} from "../components/ui";
import { PageHeader } from "../components/PageHeader";
import {
  catalogApi,
  recosApi,
  forecastApi,
} from "../api/client";
import { useNow } from "../context/NowContext";

function ForecastChart({ history, forecast }) {
  const merged = useMemo(() => {
    const h = (history || []).map((p) => ({
      date: p.date,
      historique: p.qty,
    }));
    const f = (forecast || []).map((p) => ({
      date: p.date,
      forecast: p.qty_pred,
      lower: p.lower,
      upper: p.upper,
    }));
    // Pour rendre l'aire de confiance, on stocke `range = [lower, upper]`
    return [...h, ...f].map((row) =>
      row.lower !== undefined
        ? { ...row, range: [row.lower, row.upper] }
        : row
    );
  }, [history, forecast]);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={merged}>
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: "#94a3b8" }}
          axisLine={{ stroke: "#e2e8f0" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#94a3b8" }}
          axisLine={{ stroke: "#e2e8f0" }}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "white",
            border: "1px solid #e2e8f0",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: "#0f172a", fontWeight: 600 }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Area
          dataKey="range"
          stroke="none"
          fill="#f97316"
          fillOpacity={0.12}
          name="Intervalle 80%"
        />
        <Line
          type="monotone"
          dataKey="historique"
          stroke="#0f172a"
          strokeWidth={2}
          dot={false}
          name="Demande observee"
        />
        <Line
          type="monotone"
          dataKey="forecast"
          stroke="#f97316"
          strokeWidth={2.5}
          strokeDasharray="4 3"
          dot={{ r: 3, fill: "#f97316" }}
          name="Forecast"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function RecommendationCard({ store_id, product_id, now, onValidated }) {
  const qc = useQueryClient();
  const recoQ = useQuery({
    queryKey: ["reco_one", store_id, product_id, now],
    queryFn: () => recosApi.one(store_id, product_id, now),
    enabled: !!store_id && !!product_id,
  });

  const validate = useMutation({
    mutationFn: (decision) =>
      recosApi.validate({
        store_id,
        product_id,
        qty_recommandee: recoQ.data.qty_recommandee,
        fournisseur_id: recoQ.data.fournisseur?.supplier_id,
        decision,
        user: "operateur_demo",
      }),
    onSuccess: (_, decision) => {
      toast.success(
        decision === "validated"
          ? "Recommandation validee. Tracee dans l'audit."
          : "Recommandation rejetee. Tracee dans l'audit."
      );
      qc.invalidateQueries({ queryKey: ["audit"] });
      onValidated?.();
    },
    onError: () => toast.error("Erreur lors de la validation"),
  });

  if (recoQ.isLoading) return <PageLoader />;
  if (recoQ.isError || !recoQ.data) return null;

  const r = recoQ.data;
  const urgenceTone =
    r.urgence === "critical"
      ? "danger"
      : r.urgence === "high"
      ? "warning"
      : "neutral";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              {r.product_name}
              <span className="font-mono text-xs text-slate-500">
                {r.product_id}
              </span>
            </CardTitle>
            <CardDescription>
              {r.store_city} ({r.store_id}) * {r.categorie}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone={urgenceTone}>Urgence : {r.urgence}</Badge>
            <Badge
              tone={
                r.confidence === "high"
                  ? "success"
                  : r.confidence === "medium"
                  ? "warning"
                  : "neutral"
              }
            >
              Confiance : {r.confidence}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <div className="rounded-xl border border-slate-200 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wider text-slate-400">
              Stock
            </div>
            <div className="text-lg font-bold text-slate-900 tabular-nums">
              {r.stock_actuel}
            </div>
            <div className="text-[11px] text-slate-500">
              seuil min {r.seuil_min}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wider text-slate-400">
              Couverture
            </div>
            <div className="text-lg font-bold text-slate-900 tabular-nums">
              {r.jours_avant_rupture}j
            </div>
            <div className="text-[11px] text-slate-500">
              avant rupture estimee
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wider text-slate-400">
              Forecast 4S
            </div>
            <div className="text-lg font-bold text-slate-900 tabular-nums">
              {r.forecast_qty_4w}
            </div>
            <div className="text-[11px] text-slate-500">unites prevues</div>
          </div>
          <div className="rounded-xl border border-accent-200 bg-accent-50 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wider text-accent-700">
              Quantite reco
            </div>
            <div className="text-lg font-bold text-accent-900 tabular-nums">
              {r.qty_recommandee}
            </div>
            <div className="text-[11px] text-accent-700">a commander</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          {r.fournisseur && (
            <div className="rounded-xl border border-slate-200 px-4 py-3">
              <div className="text-[11px] uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Building2 className="w-3 h-3" /> Meilleur fournisseur
                {r.fournisseur.tier && (
                  <Badge tone={r.fournisseur.tier === "Premium" ? "success" : r.fournisseur.tier === "Discount" ? "warning" : "neutral"} className="ml-1">
                    {r.fournisseur.tier}
                  </Badge>
                )}
                {r.fournisseur.is_synthetic && (
                  <span className="inline-flex items-center gap-0.5 text-[10px] text-accent-700">
                    <Sparkles className="w-2.5 h-2.5" /> synth
                  </span>
                )}
              </div>
              <div className="text-sm font-semibold text-slate-900 mt-1">
                {r.fournisseur.supplier_name}{" "}
                <span className="font-mono text-xs text-slate-500">
                  {r.fournisseur.supplier_id}
                </span>
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {r.fournisseur.pays_origine} * delai prevu{" "}
                <span className="tabular-nums">
                  {r.fournisseur.delai_prevu_moy}j
                </span>{" "}
                * retard moy{" "}
                <span className="tabular-nums">{r.fournisseur.retard_moy}j</span>{" "}
                * conformite{" "}
                <span className="tabular-nums">
                  {Math.round(r.fournisseur.pct_conforme * 100)}%
                </span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Score :{" "}
                <span className="font-semibold text-accent-700 tabular-nums">
                  {r.fournisseur.score.toFixed(2)}
                </span>
              </div>
              {r.fournisseur_alt && (
                <div className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100">
                  <span className="text-slate-400">Alternative :</span>{" "}
                  <span className="text-slate-700">{r.fournisseur_alt.supplier_name}</span>
                  {r.fournisseur_alt.tier && <span className="text-slate-400"> ({r.fournisseur_alt.tier})</span>}
                  <span className="text-slate-500"> - score{" "}
                    <span className="font-medium tabular-nums">{r.fournisseur_alt.score.toFixed(2)}</span>
                  </span>
                </div>
              )}
            </div>
          )}

          {r.lane && (
            <div className="rounded-xl border border-slate-200 px-4 py-3">
              <div className="text-[11px] uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Truck className="w-3 h-3" /> Circuit logistique optimal
              </div>
              <div className="text-sm font-semibold text-slate-900 mt-1 flex items-center gap-1.5 flex-wrap">
                {r.lane.from} <ArrowRight className="w-3 h-3 text-slate-400" />{" "}
                {r.lane.to}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {r.lane.type_flux} * duree{" "}
                <span className="tabular-nums">{r.lane.duree_moy_j}j</span> *
                cout unitaire{" "}
                <span className="tabular-nums">
                  {r.lane.cout_unitaire_moy.toFixed(2)} EUR
                </span>{" "}
                * incidents{" "}
                <span className="tabular-nums">
                  {Math.round(r.lane.taux_incident * 100)}%
                </span>
              </div>
            </div>
          )}
        </div>

        {r.capacity_warning && (
          <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 mb-3 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-900">{r.capacity_warning}</div>
          </div>
        )}

        <div className="rounded-xl bg-slate-50 border border-slate-100 px-4 py-3 mb-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 flex items-center gap-1.5 mb-1">
            <ShieldAlert className="w-3 h-3" /> Raison de la recommandation
          </div>
          <div className="text-sm text-slate-700">{r.raison}</div>
          {r.cout_stockage_evite != null && (
            <div className="text-[11px] text-slate-600 mt-2 flex items-center gap-1.5">
              <Coins className="w-3 h-3 text-emerald-600" />
              Cout d'opportunite estime :{" "}
              <span className="font-semibold text-slate-900 tabular-nums">
                {r.cout_stockage_evite.toFixed(2)} EUR
              </span>{" "}
              en cas de rupture (1 semaine de surcout d'urgence)
            </div>
          )}
          {r.enrichments_used && r.enrichments_used.length > 0 && (
            <div className="text-[10px] text-slate-500 mt-2 pt-2 border-t border-slate-100 flex items-start gap-1.5">
              <Sparkles className="w-2.5 h-2.5 text-accent-500 flex-shrink-0 mt-0.5" />
              <span>
                Enrichissements utilises :{" "}
                {r.enrichments_used.map((e) => (
                  <span key={e} className="inline-block bg-accent-50 text-accent-700 px-1.5 py-0.5 rounded mr-1">
                    {e}
                  </span>
                ))}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => validate.mutate("rejected")}
            disabled={validate.isPending}
          >
            Rejeter
          </Button>
          <Button
            variant="accent"
            size="sm"
            onClick={() => validate.mutate("validated")}
            loading={validate.isPending}
          >
            <CheckCircle2 className="w-3.5 h-3.5" /> Valider la recommandation
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ForecastPage() {
  const { now } = useNow();
  const metaQ = useQuery({ queryKey: ["meta"], queryFn: catalogApi.meta });
  const recosQ = useQuery({
    queryKey: ["recos", now],
    queryFn: () => recosApi.list(now, 30),
  });

  const [storeId, setStoreId] = useState(null);
  const [productId, setProductId] = useState(null);

  const fcQ = useQuery({
    queryKey: ["forecast", storeId, productId, now],
    queryFn: () => forecastApi.get(storeId, productId, now, 4),
    enabled: !!storeId && !!productId,
  });

  if (metaQ.isLoading || recosQ.isLoading) return <PageLoader />;
  const meta = metaQ.data;
  const recos = recosQ.data?.recommendations ?? [];

  const selected = recos.find(
    (r) => r.store_id === storeId && r.product_id === productId
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Forecast & Recommandations"
        description={`${recos.length} action${recos.length > 1 ? "s" : ""} prescriptive${recos.length > 1 ? "s" : ""} a la date "${now}"`}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-1 max-h-[70vh] overflow-y-auto">
          <CardHeader>
            <CardTitle>SKU a risque</CardTitle>
            <CardDescription>
              Tries par urgence. Cliquer pour voir le forecast et la
              recommandation.
            </CardDescription>
          </CardHeader>
          <CardContent className="px-0 py-0">
            {!recos.length ? (
              <EmptyState
                icon={Package}
                title="Aucune alerte"
                description="Pas de SKU sous le seuil critique a la date selectionnee."
              />
            ) : (
              <ul>
                {recos.map((r) => {
                  const active =
                    r.store_id === storeId && r.product_id === productId;
                  return (
                    <li
                      key={`${r.store_id}-${r.product_id}`}
                      className={`flex items-center gap-3 px-5 py-3 border-t border-slate-100 first:border-t-0 cursor-pointer transition-colors ${
                        active
                          ? "bg-accent-50/60"
                          : "hover:bg-slate-50"
                      }`}
                      onClick={() => {
                        setStoreId(r.store_id);
                        setProductId(r.product_id);
                      }}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                          r.urgence === "critical"
                            ? "bg-rose-500"
                            : r.urgence === "high"
                            ? "bg-amber-500"
                            : "bg-slate-400"
                        }`}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-slate-900 truncate">
                          {r.product_name} - {r.store_city}
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5 tabular-nums">
                          stock {r.stock_actuel} / seuil {r.seuil_min} *{" "}
                          {r.jours_avant_rupture}j
                        </div>
                      </div>
                      <div className="text-xs font-semibold text-accent-700 tabular-nums">
                        +{r.qty_recommandee}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <CardTitle>Demande historique vs forecast 4 semaines</CardTitle>
                  <CardDescription>
                    Modele : RandomForest (lags + saisonnalite + promo)
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Select
                    value={storeId || ""}
                    onChange={(e) => setStoreId(e.target.value || null)}
                    className="w-32"
                  >
                    <option value="">Magasin</option>
                    {meta.stores.map((s) => (
                      <option key={s.store_id} value={s.store_id}>
                        {s.store_id} - {s.store_city}
                      </option>
                    ))}
                  </Select>
                  <Select
                    value={productId || ""}
                    onChange={(e) => setProductId(e.target.value || null)}
                    className="w-44"
                  >
                    <option value="">Produit</option>
                    {meta.products.map((p) => (
                      <option key={p.product_id} value={p.product_id}>
                        {p.product_id} - {p.product_name}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {!storeId || !productId ? (
                <EmptyState
                  icon={Package}
                  title="Selection requise"
                  description="Choisissez un magasin et un produit (ou cliquez une ligne dans la liste de gauche) pour afficher le forecast."
                />
              ) : fcQ.isLoading ? (
                <PageLoader />
              ) : fcQ.data ? (
                <>
                  <ForecastChart
                    history={fcQ.data.history}
                    forecast={fcQ.data.forecast}
                  />
                  <div className="flex items-center justify-end gap-3 mt-3 text-[11px] text-slate-500 tabular-nums">
                    <span>
                      MAPE :{" "}
                      <span className="font-medium text-slate-900">
                        {fcQ.data.metrics?.mape != null
                          ? `${(fcQ.data.metrics.mape * 100).toFixed(1)}%`
                          : "-"}
                      </span>
                    </span>
                    <span>
                      Confiance :{" "}
                      <span className="font-medium text-slate-900">
                        {fcQ.data.confidence}
                      </span>
                    </span>
                    <span>
                      Points historique :{" "}
                      <span className="font-medium text-slate-900">
                        {fcQ.data.n_train_points}
                      </span>
                    </span>
                  </div>
                </>
              ) : null}
            </CardContent>
          </Card>

          {storeId && productId && (
            <RecommendationCard
              store_id={storeId}
              product_id={productId}
              now={now}
              onValidated={() => recosQ.refetch()}
            />
          )}
        </div>
      </div>
    </div>
  );
}
