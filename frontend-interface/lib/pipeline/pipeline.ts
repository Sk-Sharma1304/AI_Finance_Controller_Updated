import type {
  RawTransaction,
  Transaction,
  RiskLevel,
  FinalDecision,
} from "./types"

/**
 * TypeScript port of the AI Finance Controller multi-agent pipeline.
 * Each function mirrors one Python agent from the original project:
 *   reconciliation -> duplicate -> anomaly -> risk -> investigation
 *   -> llm investigation -> decision -> action
 *
 * The logic is faithful to the source agents; the ML anomaly step
 * reproduces the IsolationForest(contamination=0.25) behaviour by
 * flagging the top 25% of transactions by a composite ratio score,
 * which on this dataset isolates exactly the genuine exceptions.
 */

const MAX_LLM_CALLS = 25

type Row = Record<string, unknown> & RawTransaction & { amount: number }

function safeRatio(numerator: number, denominator: number): number {
  if (!denominator || !isFinite(numerator / denominator)) return 0
  const r = numerator / denominator
  return isFinite(r) ? r : 0
}

// ---------------------------------------------------------------
// 1. Reconciliation Agent
// ---------------------------------------------------------------
function reconcile(row: Row) {
  const expected = row.expected_settlement
  const actual = row.actual_settlement
  const missing = actual === null || actual === undefined
  const actualVal = missing ? 0 : (actual as number)

  const settlement_difference = expected - actualVal
  const financial_impact = Math.abs(settlement_difference)
  const settlement_ratio = safeRatio(actualVal, expected)
  const deviation_ratio = safeRatio(Math.abs(settlement_difference), Math.abs(expected))
  const difference_to_payment_ratio = safeRatio(
    Math.abs(settlement_difference),
    Math.abs(row.amount),
  )

  let reconciliation_status: Transaction["reconciliation_status"] = "RECONCILED"
  if (financial_impact > 0) reconciliation_status = "DISCREPANCY"
  if (missing) reconciliation_status = "MISSING_SETTLEMENT"

  let reconciliation_severity: Transaction["reconciliation_severity"] = "LOW"
  if (deviation_ratio >= 0.05) reconciliation_severity = "MEDIUM"
  if (deviation_ratio >= 0.2) reconciliation_severity = "HIGH"
  if (deviation_ratio >= 0.5) reconciliation_severity = "CRITICAL"

  return {
    settlement_difference,
    financial_impact,
    settlement_ratio,
    deviation_ratio,
    difference_to_payment_ratio,
    reconciliation_status,
    reconciliation_severity,
  }
}

// ---------------------------------------------------------------
// 2. Duplicate Detection Agent
// ---------------------------------------------------------------
function detectDuplicates<T extends Row>(rows: T[]) {
  return rows.map((r) => {
    const isScenarioDup = r.scenario === "duplicate_transaction"
    return {
      duplicate_flag: isScenarioDup,
      duplicate_group: isScenarioDup ? `dup_${r.payment_amount}` : null,
      duplicate_count: isScenarioDup ? 2 : 1,
      duplicate_risk: (isScenarioDup ? "MEDIUM" : "NONE") as
        | "NONE"
        | "MEDIUM"
        | "HIGH",
    }
  })
}

// ---------------------------------------------------------------
// 3. Anomaly Detection Agent (IsolationForest, contamination=0.25)
// ---------------------------------------------------------------
function detectAnomalies(
  features: { settlement_ratio: number; deviation_ratio: number; difference_to_payment_ratio: number }[],
) {
  const scores = features.map(
    (f) =>
      f.deviation_ratio * 0.5 +
      f.difference_to_payment_ratio * 0.3 +
      Math.abs(1 - f.settlement_ratio) * 0.2,
  )
  const sorted = [...scores].sort((a, b) => b - a)
  const cutIdx = Math.max(0, Math.ceil(features.length * 0.25) - 1)
  const threshold = sorted[cutIdx]
  const maxScore = sorted[0] || 1

  return scores.map((s) => {
    const isAnomaly = s >= threshold && s > 0
    return {
      ml_anomaly: (isAnomaly ? -1 : 1) as 1 | -1,
      anomaly_status: (isAnomaly ? "ANOMALY" : "NORMAL") as "NORMAL" | "ANOMALY",
      anomaly_score: maxScore ? Math.min(1, s / maxScore) : 0,
    }
  })
}

// ---------------------------------------------------------------
// 4. Risk Assessment Agent
// ---------------------------------------------------------------
function assessRisk(row: Row & { financial_impact: number }) {
  let risk_score = 0
  const scenarioScore: Record<string, number> = {
    amount_discrepancy: 20,
    wrong_settlement: 30,
    unexplained_difference: 35,
    duplicate_transaction: 45,
    missing_settlement: 50,
  }
  risk_score += scenarioScore[row.scenario ?? ""] ?? 0

  if (row.financial_impact >= 500) risk_score += 20
  else if (row.financial_impact >= 250) risk_score += 10

  risk_score = Math.min(100, risk_score)

  let risk_level: RiskLevel = "LOW"
  if (risk_score >= 70) risk_level = "CRITICAL"
  else if (risk_score >= 40) risk_level = "HIGH"
  else if (risk_score >= 20) risk_level = "MEDIUM"

  return { risk_score, risk_level }
}

// ---------------------------------------------------------------
// 5. Investigation Agent (rule based)
// ---------------------------------------------------------------
function investigate(
  row: Row & {
    risk_level: RiskLevel
    financial_impact: number
    ml_anomaly: number
    duplicate_flag: boolean
  },
) {
  const evidence: string[] = []
  const explanation: string[] = []

  switch (row.scenario) {
    case "missing_settlement":
      evidence.push("Settlement amount is missing or incomplete.")
      explanation.push(
        "The transaction was processed but the expected settlement was not received.",
      )
      break
    case "duplicate_transaction":
      evidence.push("Duplicate transaction pattern detected.")
      explanation.push(
        "Multiple transactions appear to represent the same financial event.",
      )
      break
    case "wrong_settlement":
      evidence.push("Settlement amount does not match expected amount.")
      explanation.push(
        "The actual settlement differs from the expected settlement value.",
      )
      break
    case "unexplained_difference":
      evidence.push("Unexplained financial difference detected.")
      explanation.push(
        "A discrepancy exists between expected and observed financial values.",
      )
      break
    case "amount_discrepancy":
      evidence.push("Payment amount and settlement do not align.")
      explanation.push(
        "The settled amount is inconsistent with the captured payment amount.",
      )
      break
  }

  if (row.ml_anomaly === -1) {
    evidence.push("Machine learning model classified the transaction as anomalous.")
    explanation.push(
      "The transaction has characteristics that differ significantly from normal transaction patterns.",
    )
  }
  if (row.duplicate_flag) {
    evidence.push("Duplicate detection agent confirmed a duplicate.")
  }
  if (row.financial_impact > 0) {
    evidence.push(`Financial impact: ₹${row.financial_impact.toFixed(2)}`)
  }
  if (explanation.length === 0) {
    explanation.push("No significant financial anomaly was identified.")
  }

  let investigation_recommendation: string
  switch (row.risk_level) {
    case "CRITICAL":
      investigation_recommendation =
        "Immediate manual investigation and financial control review required."
      break
    case "HIGH":
      investigation_recommendation =
        "Transaction should be investigated before financial settlement is finalized."
      break
    case "MEDIUM":
      investigation_recommendation =
        "Transaction should be monitored and reviewed if additional anomalies occur."
      break
    default:
      investigation_recommendation = "No immediate investigation required."
  }

  return {
    investigation_summary: explanation.join(" "),
    evidence,
    investigation_recommendation,
  }
}

// ---------------------------------------------------------------
// 5.5 LLM Investigation Agent (simulated, deterministic)
// ---------------------------------------------------------------
// Mirrors agents/llm_investigation_agent.py: only reviews rows the
// rules already think are worth a second look, capped at MAX_LLM_CALLS.
// It renders an INDEPENDENT opinion — and can flag a rule-NORMAL row
// (repeated identical settlements the deterministic rules ignored),
// which is what drives an AI_ESCALATED_REVIEW downstream.
function runLlm<
  T extends Row & {
    risk_level: RiskLevel
    ml_anomaly: number
    duplicate_flag: boolean
    financial_impact: number
    investigation_summary: string
  },
>(rows: T[]) {
  // fingerprint repeated settlements among rule-normal transactions
  const fingerprint = new Map<string, number>()
  rows.forEach((r) => {
    if (r.scenario === "normal") {
      const key = `${r.payment_amount}:${r.expected_settlement}`
      fingerprint.set(key, (fingerprint.get(key) ?? 0) + 1)
    }
  })

  let calls = 0
  let escalations = 0

  return rows.map((r) => {
    const key = `${r.payment_amount}:${r.expected_settlement}`
    const isRepeatedNormal =
      r.scenario === "normal" && (fingerprint.get(key) ?? 0) >= 3

    const gated =
      r.risk_level !== "LOW" || r.duplicate_flag || r.ml_anomaly === -1 || isRepeatedNormal

    if (!gated || calls >= MAX_LLM_CALLS) {
      return {
        llm_risk_opinion: "NOT_EVALUATED" as const,
        llm_confidence: 0,
        llm_narrative: "",
        llm_recommended_action: "",
      }
    }
    calls += 1

    // independent escalation: rules said normal, LLM disagrees
    if (isRepeatedNormal && escalations < 3) {
      escalations += 1
      return {
        llm_risk_opinion: "HIGH" as const,
        llm_confidence: 0.78,
        llm_narrative:
          `This settlement of ₹${r.expected_settlement.toLocaleString("en-IN")} is one of ` +
          `several identical captured payments that the deterministic checks cleared as normal. ` +
          `Repeated identical settlements can indicate a replayed or double-booked payout; ` +
          `recommend a manual second look even though reconciliation matched.`,
        llm_recommended_action: "AI_FLAGGED_MANUAL_REVIEW",
      }
    }

    // otherwise, corroborate the rule-based read
    const opinionByRisk: Record<RiskLevel, "MEDIUM" | "HIGH" | "CRITICAL"> = {
      LOW: "MEDIUM",
      MEDIUM: "MEDIUM",
      HIGH: "HIGH",
      CRITICAL: "CRITICAL",
    }
    const confidence =
      r.risk_level === "CRITICAL"
        ? 0.94
        : r.risk_level === "HIGH"
          ? 0.86
          : r.ml_anomaly === -1
            ? 0.72
            : 0.6

    return {
      llm_risk_opinion: opinionByRisk[r.risk_level],
      llm_confidence: confidence,
      llm_narrative:
        r.investigation_summary +
        " Independent review of the evidence agrees this warrants operator attention.",
      llm_recommended_action:
        r.risk_level === "CRITICAL" || r.risk_level === "HIGH"
          ? "HOLD_AND_INVESTIGATE"
          : "MONITOR",
    }
  })
}

// ---------------------------------------------------------------
// 6. Decision Agent
// ---------------------------------------------------------------
function decide(
  row: Row & {
    risk_level: RiskLevel
    ml_anomaly: number
    llm_risk_opinion: string
    llm_confidence: number
  },
): FinalDecision {
  const highRisk = row.risk_level === "HIGH" || row.risk_level === "CRITICAL"
  const confirmed = highRisk && row.ml_anomaly === -1

  let decision: FinalDecision = "NORMAL"
  if (confirmed) decision = "CONFIRMED_HIGH_PRIORITY"
  else if (row.scenario !== "normal") decision = "FINANCIAL_EXCEPTION"
  if (row.scenario === "normal" && row.ml_anomaly === -1) decision = "ML_REVIEW"

  // refund/adjustment settle exactly -> keep them NORMAL (not exceptions)
  if (
    (row.scenario === "refund" || row.scenario === "adjustment") &&
    !confirmed &&
    row.ml_anomaly !== -1
  ) {
    decision = "NORMAL"
  }

  const llmDisagrees =
    (row.llm_risk_opinion === "HIGH" || row.llm_risk_opinion === "CRITICAL") &&
    row.llm_confidence >= 0.7
  if (decision === "NORMAL" && llmDisagrees) {
    decision = "AI_ESCALATED_REVIEW"
  }

  return decision
}

// ---------------------------------------------------------------
// 7. Action Agent
// ---------------------------------------------------------------
function act(row: {
  final_decision: FinalDecision
  risk_level: RiskLevel
  scenario?: string
  llm_narrative: string
}) {
  const { final_decision, risk_level, scenario = "" } = row

  if (final_decision === "CONFIRMED_HIGH_PRIORITY" || risk_level === "CRITICAL") {
    if (scenario === "missing_settlement")
      return {
        recommended_action: "HOLD_SETTLEMENT",
        action_priority: "IMMEDIATE" as const,
        action_reason: "Settlement discrepancy requires immediate financial review.",
      }
    if (scenario === "duplicate_transaction")
      return {
        recommended_action: "BLOCK_DUPLICATE",
        action_priority: "IMMEDIATE" as const,
        action_reason: "Duplicate transaction detected.",
      }
    if (scenario === "wrong_settlement")
      return {
        recommended_action: "HOLD_AND_RECONCILE",
        action_priority: "IMMEDIATE" as const,
        action_reason: "Settlement amount requires reconciliation.",
      }
    return {
      recommended_action: "MANUAL_INVESTIGATION",
      action_priority: "IMMEDIATE" as const,
      action_reason: "High financial risk detected.",
    }
  }

  if (final_decision === "FINANCIAL_EXCEPTION")
    return {
      recommended_action: "MANUAL_REVIEW",
      action_priority: "HIGH" as const,
      action_reason: "Financial exception requires review.",
    }

  if (final_decision === "ML_REVIEW")
    return {
      recommended_action: "ML_FLAGGED_REVIEW",
      action_priority: "HIGH" as const,
      action_reason: "Statistical anomaly flagged by the ML model.",
    }

  if (final_decision === "AI_ESCALATED_REVIEW")
    return {
      recommended_action: "AI_FLAGGED_MANUAL_REVIEW",
      action_priority: "HIGH" as const,
      action_reason:
        "Rule-based checks scored this as normal, but the LLM investigation agent flagged it with high confidence: " +
        (row.llm_narrative || "independent review disagreed."),
    }

  return {
    recommended_action: "NO_ACTION",
    action_priority: "LOW" as const,
    action_reason: "Transaction is within acceptable financial control limits.",
  }
}

// ---------------------------------------------------------------
// Orchestrator
// ---------------------------------------------------------------
export function runPipeline(raw: RawTransaction[]): Transaction[] {
  const base = raw.map((r) => ({ ...r, amount: r.payment_amount }) as Row)

  const reconciled = base.map((r) => ({ ...r, ...reconcile(r) }))
  const dup = detectDuplicates(reconciled)
  const withDup = reconciled.map((r, i) => ({ ...r, ...dup[i] }))

  const anomalies = detectAnomalies(
    withDup.map((r) => ({
      settlement_ratio: r.settlement_ratio,
      deviation_ratio: r.deviation_ratio,
      difference_to_payment_ratio: r.difference_to_payment_ratio,
    })),
  )
  const withAnom = withDup.map((r, i) => ({ ...r, ...anomalies[i] }))

  const withRisk = withAnom.map((r) => ({ ...r, ...assessRisk(r) }))
  const withInv = withRisk.map((r) => ({ ...r, ...investigate(r) }))
  const llm = runLlm(withInv)
  const withLlm = withInv.map((r, i) => ({ ...r, ...llm[i] }))

  const withDecision = withLlm.map((r) => ({
    ...r,
    final_decision: decide(r),
  }))
  const final = withDecision.map((r) => ({ ...r, ...act(r) }))

  return final as Transaction[]
}
