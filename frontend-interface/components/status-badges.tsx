import { cn } from "@/lib/utils"
import {
  DECISION_BG,
  DECISION_META,
  RISK_BG,
  RISK_META,
} from "@/lib/pipeline/display"
import type { FinalDecision, RiskLevel, ActionPriority } from "@/lib/pipeline/types"

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium",
        RISK_BG[level],
      )}
    >
      <span className="size-1.5 rounded-full bg-current" />
      {RISK_META[level].label}
    </span>
  )
}

export function DecisionBadge({ decision }: { decision: FinalDecision }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        DECISION_BG[decision],
      )}
    >
      {DECISION_META[decision].label}
    </span>
  )
}

const PRIORITY_STYLE: Record<ActionPriority, string> = {
  IMMEDIATE: "bg-risk-critical/15 text-risk-critical border-risk-critical/35",
  HIGH: "bg-risk-high/14 text-risk-high border-risk-high/28",
  LOW: "bg-muted text-muted-foreground border-border",
}

export function PriorityBadge({ priority }: { priority: ActionPriority }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
        PRIORITY_STYLE[priority],
      )}
    >
      {priority}
    </span>
  )
}
