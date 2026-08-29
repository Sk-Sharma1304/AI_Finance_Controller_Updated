"use client"

import { useMemo, useState } from "react"
import { DashboardHeader } from "@/components/dashboard-header"
import { KpiCards } from "@/components/kpi-cards"
import { DecisionChart, RiskDonut } from "@/components/overview-charts"
import { Workspace } from "@/components/workspace"
import { UploadPanel, type UploadResult } from "@/components/upload-panel"
import { AuditTrail } from "@/components/audit-trail"
import { priorityQueueFrom, type DataSource } from "@/lib/pipeline"
import type { PipelineSummary, Transaction } from "@/lib/pipeline/types"

export function DashboardClient({
  initialTransactions,
  initialSummary,
  initialSource,
}: {
  initialTransactions: Transaction[]
  initialSummary: PipelineSummary
  initialSource: DataSource
}) {
  const [upload, setUpload] = useState<UploadResult | null>(null)

  const transactions = upload ? upload.transactions : initialTransactions
  const summary = upload ? upload.summary : initialSummary
  const queue = useMemo(() => priorityQueueFrom(transactions), [transactions])

  const source: DataSource | "upload" = upload ? "upload" : initialSource

  return (
    <div className="min-h-svh">
      <DashboardHeader
        total={summary.total}
        llmEvaluated={summary.llmEvaluated}
        source={source}
        filename={upload?.filename}
      />

      <main className="mx-auto max-w-[1400px] space-y-5 px-5 py-6 md:px-8 md:py-8">
        <section aria-label="Upload">
          <UploadPanel
            active={!!upload}
            onResult={(result) => setUpload(result)}
            onReset={() => setUpload(null)}
          />
        </section>

        <section aria-label="Key metrics">
          <KpiCards summary={summary} />
        </section>

        <section className="grid gap-4 lg:grid-cols-2" aria-label="Overview charts">
          <DecisionChart counts={summary.decisionCounts} />
          <RiskDonut counts={summary.riskCounts} />
        </section>

        <section aria-label="Operations workspace">
          <Workspace transactions={transactions} queue={queue} summary={summary} />
        </section>

        {upload && (
          <section aria-label="Audit trail">
            <AuditTrail uploadId={upload.uploadId} />
          </section>
        )}

        <footer className="border-t border-border pt-5 text-xs text-muted-foreground">
          <p className="text-pretty">
            AI Finance Controller — multi-agent settlement reconciliation and
            fraud-control pipeline. {upload ? (
              <>
                Verdicts computed live from your uploaded file (
                <span className="font-medium text-foreground">{upload.filename}</span>
                ), {summary.total} transactions
                {upload.modelVersion && (
                  <>
                    {" "}
                    · anomaly model <span className="font-mono">{upload.modelVersion}</span>
                  </>
                )}
                .
              </>
            ) : (
              <>
                Verdicts are computed live from {summary.total} synthetic
                transactions running the full reconciliation → duplicate →
                anomaly → risk → investigation → LLM → decision → action
                chain.
              </>
            )}
          </p>
        </footer>
      </main>
    </div>
  )
}
