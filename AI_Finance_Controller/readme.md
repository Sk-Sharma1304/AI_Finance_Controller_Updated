# AI Finance Controller

A multi-agent financial reconciliation and fraud-control pipeline,
with an LLM reasoning layer and a live control-tower dashboard,
built for the **Razorpay Buildathon**.

## The problem

Every payment gateway runs settlement reconciliation: comparing
what a payout *should* have been against what actually settled.
Most exceptions are boring (a fee was miscalculated) — some are not
(a duplicate payout, a missing settlement, an amount that doesn't
match anything on record). Today that triage is largely manual:
an ops analyst opens a spreadsheet, eyeballs a diff, and decides
what to do. It doesn't scale, and it's inconsistent between
analysts.

This project automates that triage end-to-end: ingest raw
transactions → reconcile → detect duplicates → detect statistical
anomalies → score risk → investigate (rules + LLM) → decide → act,
and surfaces the result in a reviewable queue instead of a wall of
CSVs.

## Architecture

```
Transaction Data
       ↓
 ORCHESTRATOR AGENT
       ↓
 ┌───────────────┬────────────────────┬─────────────────────┐
 │ Reconciliation │ Anomaly Detection  │ Duplicate Detection │
 │     Agent      │       Agent        │        Agent        │
 └───────┬───────┴──────────┬─────────┴──────────┬──────────┘
         └──────────────────┼─────────────────────┘
                             ↓
                    Risk Assessment Agent
                             ↓
              Investigation Agent (rule-based)
                             ↓
             LLM Investigation Agent (OpenAI) 
                             ↓
                     Decision Agent
                             ↓
                       Action Agent
                             ↓
              Streamlit Control-Tower Dashboard ← NEW
```

## Why a multi-agent pipeline?

Reconciliation exceptions aren't one problem, they're several: a
settlement can be short, missing, duplicated, or just
statistically weird compared to everything else that day. A single
rule set (or a single model) tends to get good at one of those and
blind to the rest. Splitting the work lets each agent specialize:

- **Reconciliation Agent** – deterministic comparison of expected
  vs. actual settlement (ratios, deviation, severity).
- **Duplicate Detection Agent** – flags transactions that look like
  the same financial event happened more than once.
- **Anomaly Detection Agent** – an unsupervised `IsolationForest`
  that catches statistically unusual transactions without needing
  any labels, so it works even on patterns it's never seen before.
- **Risk Assessment Agent** – turns exception type + financial
  impact into a 0–100 risk score and a LOW/MEDIUM/HIGH/CRITICAL
  level.
- **Investigation Agent (rule-based)** – turns all of the above
  evidence into a human-readable explanation and recommendation.
- **LLM Investigation Agent (OpenAI)** – see below.
- **Decision Agent** – combines rule-based risk, the ML anomaly
  signal, and the LLM's independent opinion into one final call.
- **Action Agent** – converts the decision into a concrete next
  step (`HOLD_SETTLEMENT`, `BLOCK_DUPLICATE`, `AI_FLAGGED_MANUAL_REVIEW`,
  ...) with a priority and reason.

## The LLM layer — and why it's not just narration

It would be easy to bolt an LLM onto this pipeline purely to write
nicer sentences on top of a decision the rules already made. That's
not what this does. `agents/llm_investigation_agent.py` sends the
full evidence for a transaction to OpenAI and asks for an
**independent** risk opinion — and `agents/decision_agent.py` acts
on it:

> If the rule-based pipeline scored a transaction as `NORMAL`, but
> the LLM disagrees with confidence ≥ 0.7 and rates it HIGH or
> CRITICAL, the decision is escalated to `AI_ESCALATED_REVIEW`
> instead of silently trusting the rules.

That's the actual point of the LLM step: catching the case where
the deterministic rules missed something a sharper read of the
evidence would catch — not re-describing a foregone conclusion.

Engineering choices, on purpose:
- **Cost/latency control** — the LLM only reviews transactions the
  rules already think are worth a second look (`risk_level != LOW`,
  or `duplicate_flag`, or an ML anomaly), capped by `MAX_LLM_CALLS`
  (default 25) per run.
- **Graceful degradation** — no `OPENAI_API_KEY`? The pipeline
  still runs end-to-end on rule-based logic alone; the LLM agent
  no-ops with a clear log line instead of crashing. Anyone can run
  and judge this project without an API key.
- **Structured output** — the model is asked for strict JSON
  (`narrative`, `risk_opinion`, `confidence`, `recommended_action`)
  via `response_format={"type": "json_object"}`, parsed defensively.

### Configuration

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"   # optional, this is the default
export MAX_LLM_CALLS="25"           # optional, cost/latency cap
```

## Project structure

```
AI_Finance_Controller/
├── main.py                        # entry point
├── orchestrator/
│   └── finance_orchestrator.py    # loads data, runs all agents in order
├── agents/
│   ├── reconciliation_agent.py
│   ├── duplicates_detection_agent.py
│   ├── anomaly_agent.py
│   ├── risk_agent.py
│   ├── investigation_agent.py
│   ├── llm_investigation_agent.py # OpenAI reasoning layer
│   ├── decision_agent.py
│   └── action_agent.py
├── dashboard/
│   └── app.py                     # Streamlit control-tower demo
├── evaluation/
│   ├── labels.py                  # shared, corrected ground-truth labels
│   ├── evaluate_reconciliation_model.py
│   └── evaluate_anomaly_model.py
├── data/
│   ├── finance_controller_dataset.csv   # raw synthetic transactions
│   ├── ground_truth.csv                 # injected scenario + expected settlement
│   ├── finance_features.csv             # precomputed features (analysis)
│   └── reconciliation_features.csv      # precomputed features (evaluation)
└── requirements.txt
```

## Getting started

```bash
pip install -r requirements.txt

# 1. Run the pipeline (LLM step is optional — see above)
export OPENAI_API_KEY="sk-..."   # optional
python main.py

# 2. Open the dashboard
streamlit run dashboard/app.py
```

The pipeline writes one CSV per stage into `outputs/` (created
automatically):

| File                          | Produced by                 |
|--------------------------------|------------------------------|
| `reconciliation_results.csv`   | Reconciliation Agent         |
| `duplicate_results.csv`        | Duplicate Detection Agent    |
| `anomaly_results.csv`          | Anomaly Detection Agent      |
| `risk_results.csv`             | Risk Assessment Agent        |
| `investigation_results.csv`    | Investigation Agent          |
| `llm_investigation_results.csv`| LLM Investigation Agent      |
| `final_decisions.csv`          | Decision Agent                |
| `action_results.csv`           | Action Agent (dashboard reads this) |

Each agent can also be run standalone for debugging, e.g.
`python agents/reconciliation_agent.py`.

## Data

`data/finance_controller_dataset.csv` is a synthetic set of 100
payments (amount, fee, tax, refund, adjustment, actual settlement,
status). `data/ground_truth.csv` carries the injected scenario for
each payment plus what the settlement *should* have been. The
orchestrator merges the two on `payment_id` before the pipeline
runs — the same way a reconciliation system compares a payout file
against its own computed expectation.

## Evaluation 

Current results, stratified 70/30 train/test split, corrected labels:

| Model                                             | Precision | Recall | F1   | ROC-AUC |
|----------------------------------------------------|-----------|--------|------|---------|
| IsolationForest, ratio features (unsupervised)      | 1.00      | 1.00   | 1.00 | 1.00    |
| RandomForest, ratio features (supervised)           | 1.00      | 1.00   | 1.00 | 1.00    |
| IsolationForest, raw settlement fields (unsupervised)| 0.75     | 0.36   | 0.49 | 0.68    |

The gap between the last two rows is itself the finding: **feature
engineering, not model choice, is what makes this work.** Ratio
features (settlement ratio, deviation ratio, difference-to-payment
ratio) separate exceptions from normal transactions almost
perfectly; raw absolute fields (fee, tax, settlement amount) don't
carry that signal on their own. The pipeline uses the ratio
features (`agents/anomaly_agent.py`) and stays unsupervised on
purpose — no scenario labels required in production, so it works
against a real, unlabeled settlement stream and can catch a novel
failure mode a supervised model has never seen.

Run `python evaluation/evaluate_reconciliation_model.py` and
`python evaluation/evaluate_anomaly_model.py` to reproduce.

## Dashboard

`dashboard/app.py` is a Streamlit control-tower view over
`outputs/action_results.csv`:

- **KPIs** — total volume, auto-cleared %, flagged count, AI-escalated
  count, total financial impact at risk.
- **Priority queue** — every non-normal decision, sorted by
  financial impact, with a per-transaction Approve / Hold action
  (demo-only — kept in session state, doesn't write back to the
  pipeline; in production this would call an action-execution
  service).
- **Transaction drill-down** — pick any `payment_id` and see the
  full 8-step agent trail: what reconciliation found, whether it
  was a duplicate, the ML anomaly verdict, the risk score, the
  rule-based investigation, the LLM's independent opinion, the
  final decision, and the recommended action — the "show your
  work" view for a single case.

## Known limitations

- The dataset is synthetic and small (100 transactions); the
  perfect scores above reflect a clean synthetic signal, not a
  claim that this generalizes untested to real settlement noise.
  Next step: validate against a larger, real (or more realistically
  noisy) transaction set.
- The LLM escalation threshold (confidence ≥ 0.7) is a starting
  point, not calibrated against labeled outcomes yet.
