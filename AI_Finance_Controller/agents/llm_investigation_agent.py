"""
LLM Investigation Agent
========================

Adds a genuine LLM reasoning step on top of the rule-based
Investigation Agent. Where `InvestigationAgent` (investigation_agent.py)
produces a templated summary from fixed if/elif branches, this
agent hands the same evidence to an OpenAI model and asks it to:

  1. Write a free-form investigation narrative (not a template).
  2. Give an independent risk opinion (LOW/MEDIUM/HIGH/CRITICAL).
  3. Give a confidence score for that opinion.
  4. Suggest a concrete next action in plain language.

Design decisions, on purpose:

- Cost/latency control: the LLM is only called for transactions
  the rule-based agents already think are worth a second look
  (risk_level != LOW, OR duplicate_flag, OR ml_anomaly == -1), and
  is capped by MAX_LLM_CALLS so a demo run never surprises you with
  100 API calls. Everything else keeps its rule-based summary.
- Graceful degradation: if OPENAI_API_KEY isn't set, or a call
  fails, or the `openai` package isn't installed, this agent no-ops
  and the pipeline still runs end to end on rule-based logic alone.
  Judges without an API key on hand can still run the full project.
- It genuinely feeds back into the decision: see decision_agent.py,
  which escalates a transaction the rules called NORMAL if the LLM
  disagrees with high confidence. That's the "AI catches what the
  rules missed" behaviour, not just narration on top of a fixed
  answer.

Environment variables:
    OPENAI_API_KEY   required to enable this agent at all
    OPENAI_MODEL     defaults to "gpt-4o-mini"
    MAX_LLM_CALLS    defaults to 25 (cost/latency cap per run)
"""

import json
import os

import pandas as pd


DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_LLM_CALLS = int(os.environ.get("MAX_LLM_CALLS", "25"))

SYSTEM_PROMPT = (
    "You are a senior payments risk analyst at a payment gateway "
    "(similar to Razorpay). You are reviewing a single transaction "
    "that an automated reconciliation and anomaly-detection pipeline "
    "has already scored. You are the final human-style sanity check "
    "before it goes to a decision engine. Be skeptical, concise, and "
    "concrete. Do not repeat the input verbatim back at the user. "
    "Respond ONLY with a JSON object matching this schema:\n"
    '{"narrative": string (2-3 sentences, plain English explanation '
    "for a finance ops reviewer), "
    '"risk_opinion": one of ["LOW","MEDIUM","HIGH","CRITICAL"], '
    '"confidence": number between 0 and 1, '
    '"recommended_action": string (one concrete next step)}'
)


def _client_available():

    if not os.environ.get("OPENAI_API_KEY"):
        return False

    try:
        import openai  # noqa: F401
    except ImportError:
        return False

    return True


def _build_user_prompt(row):

    fields = {
        "payment_id": row.get("payment_id"),
        "scenario": row.get("scenario"),
        "financial_impact": row.get("financial_impact"),
        "risk_score": row.get("risk_score"),
        "risk_level": row.get("risk_level"),
        "reconciliation_status": row.get("reconciliation_status"),
        "duplicate_flag": bool(row.get("duplicate_flag", False)),
        "duplicate_count": row.get("duplicate_count"),
        "ml_anomaly": (
            "ANOMALY"
            if row.get("ml_anomaly") == -1
            else "NORMAL"
        ),
        "rule_based_summary": row.get("investigation_summary"),
        "rule_based_evidence": row.get("evidence"),
    }

    return (
        "Review this transaction and give your independent "
        "assessment:\n\n" + json.dumps(fields, default=str, indent=2)
    )


def _call_llm(client, model, row):

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(row)},
        ],
    )

    content = response.choices[0].message.content

    parsed = json.loads(content)

    return {
        "llm_narrative": parsed.get("narrative", ""),
        "llm_risk_opinion": parsed.get("risk_opinion", "UNKNOWN"),
        "llm_confidence": float(parsed.get("confidence", 0.0)),
        "llm_recommended_action": parsed.get(
            "recommended_action", ""
        ),
    }


def _fallback_row(reason):

    return {
        "llm_narrative": reason,
        "llm_risk_opinion": "NOT_EVALUATED",
        "llm_confidence": 0.0,
        "llm_recommended_action": "",
    }


def _needs_llm_review(row):

    return (
        row.get("risk_level") != "LOW"
        or bool(row.get("duplicate_flag", False))
        or row.get("ml_anomaly") == -1
    )


def run_llm_investigation_agent(df, model=None, max_calls=None):
    """
    Adds llm_narrative / llm_risk_opinion / llm_confidence /
    llm_recommended_action columns to `df`. Safe to call even
    without an API key — it will just fill in a fallback message
    and the pipeline keeps working on rule-based logic alone.

    `max_calls` overrides the MAX_LLM_CALLS env default for this
    call only -- used by api_server.py to enforce a per-actor daily
    LLM budget (rate_limit.py) on top of the per-run cap.
    """

    result = df.copy()

    model = model or DEFAULT_MODEL
    call_budget = MAX_LLM_CALLS if max_calls is None else max_calls

    if not _client_available():

        print(
            "  [LLM Investigation Agent] OPENAI_API_KEY not set "
            "(or `openai` package missing) — skipping LLM "
            "enrichment, rule-based investigation only."
        )

        fallback = _fallback_row(
            "LLM review skipped: no OPENAI_API_KEY configured."
        )

        for key, value in fallback.items():
            result[key] = value

        return result

    from openai import OpenAI

    client = OpenAI()

    candidate_mask = result.apply(_needs_llm_review, axis=1)

    candidate_indices = result[candidate_mask].index.tolist()

    calls_made = 0
    calls_skipped_due_to_cap = 0

    llm_columns = {
        idx: _fallback_row("Not selected for LLM review.")
        for idx in result.index
    }

    for idx in candidate_indices:

        if calls_made >= call_budget:
            calls_skipped_due_to_cap += 1
            llm_columns[idx] = _fallback_row(
                "MAX_LLM_CALLS budget reached for this run."
            )
            continue

        row = result.loc[idx]

        try:
            llm_columns[idx] = _call_llm(client, model, row)
            calls_made += 1

        except Exception as exc:  # noqa: BLE001 - degrade gracefully

            llm_columns[idx] = _fallback_row(
                f"LLM call failed ({exc.__class__.__name__}); "
                "falling back to rule-based investigation."
            )

    llm_df = pd.DataFrame.from_dict(llm_columns, orient="index")

    result = result.join(llm_df)

    print(
        f"  [LLM Investigation Agent] {calls_made} call(s) made, "
        f"{calls_skipped_due_to_cap} skipped (call_budget="
        f"{call_budget}), model={model}."
    )

    return result


if __name__ == "__main__":

    df = pd.read_csv("outputs/investigation_results.csv")

    result = run_llm_investigation_agent(df)

    os.makedirs("outputs", exist_ok=True)

    result.to_csv(
        "outputs/llm_investigation_results.csv",
        index=False
    )

    print("=" * 50)
    print("LLM INVESTIGATION AGENT")
    print("=" * 50)

    print(
        result[
            [
                "payment_id",
                "risk_level",
                "llm_risk_opinion",
                "llm_confidence",
                "llm_narrative",
            ]
        ].head(20).to_string(index=False)
    )
