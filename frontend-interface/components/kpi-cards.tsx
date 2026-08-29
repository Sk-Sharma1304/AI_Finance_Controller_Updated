import {
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Layers,
  IndianRupee,
} from "lucide-react"
import { formatINR } from "@/lib/pipeline/display"
import type { PipelineSummary } from "@/lib/pipeline/types"
import { cn } from "@/lib/utils"

function Kpi({
  label,
  value,
  sub,
  icon,
  accent,
}: {
  label: string
  value: string
  sub: string
  icon: React.ReactNode
  accent?: string
}) {
  return (
    <div className="flex flex-col justify-between rounded-xl border border-border bg-card p-4 md:p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        <span className={cn("text-muted-foreground", accent)}>{icon}</span>
      </div>
      <div className="mt-3">
        <div className="font-mono text-2xl font-semibold tracking-tight tabular-nums md:text-[28px]">
          {value}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
      </div>
    </div>
  )
}

export function KpiCards({ summary }: { summary: PipelineSummary }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
      <Kpi
        label="Total volume"
        value={summary.total.toLocaleString("en-IN")}
        sub="Transactions ingested this run"
        icon={<Layers className="size-4" aria-hidden />}
      />
      <Kpi
        label="Auto-cleared"
        value={`${summary.autoClearedPct.toFixed(0)}%`}
        sub={`${summary.autoCleared} settled cleanly`}
        icon={<CheckCircle2 className="size-4" aria-hidden />}
        accent="text-risk-low"
      />
      <Kpi
        label="Flagged for review"
        value={summary.flagged.toLocaleString("en-IN")}
        sub={`${summary.confirmedHighPriority} confirmed critical`}
        icon={<AlertTriangle className="size-4" aria-hidden />}
        accent="text-risk-high"
      />
      <Kpi
        label="AI-escalated"
        value={summary.aiEscalated.toLocaleString("en-IN")}
        sub="Rules cleared, LLM disagreed"
        icon={<Sparkles className="size-4" aria-hidden />}
        accent="text-chart-4"
      />
      <Kpi
        label="Impact at risk"
        value={formatINR(summary.atRiskImpact, { compact: true })}
        sub={`of ${formatINR(summary.totalImpact, { compact: true })} total exposure`}
        icon={<IndianRupee className="size-4" aria-hidden />}
        accent="text-risk-critical"
      />
    </div>
  )
}
