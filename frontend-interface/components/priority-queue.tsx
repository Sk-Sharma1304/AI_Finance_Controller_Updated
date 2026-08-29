"use client"

import { useMemo, useState } from "react"
import { Check, X, ChevronRight, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { DecisionBadge, PriorityBadge, RiskBadge } from "@/components/status-badges"
import { formatINR, transactionTag } from "@/lib/pipeline/display"
import type { Transaction } from "@/lib/pipeline/types"
import { cn } from "@/lib/utils"

type ReviewState = "pending" | "approved" | "held"

export function PriorityQueue({
  queue,
  onInspect,
}: {
  queue: Transaction[]
  onInspect?: (id: string) => void
}) {
  const [reviews, setReviews] = useState<Record<string, ReviewState>>({})
  const [expanded, setExpanded] = useState<string | null>(queue[0]?.payment_id ?? null)

  const pending = useMemo(
    () => queue.filter((t) => (reviews[t.payment_id] ?? "pending") === "pending").length,
    [queue, reviews],
  )

  if (queue.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
        Nothing in the review queue right now.
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">Priority review queue</h2>
          <p className="text-xs text-muted-foreground">
            Sorted by severity, then financial impact
          </p>
        </div>
        <span className="rounded-md border border-border bg-muted/40 px-2.5 py-1 font-mono text-xs text-muted-foreground">
          {pending} pending / {queue.length}
        </span>
      </div>

      <ul className="divide-y divide-border">
        {queue.map((t) => {
          const state = reviews[t.payment_id] ?? "pending"
          const isOpen = expanded === t.payment_id
          return (
            <li key={t.payment_id}>
              <button
                type="button"
                onClick={() => setExpanded(isOpen ? null : t.payment_id)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/30"
                aria-expanded={isOpen}
              >
                <ChevronRight
                  className={cn(
                    "size-4 shrink-0 text-muted-foreground transition-transform",
                    isOpen && "rotate-90",
                  )}
                  aria-hidden
                />
                <span className="font-mono text-sm font-medium">{t.payment_id}</span>
                <span className="hidden text-sm text-muted-foreground sm:inline">
                  {transactionTag(t)}
                </span>
                <span className="ml-auto flex items-center gap-2">
                  {state !== "pending" && (
                    <span
                      className={cn(
                        "rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase",
                        state === "approved"
                          ? "bg-risk-low/15 text-risk-low"
                          : "bg-risk-high/15 text-risk-high",
                      )}
                    >
                      {state}
                    </span>
                  )}
                  <span className="hidden font-mono text-sm tabular-nums text-muted-foreground md:inline">
                    {formatINR(t.financial_impact)}
                  </span>
                  <DecisionBadge decision={t.final_decision} />
                </span>
              </button>

              {isOpen && (
                <div className="grid gap-4 border-t border-border/60 bg-background/40 px-4 py-4 md:grid-cols-[1fr_auto]">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <RiskBadge level={t.risk_level} />
                      <PriorityBadge priority={t.action_priority} />
                      <span className="rounded-md border border-border bg-muted/40 px-2 py-0.5 font-mono text-xs text-muted-foreground">
                        risk {t.risk_score}/100
                      </span>
                      <span className="rounded-md border border-border bg-muted/40 px-2 py-0.5 font-mono text-xs text-muted-foreground">
                        {t.recommended_action}
                      </span>
                    </div>

                    <p className="text-sm text-foreground/90">{t.investigation_summary}</p>

                    {t.llm_risk_opinion !== "NOT_EVALUATED" && t.llm_narrative && (
                      <div className="rounded-lg border border-chart-4/25 bg-chart-4/8 p-3">
                        <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-chart-4">
                          <Sparkles className="size-3.5" aria-hidden />
                          LLM opinion · {t.llm_risk_opinion} ·{" "}
                          {(t.llm_confidence * 100).toFixed(0)}% confidence
                        </div>
                        <p className="text-sm text-foreground/85">{t.llm_narrative}</p>
                      </div>
                    )}

                    <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-3">
                      <Meta label="Expected" value={formatINR(t.expected_settlement)} />
                      <Meta
                        label="Actual"
                        value={
                          t.actual_settlement == null
                            ? "—"
                            : formatINR(t.actual_settlement)
                        }
                      />
                      <Meta label="Impact" value={formatINR(t.financial_impact)} />
                    </dl>
                  </div>

                  <div className="flex flex-row gap-2 md:flex-col">
                    <Button
                      size="sm"
                      variant="secondary"
                      className="flex-1 border border-risk-low/30 bg-risk-low/10 text-risk-low hover:bg-risk-low/20"
                      onClick={() =>
                        setReviews((r) => ({ ...r, [t.payment_id]: "approved" }))
                      }
                    >
                      <Check className="size-4" aria-hidden />
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="flex-1 border border-risk-high/30 bg-risk-high/10 text-risk-high hover:bg-risk-high/20"
                      onClick={() =>
                        setReviews((r) => ({ ...r, [t.payment_id]: "held" }))
                      }
                    >
                      <X className="size-4" aria-hidden />
                      Hold
                    </Button>
                    {onInspect && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="flex-1 text-muted-foreground"
                        onClick={() => onInspect(t.payment_id)}
                      >
                        Full trail
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </li>
          )
        })}
      </ul>

      <p className="border-t border-border px-4 py-3 text-xs text-muted-foreground">
        Approve / Hold is a demo control kept in local state — in production this would
        call an action-execution service with a durable audit record.
      </p>
    </div>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-mono tabular-nums">{value}</dd>
    </div>
  )
}
