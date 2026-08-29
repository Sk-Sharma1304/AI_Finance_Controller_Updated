import { Activity, ShieldCheck } from "lucide-react"
import type { DataSource } from "@/lib/pipeline"

export function DashboardHeader({
  total,
  llmEvaluated,
  source,
  filename,
}: {
  total: number
  llmEvaluated: number
  source?: DataSource | "upload"
  filename?: string
}) {
  const runTime = new Date().toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  })

  return (
    <header className="border-b border-border/80 bg-card/40">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-4 px-5 py-5 md:flex-row md:items-center md:justify-between md:px-8">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/12 text-primary ring-1 ring-primary/20">
            <ShieldCheck className="size-5" aria-hidden />
          </div>
          <div>
            <h1 className="text-pretty text-lg font-semibold leading-tight tracking-tight md:text-xl">
              AI Finance Controller
            </h1>
            <p className="text-sm text-muted-foreground">
              Settlement reconciliation control tower — 8-agent decisioning pipeline
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-md border border-risk-low/25 bg-risk-low/10 px-2.5 py-1 text-xs font-medium text-risk-low">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-risk-low/60" />
              <span className="relative inline-flex size-2 rounded-full bg-risk-low" />
            </span>
            Pipeline healthy
          </span>
          {source === "upload" ? (
            <span
              className="inline-flex items-center gap-1.5 rounded-md border border-primary/25 bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
              title={filename ? `Scoring your uploaded file: ${filename}` : undefined}
            >
              Your file{filename ? ` · ${filename}` : ""}
            </span>
          ) : source === "backend" ? (
            <span className="inline-flex items-center gap-1.5 rounded-md border border-primary/25 bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
              Live model · Python backend
            </span>
          ) : source === "fallback" ? (
            <span
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-muted/40 px-2.5 py-1 text-xs font-medium text-muted-foreground"
              title="Backend API not reachable — showing local simulated pipeline. Start api_server.py to see live IsolationForest results."
            >
              Offline demo data
            </span>
          ) : null}
          <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-muted/40 px-2.5 py-1 font-mono text-xs text-muted-foreground">
            <Activity className="size-3.5" aria-hidden />
            {total} txns · {llmEvaluated} LLM-reviewed
          </span>
          <span className="hidden rounded-md border border-border bg-muted/40 px-2.5 py-1 font-mono text-xs text-muted-foreground sm:inline">
            Last run {runTime}
          </span>
        </div>
      </div>
    </header>
  )
}
