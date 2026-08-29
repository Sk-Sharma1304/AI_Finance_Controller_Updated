"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp, ScrollText } from "lucide-react"
import { API_URL } from "@/lib/pipeline"
import { cn } from "@/lib/utils"

interface AuditEntry {
  paymentId: string
  riskScore: number | null
  riskLevel: string | null
  finalDecision: string | null
  recommendedAction: string | null
  financialImpact: number | null
  modelVersion: string | null
  actor: string | null
  createdAt: string | null
}

const API_KEY_STORAGE_KEY = "afc_api_key"

export function AuditTrail({ uploadId }: { uploadId: string }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [entries, setEntries] = useState<AuditEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    if (entries || loading) {
      setOpen((o) => !o)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const apiKey = window.localStorage.getItem(API_KEY_STORAGE_KEY)
      const res = await fetch(`${API_URL}/api/audit/${uploadId}`, {
        headers: apiKey ? { "X-API-Key": apiKey } : {},
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setEntries(data.entries)
      setOpen(true)
    } catch {
      setError("Couldn't load the audit trail.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card/40">
      <button
        type="button"
        onClick={load}
        className="flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <span className="inline-flex items-center gap-1.5">
          <ScrollText className="size-3.5" aria-hidden />
          {loading ? "Loading audit trail…" : "Audit trail (append-only decision log)"}
        </span>
        {open ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
      </button>

      {error && <p className="px-4 pb-3 text-xs text-risk-critical">{error}</p>}

      {open && entries && (
        <div className="max-h-64 overflow-y-auto border-t border-border">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-card text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">Payment</th>
                <th className="px-2 py-2 font-medium">Risk</th>
                <th className="px-2 py-2 font-medium">Decision</th>
                <th className="px-2 py-2 font-medium">Action</th>
                <th className="px-2 py-2 font-medium">Actor</th>
                <th className="px-4 py-2 font-medium">Model</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={i} className={cn(i % 2 === 0 ? "bg-transparent" : "bg-muted/20")}>
                  <td className="px-4 py-1.5 font-mono">{e.paymentId}</td>
                  <td className="px-2 py-1.5">{e.riskLevel}</td>
                  <td className="px-2 py-1.5">{e.finalDecision}</td>
                  <td className="px-2 py-1.5">{e.recommendedAction}</td>
                  <td className="px-2 py-1.5">{e.actor}</td>
                  <td className="px-4 py-1.5 font-mono text-muted-foreground">{e.modelVersion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
