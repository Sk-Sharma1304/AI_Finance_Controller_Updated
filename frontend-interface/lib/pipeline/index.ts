import rawData from "@/lib/data/transactions.json"
import { runPipeline } from "./pipeline"
import type {
  RawTransaction,
  Transaction,
  PipelineSummary,
  FinalDecision,
  RiskLevel,
} from "./types"

export * from "./types"

// The Next.js frontend talks to the real Python backend
// (AI_Finance_Controller/api_server.py), which trains the
// IsolationForest fresh and runs the full 8-agent pipeline on
// every request. If that backend isn't reachable (e.g. running the
// frontend standalone for a quick UI preview), we fall back to the
// bundled TS pipeline simulation over static data so the dashboard
// still renders something sensible.
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8000"

export type DataSource = "backend" | "fallback"

export interface PipelineData {
  transactions: Transaction[]
  summary: PipelineSummary
  source: DataSource
}

let cached: PipelineData | null = null

const emptyDecision = (): Record<FinalDecision, number> => ({
  NORMAL: 0,
  FINANCIAL_EXCEPTION: 0,
  ML_REVIEW: 0,
  AI_ESCALATED_REVIEW: 0,
  CONFIRMED_HIGH_PRIORITY: 0,
})

const emptyRisk = (): Record<RiskLevel, number> => ({
  LOW: 0,
  MEDIUM: 0,
  HIGH: 0,
  CRITICAL: 0,
})

function computeSummary(txns: Transaction[]): PipelineSummary {
  const total = txns.length

  const decisionCounts = emptyDecision()
  const riskCounts = emptyRisk()
  const actionCounts: Record<string, number> = {}

  let totalImpact = 0
  let atRiskImpact = 0
  let mlAnomalies = 0
  let duplicates = 0
  let llmEvaluated = 0

  for (const t of txns) {
    decisionCounts[t.final_decision] += 1
    riskCounts[t.risk_level] += 1
    actionCounts[t.recommended_action] =
      (actionCounts[t.recommended_action] ?? 0) + 1
    totalImpact += t.financial_impact
    if (t.final_decision !== "NORMAL") atRiskImpact += t.financial_impact
    if (t.ml_anomaly === -1) mlAnomalies += 1
    if (t.duplicate_flag) duplicates += 1
    if (t.llm_risk_opinion !== "NOT_EVALUATED") llmEvaluated += 1
  }

  const autoCleared = decisionCounts.NORMAL
  const flagged = total - autoCleared

  return {
    total,
    autoCleared,
    autoClearedPct: total ? (autoCleared / total) * 100 : 0,
    flagged,
    aiEscalated: decisionCounts.AI_ESCALATED_REVIEW,
    confirmedHighPriority: decisionCounts.CONFIRMED_HIGH_PRIORITY,
    mlAnomalies,
    duplicates,
    totalImpact,
    atRiskImpact,
    decisionCounts,
    riskCounts,
    actionCounts,
    llmEvaluated,
  }
}

async function fetchFromBackend(): Promise<PipelineData | null> {
  try {
    const res = await fetch(`${API_URL}/api/results`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    })
    if (!res.ok) return null
    const data = (await res.json()) as {
      transactions: Transaction[]
      summary: PipelineSummary
    }
    if (!Array.isArray(data.transactions) || data.transactions.length === 0) {
      return null
    }
    return { transactions: data.transactions, summary: data.summary, source: "backend" }
  } catch {
    return null
  }
}

async function getPipelineData(): Promise<PipelineData> {
  if (cached) return cached

  const backend = await fetchFromBackend()
  if (backend) {
    cached = backend
    return cached
  }

  const transactions = runPipeline(rawData as unknown as RawTransaction[])
  cached = { transactions, summary: computeSummary(transactions), source: "fallback" }
  return cached
}

export async function getDataSource(): Promise<DataSource> {
  return (await getPipelineData()).source
}

export async function getTransactions(): Promise<Transaction[]> {
  return (await getPipelineData()).transactions
}

export async function getTransaction(id: string): Promise<Transaction | undefined> {
  const txns = await getTransactions()
  return txns.find((t) => t.payment_id === id)
}

export async function getSummary(): Promise<PipelineSummary> {
  return (await getPipelineData()).summary
}

const PRIORITY_DECISIONS: FinalDecision[] = [
  "CONFIRMED_HIGH_PRIORITY",
  "AI_ESCALATED_REVIEW",
  "FINANCIAL_EXCEPTION",
  "ML_REVIEW",
]

// Pure function version so client components (e.g. the upload
// panel, which receives fresh transactions straight from a fetch
// response rather than through the cached server-side pipeline)
// can compute the same priority ordering without going through
// the async/cached getPipelineData() path.
export function priorityQueueFrom(txns: Transaction[]): Transaction[] {
  return txns
    .filter((t) => PRIORITY_DECISIONS.includes(t.final_decision))
    .sort((a, b) => {
      const rank = (d: FinalDecision) => PRIORITY_DECISIONS.indexOf(d)
      if (rank(a.final_decision) !== rank(b.final_decision)) {
        return rank(a.final_decision) - rank(b.final_decision)
      }
      return b.financial_impact - a.financial_impact
    })
}

export async function getPriorityQueue(): Promise<Transaction[]> {
  const txns = await getTransactions()
  return priorityQueueFrom(txns)
}
