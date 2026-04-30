import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Truck, Search, Sparkles } from "lucide-react";
import {
  Card,
  Badge,
  Input,
  PageLoader,
  EmptyState,
  Button,
} from "../components/ui";
import { PageHeader } from "../components/PageHeader";
import { suppliersApi } from "../api/client";

function ScoreBar({ score, isTop }) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-20 rounded-full bg-slate-100 overflow-hidden">
        <div
          className={`h-full ${isTop ? "bg-accent-500" : "bg-slate-700"}`}
          style={{ width: `${Math.max(pct, 4)}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-slate-900 tabular-nums w-9 text-right">
        {score.toFixed(2)}
      </span>
    </div>
  );
}

export default function SuppliersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["suppliers"],
    queryFn: suppliersApi.list,
  });
  const [q, setQ] = useState("");

  if (isLoading) return <PageLoader />;
  const all = data?.suppliers ?? [];
  const filtered = q
    ? all.filter(
        (s) =>
          s.supplier_name.toLowerCase().includes(q.toLowerCase()) ||
          s.pays_origine.toLowerCase().includes(q.toLowerCase()) ||
          s.product_name.toLowerCase().includes(q.toLowerCase())
      )
    : all;
  const topScore = all[0]?.score ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Fournisseurs"
        description="Scoring fiabilite x ponctualite x conformite. Le score est utilise pour selectionner automatiquement le meilleur fournisseur dans chaque recommandation."
      />

      <div className="flex gap-2 items-center flex-wrap">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Chercher un fournisseur, pays, produit..."
            className="pl-9"
          />
        </div>
        {q && (
          <Button variant="ghost" size="sm" onClick={() => setQ("")}>
            Reset
          </Button>
        )}
        <span className="text-xs text-slate-500 ml-auto tabular-nums">
          {filtered.length} / {all.length}
        </span>
      </div>

      {!filtered.length ? (
        <EmptyState
          icon={Truck}
          title="Aucun fournisseur"
          description="Ajustez votre filtre."
        />
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3 text-left font-semibold w-12">#</th>
                <th className="px-5 py-3 text-left font-semibold">
                  Fournisseur
                </th>
                <th className="px-5 py-3 text-left font-semibold">Produit</th>
                <th className="px-5 py-3 text-left font-semibold">Score</th>
                <th className="px-5 py-3 text-left font-semibold">Delais</th>
                <th className="px-5 py-3 text-left font-semibold">Conformite</th>
                <th className="px-5 py-3 text-right font-semibold">CA total</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <tr
                  key={s.supplier_id}
                  className="border-t border-slate-100 hover:bg-slate-50"
                >
                  <td className="px-5 py-3 font-mono text-xs text-slate-500 tabular-nums">
                    {i + 1}
                  </td>
                  <td className="px-5 py-3">
                    <div className="font-medium text-slate-900 flex items-center gap-1.5">
                      {s.supplier_name}
                      {s.tier && s.tier !== "Incumbent" && (
                        <Badge
                          tone={
                            s.tier === "Premium"
                              ? "success"
                              : s.tier === "Discount"
                              ? "warning"
                              : "neutral"
                          }
                        >
                          {s.tier}
                        </Badge>
                      )}
                      {s.is_synthetic && (
                        <span title="Fournisseur synthetique - documente dans la model card">
                          <Sparkles className="w-3 h-3 text-accent-500" />
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-500 font-mono">
                      {s.supplier_id} * {s.pays_origine}
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <div className="text-slate-700">{s.product_name}</div>
                    <div className="text-[11px] text-slate-500 font-mono">
                      {s.product_id} * {s.categorie}
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <ScoreBar score={s.score} isTop={s.score === topScore} />
                  </td>
                  <td className="px-5 py-3 text-xs text-slate-700 tabular-nums">
                    prevu {s.delai_prevu_moy}j
                    <br />
                    <span className="text-slate-500">
                      reel {s.delai_reel_moy}j (+{s.retard_moy.toFixed(1)})
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <Badge
                      tone={
                        s.pct_conforme >= 0.93
                          ? "success"
                          : s.pct_conforme >= 0.88
                          ? "neutral"
                          : "warning"
                      }
                    >
                      {Math.round(s.pct_conforme * 100)}%
                    </Badge>
                    <div className="text-[11px] text-slate-500 tabular-nums mt-1">
                      fiab {Math.round(s.taux_fiabilite * 100)}%
                    </div>
                  </td>
                  <td className="px-5 py-3 text-right text-xs text-slate-700 tabular-nums">
                    {(s.ca_total / 1e6).toFixed(1)} M EUR
                    <div className="text-[11px] text-slate-500">
                      {s.n_orders} commandes
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
