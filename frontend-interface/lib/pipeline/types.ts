export type Scenario =
  | "normal"
  | "refund"
  | "adjustment"
  | "amount_discrepancy"
  | "wrong_settlement"
  | "unexplained_difference"
  | "duplicate_transaction"
  | "missing_settlement"

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"

export type ReconciliationStatus =
  | "RECONCILED"
  | "DISCREPANCY"
  | "MISSING_SETTLEMENT"

export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"

export type FinalDecision =
  | "NORMAL"
  | "FINANCIAL_EXCEPTION"
  | "ML_REVIEW"
  | "AI_ESCALATED_REVIEW"
  | "CONFIRMED_HIGH_PRIORITY"

export type ActionPriority = "IMMEDIATE" | "HIGH" | "LOW"

export type LlmOpinion = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | "NOT_EVALUATED"

export interface RawTransaction {
  payment_id: string
  order_id?: string
  payment_amount: number
  fee: number
  tax: number
  refund: number
  adjustment: number
  actual_settlement: number | null
  // The next three are demo-dataset-only columns (they come from
  // the synthetic dataset's `status` column and the ground-truth
  // "answer key" file's `scenario`/`expected_status`). A real
  // uploaded CSV never has them -- every place that reads these
  // must treat them as optional and fall back to the computed
  // signals (reconciliation_status, risk_level, etc.) instead.
  status?: string
  scenario?: Scenario
  expected_settlement: number
  expected_status?: string
}

export interface Transaction extends RawTransaction {
  amount: number

  // reconciliation
  settlement_difference: number
  financial_impact: number
  settlement_ratio: number
  deviation_ratio: number
  difference_to_payment_ratio: number
  reconciliation_status: ReconciliationStatus
  reconciliation_severity: Severity

  // duplicate detection
  duplicate_flag: boolean
  duplicate_group: string | null
  duplicate_count: number
  duplicate_risk: "NONE" | "MEDIUM" | "HIGH"

  // anomaly detection (ML)
  ml_anomaly: 1 | -1
  anomaly_status: "NORMAL" | "ANOMALY"
  anomaly_score: number

  // risk assessment
  risk_score: number
  risk_level: RiskLevel

  // investigation (rule based)
  investigation_summary: string
  evidence: string[]
  investigation_recommendation: string

  // llm investigation
  llm_risk_opinion: LlmOpinion
  llm_confidence: number
  llm_narrative: string
  llm_recommended_action: string

  // decision + action
  final_decision: FinalDecision
  recommended_action: string
  action_priority: ActionPriority
  action_reason: string
}

export interface PipelineSummary {
  total: number
  autoCleared: number
  autoClearedPct: number
  flagged: number
  aiEscalated: number
  confirmedHighPriority: number
  mlAnomalies: number
  duplicates: number
  totalImpact: number
  atRiskImpact: number
  decisionCounts: Record<FinalDecision, number>
  riskCounts: Record<RiskLevel, number>
  actionCounts: Record<string, number>
  llmEvaluated: number
}
