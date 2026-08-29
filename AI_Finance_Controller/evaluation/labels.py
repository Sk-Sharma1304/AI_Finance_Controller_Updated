"""
Shared ground-truth label definition for evaluation scripts.

IMPORTANT FINDING
------------------
`ground_truth.csv` carries a `scenario` column with 8 possible
values: normal, refund, adjustment, amount_discrepancy,
missing_settlement, duplicate_transaction, wrong_settlement,
unexplained_difference.

The original evaluation scripts labeled anything with
`scenario != "normal"` as an anomaly. That's wrong: `refund` and
`adjustment` are legitimate business events where the settlement
was correctly reconciled (deviation_ratio == 0.0, settlement_ratio
== 1.0 for every single row in those two scenarios) — the model
was being graded as "wrong" for correctly NOT flagging clean
transactions. That mislabeling alone was enough to collapse
precision/recall to ~0 in `evaluate_reconciliation_model.py`.

`EXCEPTION_SCENARIOS` below is the corrected set: only scenarios
that represent an actual reconciliation problem count as positive
(anomalous) examples.
"""

EXCEPTION_SCENARIOS = [
    "missing_settlement",
    "duplicate_transaction",
    "wrong_settlement",
    "amount_discrepancy",
    "unexplained_difference",
]


def is_exception(scenario_series):
    """Return a 0/1 label Series: 1 if the scenario is a genuine
    reconciliation exception, 0 if it's normal or a legitimate,
    correctly-reconciled business event (refund, adjustment)."""

    return scenario_series.isin(EXCEPTION_SCENARIOS).astype(int)
