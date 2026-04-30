import { useQuery } from "@tanstack/react-query";
import { ScrollText, ShieldCheck, FileText, Sparkles, AlertCircle } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
  Badge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  PageLoader,
  EmptyState,
} from "../components/ui";
import { PageHeader } from "../components/PageHeader";
import { auditApi } from "../api/client";

function DecisionBadge({ decision }) {
  const tone =
    decision === "validated"
      ? "success"
      : decision === "rejected"
      ? "danger"
      : "warning";
  return <Badge tone={tone}>{decision}</Badge>;
}

function EventList({ events }) {
  if (!events?.length)
    return (
      <EmptyState
        icon={ScrollText}
        title="Pas encore de decision"
        description="Validez ou rejetez une recommandation depuis la page Forecast & Reco pour alimenter ce journal."
      />
    );
  return (
    <Card className="overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
          <tr>
            <th className="px-5 py-3 text-left font-semibold">Horodatage</th>
            <th className="px-5 py-3 text-left font-semibold">Type</th>
            <th className="px-5 py-3 text-left font-semibold">SKU</th>
            <th className="px-5 py-3 text-left font-semibold">Decision</th>
            <th className="px-5 py-3 text-left font-semibold">
              Quantite / Fournisseur
            </th>
            <th className="px-5 py-3 text-left font-semibold">Operateur</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e, i) => (
            <tr
              key={i}
              className="border-t border-slate-100 hover:bg-slate-50"
            >
              <td className="px-5 py-3 font-mono text-xs text-slate-600 whitespace-nowrap">
                {e.ts?.replace("T", " ").replace("Z", "")}
              </td>
              <td className="px-5 py-3">
                <Badge tone="neutral">{e.type}</Badge>
              </td>
              <td className="px-5 py-3 font-mono text-xs text-slate-700">
                {e.store_id} - {e.product_id}
              </td>
              <td className="px-5 py-3">
                <DecisionBadge decision={e.decision} />
              </td>
              <td className="px-5 py-3 text-xs text-slate-700 tabular-nums">
                {e.qty_modified ?? e.qty_recommandee} u.
                {e.fournisseur_id && (
                  <span className="text-slate-500"> * {e.fournisseur_id}</span>
                )}
              </td>
              <td className="px-5 py-3 text-xs text-slate-600">
                {e.user || "anonymous"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function ModelCardView({ card }) {
  if (!card) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-accent-600" /> {card.name}
        </CardTitle>
        <CardDescription>
          v{card.version} * {card.type}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Section title="Finalite">{card.purpose}</Section>
        <Section title="Donnees d'entrainement">
          <ul className="text-sm text-slate-700 space-y-1">
            {Object.entries(card.training_data || {}).map(([k, v]) => (
              <li key={k}>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  {k}
                </span>
                <div className="text-sm text-slate-700 mt-0.5">{v}</div>
              </li>
            ))}
          </ul>
        </Section>
        <Section title="Features">
          <div className="flex flex-wrap gap-1.5">
            {(card.features || []).map((f) => (
              <Badge key={f} tone="neutral">
                {f}
              </Badge>
            ))}
          </div>
        </Section>
        <Section title="Hyperparametres">
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(card.hyperparams || {}).map(([k, v]) => (
              <Badge key={k} tone="accent">
                {k}={v}
              </Badge>
            ))}
          </div>
        </Section>
        <Section title="Limites assumees">
          <ul className="text-sm text-slate-700 space-y-1 list-disc pl-5">
            {(card.limites_assumees || card.limites || []).map((l, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <AlertCircle className="w-3 h-3 text-amber-500 flex-shrink-0 mt-1" />
                <span>{l}</span>
              </li>
            ))}
          </ul>
        </Section>

        {card.enrichissements && (
          <Section title={`Enrichissements (${card.enrichissements.actif ? "actifs" : "inactifs"})`}>
            <div className="space-y-3">
              {(card.enrichissements.details || []).map((e) => (
                <div key={e.nom} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-3.5 h-3.5 text-accent-500" />
                    <span className="font-mono text-xs font-semibold text-slate-900">{e.nom}</span>
                    <Badge tone={e.type.includes("synth") ? "warning" : e.type.includes("externe") ? "accent" : "neutral"}>
                      {e.type}
                    </Badge>
                  </div>
                  <div className="text-sm text-slate-700">{e.description}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Methode :</span>{" "}
                    {e.methode}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Pourquoi :</span>{" "}
                    {e.motivation}
                  </div>
                  {e.flag && (
                    <div className="text-[11px] font-mono text-slate-500 mt-1">
                      flag: {e.flag}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Section>
        )}
        <Section title="Supervision humaine">
          <div className="text-sm text-slate-700">
            {card.supervision_humaine?.principe}
          </div>
          <div className="text-[11px] font-mono text-slate-500 mt-1">
            log: {card.supervision_humaine?.log_audit}
          </div>
        </Section>
        <Section title="Conformite IA Act">
          <div className="text-sm text-slate-700 mb-2">
            Categorie :{" "}
            <Badge tone="warning">{card.ia_act?.categorie}</Badge>
          </div>
          <ul className="text-sm text-slate-700 space-y-1">
            {(card.ia_act?.obligations_couvertes || []).map((o, i) => (
              <li key={i} className="flex items-start gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>{o}</span>
              </li>
            ))}
          </ul>
        </Section>
      </CardContent>
    </Card>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
        {title}
      </div>
      <div>{children}</div>
    </div>
  );
}

export default function AuditPage() {
  const eventsQ = useQuery({
    queryKey: ["audit"],
    queryFn: () => auditApi.list(200),
    refetchInterval: 10_000,
  });
  const cardQ = useQuery({
    queryKey: ["model_card"],
    queryFn: () => auditApi.modelCard(),
  });

  if (eventsQ.isLoading || cardQ.isLoading) return <PageLoader />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tracabilite IA Act"
        description="Journal d'audit append-only + documentation modele. Conforme aux obligations de transparence et de supervision humaine."
      />

      <Tabs defaultValue="events">
        <TabsList>
          <TabsTrigger value="events">Decisions</TabsTrigger>
          <TabsTrigger value="model">Model card</TabsTrigger>
        </TabsList>

        <TabsContent value="events">
          <EventList events={eventsQ.data?.events || []} />
        </TabsContent>

        <TabsContent value="model">
          <ModelCardView card={cardQ.data} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
