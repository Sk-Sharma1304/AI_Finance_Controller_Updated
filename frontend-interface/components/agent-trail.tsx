import {
  GitCompareArrows,
  Copy,
  Radar,
  Gauge,
  Search,
  Sparkles,
  Scale,
  Zap,
} from "lucide-react"
import { RiskBadge, DecisionBadge, PriorityBadge } from "@/components/status-badges"
import { formatINR, transactionTag } from "@/lib/pipeline/display"
import type { Transaction } from "@/lib/pipeline/types"

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`
}

export function AgentTrail({ t }: { t: Transaction }) {
  const steps = [
    {
      n: 1,
      icon: GitCompareArrows,
      name: "Reconciliation",
      headline: t.reconciliation_status,
      accent: t.reconciliation_status === "RECONCILED",
      detail: `Deviation ${pct(t.deviation_ratio)} · settlement ratio ${pct(
        t.settlement_ratio,
      )} · severity ${t.reconciliation_severity}`,
    },
    {
      n: 2,
      icon: Copy,
      name: "Duplicate detection",
      headline: t.duplicate_flag ? "DUPLICATE" : "CLEAR",
      accent: !t.duplicate_flag,
      detail: `Duplicate count ${t.duplicate_count} · risk ${t.duplicate_risk}`,
    },
    {
      n: 3,
      icon: Radar,
      name: "Anomaly detection (ML)",
      headline: t.anomaly_status,
      accent: t.anomaly_status === "NORMAL",
      detail: `IsolationForest on ratio features · anomaly score ${pct(
        t.anomaly_score,
      )}`,
    },
    {
      n: 4,
      icon: Gauge,
      name: "Risk assessment",
      headline: `${t.risk_level} · ${t.risk_score}/100`,
      accent: t.risk_level === "LOW",
      detail: `Scored from exception type and ₹${t.financial_impact.toFixed(
        0,
      )} financial impact`,
    },
    {
      n: 5,
      icon: Search,
      name: "Investigation (rules)",
      headline: "Evidence assembled",
      accent: true,
      detail: t.investigation_summary,
    },
    {
      n: 6,
      icon: Sparkles,
      name: "LLM investigation",
      headline:
        t.llm_risk_opinion === "NOT_EVALUATED"
          ? "Not evaluated (below threshold)"
          : `${t.llm_risk_opinion} · ${(t.llm_confidence * 100).toFixed(0)}% confidence`,
      accent: t.llm_risk_opinion === "NOT_EVALUATED",
      detail:
        t.llm_narrative ||
        "Rules cleared this transaction, so the cost-gated LLM layer did not review it.",
    },
    {
      n: 7,
      icon: Scale,
      name: "Decision",
      headline: t.final_decision,
      accent: t.final_decision === "NORMAL",
      detail: "Combines rule risk, the ML signal and the LLM's independent opinion.",
    },
    {
      n: 8,
      icon: Zap,
      name: "Action",
      headline: t.recommended_action,
      accent: t.recommended_action === "NO_ACTION",
      detail: t.action_reason,
    },
  ]

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2 border-b border-border pb-4">
        <span className="font-mono text-base font-semibold">{t.payment_id}</span>
        <span className="rounded-md border border-border bg-muted/40 px-2 py-0.5 font-mono text-xs text-muted-foreground">
          {transactionTag(t)}
        </span>
        <RiskBadge level={t.risk_level} />
        <DecisionBadge decision={t.final_decision} />
        <PriorityBadge priority={t.action_priority} />
        <span className="ml-auto font-mono text-sm tabular-nums text-muted-foreground">
          impact {formatINR(t.financial_impact)}
        </span>
      </div>

      <ol className="relative space-y-0">
        {steps.map((s, i) => {
          const Icon = s.icon
          const last = i === steps.length - 1
          return (
            <li key={s.n} className="relative flex gap-3 pb-4">
              {!last && (
                <span
                  className="absolute left-[15px] top-8 h-[calc(100%-1rem)] w-px bg-border"
                  aria-hidden
                />
              )}
              <span
                className={
                  "z-10 flex size-8 shrink-0 items-center justify-center rounded-full border " +
                  (s.accent
                    ? "border-border bg-muted/60 text-muted-foreground"
                    : "border-primary/30 bg-primary/12 text-primary")
                }
              >
                <Icon className="size-4" aria-hidden />
              </span>
              <div className="min-w-0 flex-1 pt-0.5">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {s.n}. {s.name}
                  </span>
                  <span className="font-mono text-sm font-medium">{s.headline}</span>
                </div>
                <p className="mt-0.5 text-sm text-pretty text-foreground/75">
                  {s.detail}
                </p>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
