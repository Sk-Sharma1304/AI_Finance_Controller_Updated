"use client"

import { useMemo, useState } from "react"
import { Search, X } from "lucide-react"
import { AgentTrail } from "@/components/agent-trail"
import { DecisionBadge, RiskBadge } from "@/components/status-badges"
import { DECISION_META, formatINR, transactionTag } from "@/lib/pipeline/display"
import type { FinalDecision, Transaction } from "@/lib/pipeline/types"
import { cn } from "@/lib/utils"

const FILTERS: { key: FinalDecision | "ALL"; label: string }[] = [
  { key: "ALL", label: "All" },
  { key: "CONFIRMED_HIGH_PRIORITY", label: DECISION_META.CONFIRMED_HIGH_PRIORITY.short },
  { key: "AI_ESCALATED_REVIEW", label: DECISION_META.AI_ESCALATED_REVIEW.short },
  { key: "FINANCIAL_EXCEPTION", label: DECISION_META.FINANCIAL_EXCEPTION.short },
  { key: "ML_REVIEW", label: DECISION_META.ML_REVIEW.short },
  { key: "NORMAL", label: DECISION_META.NORMAL.short },
]

export function TransactionExplorer({
  transactions,
  initialId,
}: {
  transactions: Transaction[]
  initialId?: string
}) {
  const [query, setQuery] = useState("")
  const [filter, setFilter] = useState<FinalDecision | "ALL">("ALL")
  const [selected, setSelected] = useState<string>(
    initialId ?? transactions[0]?.payment_id ?? "",
  )

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return transactions.filter((t) => {
      if (filter !== "ALL" && t.final_decision !== filter) return false
      if (!q) return true
      return (
        t.payment_id.toLowerCase().includes(q) ||
        (t.order_id ?? "").toLowerCase().includes(q) ||
        (t.scenario ?? "").toLowerCase().includes(q) ||
        t.reconciliation_status.toLowerCase().includes(q)
      )
    })
  }, [transactions, query, filter])

  const selectedTxn =
    transactions.find((t) => t.payment_id === selected) ?? filtered[0] ?? transactions[0]

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      {/* list */}
      <div className="rounded-xl border border-border bg-card">
        <div className="space-y-3 border-b border-border p-3">
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search payment / order id or scenario"
              className="h-9 w-full rounded-md border border-border bg-background pl-8 pr-8 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring/50"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label="Clear search"
              >
                <X className="size-4" />
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                className={cn(
                  "rounded-md border px-2 py-1 text-xs font-medium transition-colors",
                  filter === f.key
                    ? "border-primary/40 bg-primary/12 text-primary"
                    : "border-border bg-muted/30 text-muted-foreground hover:text-foreground",
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div className="max-h-[560px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-card text-xs uppercase tracking-wide text-muted-foreground">
              <tr className="border-b border-border">
                <th className="px-3 py-2 text-left font-medium">Payment</th>
                <th className="px-3 py-2 text-left font-medium">Type</th>
                <th className="hidden px-3 py-2 text-right font-medium sm:table-cell">
                  Impact
                </th>
                <th className="px-3 py-2 text-right font-medium">Risk</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => (
                <tr
                  key={t.payment_id}
                  onClick={() => setSelected(t.payment_id)}
                  className={cn(
                    "cursor-pointer border-b border-border/50 transition-colors hover:bg-muted/30",
                    selectedTxn?.payment_id === t.payment_id && "bg-primary/8",
                  )}
                >
                  <td className="px-3 py-2">
                    <div className="font-mono text-[13px] font-medium">
                      {t.payment_id}
                    </div>
                    <div className="mt-0.5">
                      <DecisionBadge decision={t.final_decision} />
                    </div>
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {transactionTag(t)}
                  </td>
                  <td className="hidden px-3 py-2 text-right font-mono tabular-nums text-muted-foreground sm:table-cell">
                    {formatINR(t.financial_impact)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <RiskBadge level={t.risk_level} />
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-3 py-10 text-center text-sm text-muted-foreground"
                  >
                    No transactions match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="border-t border-border px-3 py-2 text-xs text-muted-foreground">
          {filtered.length} of {transactions.length} transactions
        </div>
      </div>

      {/* detail */}
      <div className="rounded-xl border border-border bg-card p-4 md:p-5">
        {selectedTxn ? (
          <AgentTrail t={selectedTxn} />
        ) : (
          <p className="text-sm text-muted-foreground">Select a transaction.</p>
        )}
      </div>
    </div>
  )
}
