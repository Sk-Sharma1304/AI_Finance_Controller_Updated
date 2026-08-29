import {
  GitCompareArrows,
  Copy,
  Radar,
  Gauge,
  Search,
  Sparkles,
  Scale,
  Zap,
  ArrowDown,
} from "lucide-react"
import type { PipelineSummary } from "@/lib/pipeline/types"

export function PipelineArchitecture({ summary }: { summary: PipelineSummary }) {
  const stages = [
    {
      icon: GitCompareArrows,
      name: "Reconciliation Agent",
      desc: "Compares expected vs. actual settlement, deriving ratio features and severity.",
      stat: `${summary.total} reconciled`,
    },
    {
      icon: Copy,
      name: "Duplicate Detection Agent",
      desc: "Flags transactions that look like the same financial event happening twice.",
      stat: `${summary.duplicates} duplicates`,
    },
    {
      icon: Radar,
      name: "Anomaly Detection Agent",
      desc: "Unsupervised IsolationForest over ratio features — catches novel patterns.",
      stat: `${summary.mlAnomalies} anomalies`,
    },
    {
      icon: Gauge,
      name: "Risk Assessment Agent",
      desc: "Turns exception type and financial impact into a 0–100 score and level.",
      stat: `${summary.riskCounts.HIGH + summary.riskCounts.CRITICAL} high+`,
    },
    {
      icon: Search,
      name: "Investigation Agent",
      desc: "Assembles human-readable evidence and a rule-based recommendation.",
      stat: `${summary.flagged} investigated`,
    },
    {
      icon: Sparkles,
      name: "LLM Investigation Agent",
      desc: "Independent LLM opinion — can escalate a case the rules cleared.",
      stat: `${summary.llmEvaluated} reviewed`,
      highlight: true,
    },
    {
      icon: Scale,
      name: "Decision Agent",
      desc: "Fuses rule risk, the ML signal and the LLM opinion into one verdict.",
      stat: `${summary.aiEscalated} AI-escalated`,
    },
    {
      icon: Zap,
      name: "Action Agent",
      desc: "Converts the decision into a concrete next step with a priority.",
      stat: `${summary.confirmedHighPriority} immediate`,
    },
  ]

  return (
    <div className="rounded-xl border border-border bg-card p-4 md:p-6">
      <div className="mb-5">
        <h2 className="text-sm font-semibold">Agent pipeline</h2>
        <p className="text-xs text-muted-foreground">
          Every transaction flows through eight specialized agents in order — each
          agent&apos;s live output count is shown on the right.
        </p>
      </div>

      <ol className="mx-auto max-w-3xl space-y-0">
        {stages.map((s, i) => {
          const Icon = s.icon
          const last = i === stages.length - 1
          return (
            <li key={s.name}>
              <div
                className={
                  "flex items-center gap-4 rounded-lg border p-3.5 " +
                  (s.highlight
                    ? "border-chart-4/30 bg-chart-4/8"
                    : "border-border bg-background/40")
                }
              >
                <span
                  className={
                    "flex size-10 shrink-0 items-center justify-center rounded-lg " +
                    (s.highlight
                      ? "bg-chart-4/15 text-chart-4"
                      : "bg-primary/12 text-primary")
                  }
                >
                  <Icon className="size-5" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{s.name}</span>
                    {s.highlight && (
                      <span className="rounded border border-chart-4/30 bg-chart-4/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-chart-4">
                        reasoning layer
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-pretty text-muted-foreground">
                    {s.desc}
                  </p>
                </div>
                <span className="hidden shrink-0 rounded-md border border-border bg-muted/40 px-2.5 py-1 font-mono text-xs text-muted-foreground sm:inline">
                  {s.stat}
                </span>
              </div>
              {!last && (
                <div className="flex justify-center py-1.5" aria-hidden>
                  <ArrowDown className="size-4 text-border" />
                </div>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
